FROM python:3.12.15-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --system --uid 10001 appuser
COPY app ./app
# Run unprivileged
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=5 \
  CMD ["python", "-c", "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2).status == 200 else 1)"]
# ws-max-size 64 KiB: clients only ever send tiny "view" messages.
# --factory: the app is built at startup from the environment, not at import time.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "65536", "--no-access-log"]

# Debug image (`make debug`): the runtime image plus debugpy. The process starts
# under the debugger and listens on 5678; compose publishes it on 127.0.0.1 only,
# because an open debug port means remote code execution.
FROM runtime AS debug
USER root
COPY requirements-debug.txt .
RUN pip install --no-cache-dir -r requirements-debug.txt
USER appuser
EXPOSE 5678
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "65536", "--no-access-log"]

# Unit tests run against exactly the runtime image plus test-only dependencies.
FROM runtime AS test
USER root
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY pytest.ini .
COPY tests ./tests
USER appuser
CMD ["pytest", "-q", "-p", "no:cacheprovider", "tests"]
