# Set make variables from .env file
ifneq (,$(wildcard ./.env))
	include .env
	export
	ENV_FILE_PARAM = --env-file .env
endif

DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE ?= $(DOCKER_REGISTRY)/portal:$(DOCKER_TAG)
DOCKER_IMAGE_LATEST ?= $(DOCKER_REGISTRY)/portal:latest
PY_IMG_TAG ?= 3.7.9-stretch
NODE_VER ?= lts

COMPOSE_CMD = docker compose -f docker-compose.yml
PORTAL_RUN_CMD = ${COMPOSE_CMD} run --rm portal

.env:
	cp .env.sample .env

.PHONY: build
build: .env
	${COMPOSE_CMD} build

.PHONY: down
down:
	${COMPOSE_CMD} down

.PHONY: down-volume
down-volume:
	${COMPOSE_CMD} down -v

.PHONY: frontend
frontend:
	${COMPOSE_CMD} up -d portal vue

.PHONY: start
start-all:
	${COMPOSE_CMD} up -d

# Run commands against portal and db
.PHONY: check
check:
	${PORTAL_RUN_CMD} check

.PHONY: migrate
migrate:
	${PORTAL_RUN_CMD} migrate

.PHONY: makemigrations
makemigrations:
	${PORTAL_RUN_CMD} makemigrations --check

.PHONY: test
test:
	${PORTAL_RUN_CMD} test
