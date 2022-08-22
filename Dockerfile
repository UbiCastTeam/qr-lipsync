FROM debian:bullseye

ENV IN_QRLIPSYNC 1

ENV LANG=C.UTF-8

RUN apt-get -q update && apt-get -qy install --no-install-recommends \
	build-essential vim git autoconf automake pkg-config m4 libtool \
	gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-x \
	libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libqrencode-dev \
        qrencode libzbar0 ffmpeg \
        python3-setuptools python3-pip python3-gst-1.0 python3-numpy

RUN \
    git clone https://github.com/UbiCastTeam/gst-qroverlay.git && \
    cd gst-qroverlay && ./autogen.sh && ./configure --prefix=/usr --libdir=/usr/lib/x86_64-linux-gnu  && make install && cd .. && rm -rf gst-qroverlay/ && \
    mkdir src/

COPY . /opt/qrlipsync

RUN cd /opt/qrlipsync && pip install -e '.[testing]'

WORKDIR /opt/src
