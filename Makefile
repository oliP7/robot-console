# One command each: make up | make debug | make test | make load | make down
SHELL := /bin/sh
COMPOSE      := docker compose -p robot-console
TEST_COMPOSE := docker compose -p robot-console-test -f docker-compose.yml -f docker-compose.test.yml
LOAD_COMPOSE := docker compose -p robot-console-load -f docker-compose.yml -f docker-compose.load.yml
DEBUG_COMPOSE := $(COMPOSE) -f docker-compose.yml -f docker-compose.debug.yml

.PHONY: up debug down logs token test test-unit test-integration load clean

up:            ## build and start the stack, wait until healthy: http://localhost:8080
	$(COMPOSE) up --build -d --wait
	@echo "Robot Console: http://localhost:8080   (MQTT for extra robots: localhost:1883)"

debug:         ## like up, but the backend runs under debugpy: attach to 127.0.0.1:5678
	$(DEBUG_COMPOSE) up --build -d --wait
	@echo "Robot Console: http://localhost:8080   Debugger: attach to 127.0.0.1:5678 (make up to leave debug mode)"

down:          ## stop the stack (keeps the generated secrets volume)
	$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE) logs -f --tail=100

token:         ## print the API token (only needed when auth is enabled)
	@$(COMPOSE) exec -T backend cat /run/robot-console-secrets/api.token

test: test-unit test-integration   ## all tests, all in containers

test-unit:
	$(TEST_COMPOSE) --profile test build backend-unit frontend-unit
	$(TEST_COMPOSE) --profile test run --rm backend-unit
	$(TEST_COMPOSE) --profile test run --rm frontend-unit

test-integration:
	@$(TEST_COMPOSE) up --build -d --wait || { $(TEST_COMPOSE) logs --tail=50; $(TEST_COMPOSE) down -v; exit 1; }
	@$(TEST_COMPOSE) --profile test run --rm --build integration; rc=$$?; \
	  if [ $$rc -ne 0 ]; then $(TEST_COMPOSE) logs --tail=80 backend web; fi; \
	  $(TEST_COMPOSE) --profile test down -v --remove-orphans; exit $$rc

load:          ## throughput benchmark: 1k, 5k, 20k, 50k msg/s (STAGES=... to override)
	@$(LOAD_COMPOSE) up --build -d --wait || { $(LOAD_COMPOSE) down -v; exit 1; }
	@$(LOAD_COMPOSE) --profile load run --rm --build loadtest python tools/loadtest.py $(if $(STAGES),--stages $(STAGES),); rc=$$?; \
	  $(LOAD_COMPOSE) --profile load down -v --remove-orphans; exit $$rc

clean:         ## remove containers AND the generated secrets volume
	$(COMPOSE) down -v --remove-orphans
