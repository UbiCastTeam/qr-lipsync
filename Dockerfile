FROM archlinux:latest

ENV IN_QRLIPSYNC 1

ENV LANG=C.UTF-8

RUN \
    pacman -Sy && \
    pacman -S archlinux-keyring --noconfirm --noprogressbar --quiet --needed && \
    pacman -Su --noconfirm --noprogressbar --quiet && \
    pacman -S --noconfirm --noprogressbar --quiet --needed \
        git vim curl \
        qrencode zbar make \
        python-setuptools python-pip python-gobject python-numpy

# FFmpeg6 with Gst 1.22 is racy see https://gitlab.freedesktop.org/gstreamer/gstreamer/-/issues/238, so we need a patched version of gst-libav until Gst 1.22.2
RUN curl -O https://nextcloud.ubicast.net/s/YyjoCzgpPTYr67j/download/gst-libav-1.22.1-2-x86_64.pkg.tar.zst
RUN pacman -U --noconfirm gst-libav-1.22.1-2-x86_64.pkg.tar.zst
RUN pacman -S --noconfirm --noprogressbar --quiet --needed gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav gst-python

COPY . /opt/qrlipsync

RUN cd /opt/qrlipsync && pip install -e '.[testing]'

WORKDIR /opt/src
