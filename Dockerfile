FROM archlinux/archlinux

ENV IN_QRLIPSYNC 1

ENV LANG=C.UTF-8

RUN \
    pacman -Sy && \
    pacman -S archlinux-keyring --noconfirm --noprogressbar --quiet --needed && \
    pacman -Su --noconfirm --noprogressbar --quiet && \
    pacman -S --noconfirm --noprogressbar --quiet --needed \
        git base-devel vim \
        gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav \
        qrencode zbar ffmpeg \
        python-setuptools python-pip python-gobject gst-python python-numpy

RUN \
    git clone https://github.com/UbiCastTeam/gst-qroverlay.git && \
    cd gst-qroverlay && ./autogen.sh && ./configure --prefix=/usr && make install && cd .. && rm -rf gst-qroverlay/ && \
    mkdir src/

COPY . /opt/qrlipsync

RUN cd /opt/qrlipsync && pip install -e '.[testing]'

WORKDIR /opt/src
