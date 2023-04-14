FROM archlinux:latest

ENV IN_QRLIPSYNC 1

ENV LANG=C.UTF-8

RUN \
    pacman -Sy && \
    pacman -S archlinux-keyring --noconfirm --noprogressbar --quiet --needed && \
    pacman -Su --noconfirm --noprogressbar --quiet && \
    pacman -S --noconfirm --noprogressbar --quiet --needed \
        git vim \
        gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav \
        qrencode zbar make \
        python-setuptools python-pip python-gobject gst-python python-numpy

COPY . /opt/qrlipsync

RUN cd /opt/qrlipsync && pip install -e '.[testing]'

WORKDIR /opt/src
