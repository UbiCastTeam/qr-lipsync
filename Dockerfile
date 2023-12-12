FROM archlinux:latest

ENV IN_QRLIPSYNC 1

ENV LANG=C.UTF-8

RUN \
    pacman -Sy && \
    pacman -S archlinux-keyring --noconfirm --noprogressbar --quiet --needed && \
    pacman -Su --noconfirm --noprogressbar --quiet && \
    pacman -S --noconfirm --noprogressbar --quiet --needed \
		git vim curl python-setuptools python-pip python-gobject python-numpy \
		qrencode zbar make

# <WORKAROUND> temporary fix: stick to ffmpeg 6.0 | refs #39001
RUN curl -L -O "https://archive.archlinux.org/packages/d/dav1d/dav1d-1.2.1-1-x86_64.pkg.tar.zst"
RUN pacman -U --noconfirm "dav1d-1.2.1-1-x86_64.pkg.tar.zst"

RUN curl -L -O "https://archive.archlinux.org/packages/r/rav1e/rav1e-0.6.6-1-x86_64.pkg.tar.zst"
RUN pacman -U --noconfirm "rav1e-0.6.6-1-x86_64.pkg.tar.zst"

RUN curl -L -O "https://archive.archlinux.org/packages/f/ffmpeg/ffmpeg-2:6.0-9-x86_64.pkg.tar.zst"
RUN pacman -U --noconfirm "ffmpeg-2:6.0-9-x86_64.pkg.tar.zst"
# </WORKAROUND>

RUN pacman -S --noconfirm --noprogressbar --quiet --needed \
		gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad \
		gst-plugins-ugly gst-libav gst-python

COPY . /opt/qrlipsync

RUN cd /opt/qrlipsync && pip install --break-system-packages -e '.[testing]'

WORKDIR /opt/src
