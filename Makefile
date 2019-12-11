VIDEO ?= video.mp4
VIDEO_FOUND := $(shell test -f ${VIDEO} 2> /dev/null; echo $$?)

DOCKER_IMG_NAME ?= qrlipsync-img
ARGS ?=

build_docker_img:
	docker build -t ${DOCKER_IMG_NAME} .


analyze:
ifeq (${VIDEO_FOUND}, 1)
	@echo "${VIDEO} file not found, exiting, run with VIDEO=${VIDEO}"
	@exit 1
else
	docker run -v ${CURDIR}/${VIDEO}:/src/${VIDEO}:ro ${DOCKER_IMG_NAME} qr-lipsync-detect.py /src/${VIDEO} ${ARGS}
endif


generate:
	docker run -v ${CURDIR}:/src ${DOCKER_IMG_NAME} qr-lipsync-generate.py ${ARGS}
