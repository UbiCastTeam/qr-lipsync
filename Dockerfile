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
        python-setuptools python-gobject gst-python

RUN mkdir /src
ADD . /src/qrlipsync
WORKDIR /src

RUN \
    git clone https://github.com/UbiCastTeam/gst-qroverlay.git && \
    cd gst-qroverlay && ./autogen.sh && ./configure --prefix=/usr && make install && cd .. && \
    cd qrlipsync && python -m unittest && python setup.py install --root=/
