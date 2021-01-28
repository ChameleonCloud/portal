# Set make variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export
	ENV_FILE_PARAM = --env-file .env
endif

DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE ?= $(DOCKER_REGISTRY)/portal:$(DOCKER_TAG)
DOCKER_IMAGE_LATEST ?= $(DOCKER_REGISTRY)/portal:latest

.env:
	cp .env.sample .env

.PHONY: build
build: .env
	./docker/client/build.sh
	docker build --build-arg PY_IMG_TAG=$(PY_IMG_TAG) \
				 --build-arg NODE_VER=$(NODE_VER) \
				 -t $(DOCKER_IMAGE) .
	docker tag $(DOCKER_IMAGE) $(DOCKER_IMAGE_LATEST)

.PHONY: publish
publish:
	docker push $(DOCKER_IMAGE)

.PHONY: publish-latest
publish-latest:
	docker push $(DOCKER_IMAGE_LATEST)

.PHONY: start
start:
	docker-compose $(ENV_FILE_PARAM) up -d

.PHONY: migrations
migrations: start
	docker-compose exec portal makemigrations --check

requirements-frozen.txt: build
	docker run --rm $(DOCKER_IMAGE) pip freeze > $@
