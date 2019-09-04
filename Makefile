DOCKER_REGISTRY ?= docker.chameleoncloud.org
DOCKER_TAG ?= $(shell git rev-parse --short HEAD)
DOCKER_IMAGE := $(DOCKER_REGISTRY)/portal:$(DOCKER_TAG)
DOCKER_IMAGE_LATEST := $(DOCKER_REGISTRY)/portal:latest

.PHONY: build
build:
	docker build -t $(DOCKER_IMAGE) .
	docker tag $(DOCKER_IMAGE) $(DOCKER_IMAGE_LATEST)

.PHONY: publish
publish:
	docker push $(DOCKER_IMAGE)
	docker push $(DOCKER_IMAGE_LATEST)

.PHONY: start
start:
	docker-compose -f docker-compose.dev.yml up

requirements-frozen.txt: build
	docker run --rm $(DOCKER_IMAGE) pip freeze > $@
