VIDEO ?= video.mp4
VIDEO_FOUND := $(shell test -f ${VIDEO} 2> /dev/null; echo $$?)
CI_COMMIT_REF_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
DOCKER_IMG_NAME ?= registry.ubicast.net/devtools/qr-lipsync:${CI_COMMIT_REF_NAME}
ARGS ?=

build:
	docker build -t ${DOCKER_IMG_NAME} .

push:
	docker push ${DOCKER_IMG_NAME}

shell:
	docker run -ti -v ${CURDIR}:/usr/src ${DOCKER_IMG_NAME} /bin/bash

lint:
	docker run -v ${CURDIR}:/usr/src ${DOCKER_IMG_NAME} flake8

test:
	docker run -v ${CURDIR}:/usr/src ${DOCKER_IMG_NAME} pytest

analyze:
ifeq (${VIDEO_FOUND}, 1)
	@echo "${VIDEO} file not found, exiting, run with VIDEO=${VIDEO}"
	@exit 1
else
	docker run -v ${CURDIR}/${VIDEO}:/usr/src/${VIDEO}:ro ${DOCKER_IMG_NAME} qr-lipsync-detect.py /usr/src/${VIDEO} ${ARGS}
endif

generate:
	docker run -v ${CURDIR}:/usr/src ${DOCKER_IMG_NAME} qr-lipsync-generate.py --output-dir /usr/src ${ARGS}
