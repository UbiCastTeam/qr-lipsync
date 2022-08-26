VIDEO ?= video.mp4
VIDEO_FOUND := $(shell test -f ${VIDEO} 2> /dev/null; echo $$?)
CI_COMMIT_REF_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
DOCKER_IMAGE_NAME ?= registry.ubicast.net/devtools/qr-lipsync:${CI_COMMIT_REF_NAME}
ARGS ?=

build:
	docker build -t ${DOCKER_IMAGE_NAME} .

pull:
	docker pull ${DOCKER_IMAGE_NAME}

push:
	docker push ${DOCKER_IMAGE_NAME}

shell:
	docker run -ti -v ${CURDIR}:/opt/qrlipsync -w /opt/qrlipsync ${DOCKER_IMAGE_NAME} /bin/bash

lint:
ifndef IN_QRLIPSYNC
	docker run -v ${CURDIR}:/opt/qrlipsync -w /opt/qrlipsync ${DOCKER_IMAGE_NAME} make lint
else
	flake8
endif

test:
ifndef IN_QRLIPSYNC
	docker run -v ${CURDIR}:/opt/qrlipsync -w /opt/qrlipsync ${DOCKER_IMAGE_NAME} make test
else
	pytest
endif

analyze:
ifeq (${VIDEO_FOUND}, 1)
	@echo "${VIDEO} file not found, exiting, run with VIDEO=${VIDEO}"
	@exit 1
else
	docker run -v ${CURDIR}:/opt/src/ ${DOCKER_IMAGE_NAME} qr-lipsync-detect.py /opt/src/${VIDEO} ${ARGS}
endif

generate:
	docker run -v ${CURDIR}:/opt/src ${DOCKER_IMAGE_NAME} qr-lipsync-generate.py --output-dir /opt/src ${ARGS}
