# Browser end-to-end tests. The base image ships Chromium and its system
# libraries, so nothing is installed on the host. Talks to the stack over the
# compose network only.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_BREAK_SYSTEM_PACKAGES=1
WORKDIR /srv
COPY tests/e2e/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --system --create-home --uid 10001 tester
COPY tests/e2e ./tests/e2e
# uid 10001 is the test runner identity that may read the API token (broker/init-secrets.sh).
USER tester
CMD ["pytest", "-q", "-s", "-p", "no:cacheprovider", "tests/e2e"]
