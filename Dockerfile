FROM archlinux/base

RUN echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen && locale-gen

ENV LANG=en_US.UTF-8

RUN \
    pacman -Sy && \
    pacman -S archlinux-keyring --noconfirm --noprogressbar --quiet --needed && \
    pacman -S pacman --noconfirm --noprogressbar --quiet && \
    pacman-db-upgrade && \
    pacman -Su --noconfirm --noprogressbar --quiet && \
    pacman -S --noconfirm --noprogressbar --quiet --needed \
        git base-devel vim \
        gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav \
        qrencode zbar ffmpeg \
        python-setuptools python-pip python-gobject gst-python

RUN \
    git clone https://github.com/UbiCastTeam/gst-qroverlay.git && \
    cd gst-qroverlay && ./autogen.sh && ./configure --prefix=/usr && make install && cd .. && rm -rf gst-qroverlay/ && \
    mkdir src/

COPY . /src/qrlipsync
WORKDIR /src/qrlipsync

RUN pip install -e '.[testing]'
