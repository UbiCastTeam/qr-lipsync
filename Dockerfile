FROM archlinux:latest

ENV IN_QRLIPSYNC=1

ENV LANG=C.UTF-8

RUN \
    pacman -Sy && \
    pacman -S archlinux-keyring --noconfirm --noprogressbar --quiet --needed && \
    pacman -Su --noconfirm --noprogressbar --quiet && \
    pacman -S --noconfirm --noprogressbar --quiet --needed \
        git vim qrencode zbar make \
        gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav \
        python-virtualenv python-gobject gst-python

RUN python -m venv /opt/venv --system-site-packages
ENV PATH="/opt/venv/bin:/usr/sbin:/usr/bin:/sbin:/bin"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY . /opt/src
WORKDIR /opt/src
RUN pip install -e '.[dev]'
