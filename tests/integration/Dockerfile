# Test runner and load tools. Talks to the stack over the compose network only.
FROM python:3.12.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY tests/integration/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd --system --uid 10001 tester
COPY tests/integration ./tests/integration
COPY tools ./tools
USER tester
CMD ["pytest", "-q", "tests/integration"]
