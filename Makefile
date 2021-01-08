DOCKER_REGISTRY ?= docker.chameleoncloud.org
DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE := $(DOCKER_REGISTRY)/portal:$(DOCKER_TAG)
DOCKER_IMAGE_LATEST := $(DOCKER_REGISTRY)/portal:latest
PYTHON_VERSION ?= 3.7.9
PYTHON_IMAGE_TAG := $(PYTHON_VERSION)-stretch

PORTAL_MANAGE_CMD := docker-compose exec portal python manage.py
#if APP is unset, then the variable equals the empty string.
ifeq ($(APP),)
MIGRATIONS_CMD := $(PORTAL_MANAGE_CMD) makemigrations
else
MIGRATIONS_CMD := $(PORTAL_MANAGE_CMD) makemigrations "$(APP)"
endif

.PHONY: build
build:
	./docker/client/build.sh
	docker build -t $(DOCKER_IMAGE) .
	docker tag $(DOCKER_IMAGE) $(DOCKER_IMAGE_LATEST)

.PHONY: publish
publish:
	docker push $(DOCKER_IMAGE)

.PHONY: publish-latest
publish-latest:
	docker push $(DOCKER_IMAGE_LATEST)

.PHONY: start
start:
	DOCKER_IMAGE_LATEST=$(DOCKER_IMAGE_LATEST) docker-compose up -d

.PHONY: migrations
migrations: start
	DOCKER_IMAGE_LATEST=$(DOCKER_IMAGE_LATEST) $(MIGRATIONS_CMD) --check

requirements-frozen.txt: build
	docker run --rm $(DOCKER_IMAGE) pip freeze > $@
