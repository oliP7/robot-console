"""Entry point. Run with: uvicorn app.main:create_app --factory"""
from __future__ import annotations

from fastapi import FastAPI

from .config.app_factory import AppFactory
from .config.settings import Settings
from .interfaces.message_broker import MessageBroker


def create_app(settings: Settings | None = None, broker: MessageBroker | None = None) -> FastAPI:
    return AppFactory(settings or Settings.from_env(), broker).create()
