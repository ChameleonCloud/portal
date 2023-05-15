# Set make variables from .env file
ifneq (,$(wildcard ./.env))
	include .env
	export
	ENV_FILE_PARAM = --env-file .env
endif

DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE ?= $(DOCKER_REGISTRY)/portal:$(DOCKER_TAG)
DOCKER_IMAGE_LATEST ?= $(DOCKER_REGISTRY)/portal:latest

ifeq ($(shell arch),arm64)
	PY_IMG = arm64v8/python
	NODE_IMG = arm64v8/node
else
	PY_IMG = python
	NODE_IMG = node
endif

PY_VER ?= 3.7.16
NODE_VER ?= lts

.env:
	cp .env.sample .env

.PHONY: build
build: .env
	docker build \
		--build-arg PY_VER=$(PY_VER) --build-arg PY_IMG=$(PY_IMG) \
		--build-arg NODE_VER=$(NODE_VER) --build-arg NODE_IMG=$(NODE_IMG) \
		-t $(DOCKER_IMAGE) .
	docker tag $(DOCKER_IMAGE) $(DOCKER_IMAGE_LATEST)

.PHONY: publish
publish:
	docker push $(DOCKER_IMAGE)

.PHONY: publish-latest
publish-latest:
	docker push $(DOCKER_IMAGE_LATEST)

.PHONY: start
start: .env
	docker-compose $(ENV_FILE_PARAM) up -d

.PHONY: clean
clean:
	docker-compose $(ENV_FILE_PARAM) down

.PHONY: migrations
migrations: start
	docker-compose exec portal python manage.py makemigrations --check

requirements-frozen.txt: build
	docker run --rm $(DOCKER_IMAGE) pip freeze > $@

COMPOSE_TEST_CMD :=  docker-compose -f tests-compose.yml

.PHONY: deploy-tests
deploy-tests:
	$(COMPOSE_TEST_CMD) run --rm portal migrate
	$(COMPOSE_TEST_CMD) run --rm portal collectstatic --no-input

.PHONY: deploy-tests-clean
deploy-tests-clean:
	$(COMPOSE_TEST_CMD) down -v
