"""Browser end-to-end test: the real web client, nginx, backend, Mosquitto and
unmodified robot.py containers. No mocks anywhere on the path.

Proves the challenge requirement through the UI itself: an operator clicks a
command button in one browser, the robot changes state, and the change appears
in that browser AND in a second, independent browser that only watches.
"""
from __future__ import annotations

import os
import time

import httpx
import pytest
from playwright.sync_api import Browser, Page, expect, sync_playwright

WEB = os.environ.get("WEB_URL", "http://web:8080")
TOKEN_FILE = os.environ.get("TOKEN_FILE", "/run/robot-console-secrets/api.token")
TIMEOUT_MS = 10_000
MODES = ("idle", "working", "error")


@pytest.fixture(scope="session")
def token() -> str:
    try:
        with open(TOKEN_FILE, encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError as exc:
        pytest.fail(f"cannot read API token from {TOKEN_FILE}: {exc}")


@pytest.fixture(scope="session")
def robot_id(token) -> str:
    """Wait until a real robot container is online and return its id."""
    deadline = time.time() + 45
    last = None
    while time.time() < deadline:
        try:
            r = httpx.get(f"{WEB}/api/robots", headers={"Authorization": f"Bearer {token}"}, timeout=3)
            last = r.status_code
            if r.status_code == 200:
                online = [x["id"] for x in r.json().get("robots", []) if x["online"]]
                if online:
                    return online[0]
        except httpx.HTTPError as exc:
            last = repr(exc)
        time.sleep(0.5)
    pytest.fail(f"no robot came online (last response: {last})")


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def open_console(browser: Browser, token: str, errors: list[str], name: str) -> Page:
    """A fresh browser context (own session storage), signed in through the token gate."""
    page = browser.new_context().new_page()
    page.on("pageerror", lambda exc: errors.append(f"{name}: {exc}"))
    page.goto(WEB)
    page.get_by_label("Access token").fill(token)
    page.get_by_role("button", name="Sign in").click()
    return page


def row_of(page: Page, robot_id: str):
    return page.get_by_role("row").filter(has_text=robot_id)


def test_click_in_one_browser_is_seen_in_both(browser, token, robot_id):
    errors: list[str] = []
    sender = open_console(browser, token, errors, "sender")
    watcher = open_console(browser, token, errors, "watcher")

    sender_mode = row_of(sender, robot_id).locator(".c-mode .chip")
    watcher_mode = row_of(watcher, robot_id).locator(".c-mode .chip")
    expect(sender_mode).to_be_visible(timeout=TIMEOUT_MS)
    expect(watcher_mode).to_be_visible(timeout=TIMEOUT_MS)

    # Pick a mode the robot is NOT in, so a change must happen.
    current = sender_mode.inner_text().strip()
    target = next(m for m in MODES if m != current)

    t0 = time.perf_counter()
    row_of(sender, robot_id).get_by_role("group", name=f"Set mode for {robot_id}") \
        .get_by_role("button", name=target, exact=True).click()

    # Both browsers show the state the robot itself reported (the UI is not optimistic).
    expect(sender_mode).to_have_text(target, timeout=TIMEOUT_MS)
    expect(watcher_mode).to_have_text(target, timeout=TIMEOUT_MS)
    ms = (time.perf_counter() - t0) * 1000

    # The sender's "Waiting for robot" line clears once telemetry confirms the command.
    expect(row_of(sender, robot_id).get_by_role("status")).to_have_count(0, timeout=TIMEOUT_MS)

    # The robot's state really changed: the backend reports it independently of the UI.
    r = httpx.get(f"{WEB}/api/robots/{robot_id}", headers={"Authorization": f"Bearer {token}"}, timeout=5)
    assert r.status_code == 200 and r.json()["mode"] == target, r.text

    assert not errors, f"uncaught errors in the page: {errors}"
    print(f"\n[browser] clicked set_mode={target} on {robot_id}: both browsers showed it after {ms:.0f} ms")
