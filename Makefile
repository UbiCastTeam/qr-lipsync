VIDEO ?= video.mp4
VIDEO_FOUND := $(shell test -f ${VIDEO} 2> /dev/null; echo $$?)
CI_COMMIT_REF_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
DOCKER_IMAGE ?= registry.ubicast.net/devtools/qr-lipsync:${CI_COMMIT_REF_NAME}
DOCKER_WORK_DIR ?= /opt/src
DOCKER_RUN ?= docker run --rm -it --user "$(shell id -u):$(shell id -g)" -v ${CURDIR}:${DOCKER_WORK_DIR} --name qr-lipsync

build:
	docker build -t ${DOCKER_IMAGE} ${BUILD_ARGS} --build-arg DOCKER_WORK_DIR=${DOCKER_WORK_DIR} .

rebuild:BUILD_ARGS = --no-cache
rebuild:build

pull:
	docker pull ${DOCKER_IMAGE}

push:
	docker push ${DOCKER_IMAGE}

shell:
	${DOCKER_RUN} ${DOCKER_IMAGE} /bin/bash

lint:
ifndef IN_QRLIPSYNC
	${DOCKER_RUN} ${DOCKER_IMAGE} make lint
else
	flake8
endif

test:PYTEST_ARGS := $(or ${PYTEST_ARGS},--cov --no-cov-on-fail --junitxml=report.xml --cov-report xml --cov-report term --cov-report html)
test:
ifndef IN_QRLIPSYNC
	${DOCKER_RUN} -e "PYTEST_ARGS=${PYTEST_ARGS}" ${DOCKER_IMAGE} make test
else
	pytest ${PYTEST_ARGS}
endif

analyze:
ifeq (${VIDEO_FOUND}, 1)
	@echo "${VIDEO} file not found, exiting, run with VIDEO=${VIDEO}"
	@exit 1
else
	${DOCKER_RUN} qr-lipsync-detect ${DOCKER_WORK_DIR}/${VIDEO} ${ARGS}
endif

generate:
	${DOCKER_RUN} qr-lipsync-generate --output-dir ${DOCKER_WORK_DIR} ${ARGS}
