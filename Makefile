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

PORTAL_RUN_CMD = docker compose run portal $(1)

.env:
	cp .env.sample .env

.PHONY: build
build: .env
	docker compose build

.PHONY: check
check:
	$(call PORTAL_RUN_CMD, check)

.PHONY: migrate
migrate:
	$(call PORTAL_RUN_CMD, migrate)

.PHONY: makemigrations
makemigrations:
	$(call PORTAL_RUN_CMD, makemigrations)

.PHONY: start
start: build
	docker compose up -d
