FROM vascoguita/raspios:arm64-trixie

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Remove the preinstalled rpicam-apps package and install the
# dependencies required to build rpicam-apps with libav support.
RUN apt-get update \
    && apt-get remove -y rpicam-apps rpicam-apps-lite || true \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        git \
        python3 \
        python3-pip \
        ffmpeg \
        meson \
        ninja-build \
        pkg-config \
        cmake \
        libboost-program-options-dev \
        libdrm-dev \
        libexif-dev \
        libcamera-dev \
        libepoxy-dev \
        libjpeg-dev \
        libtiff-dev \
        libpng-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavformat-dev \
        libswresample-dev \
    && rm -rf /var/lib/apt/lists/*

# Build Raspberry Pi's rpicam-apps with libav enabled.
RUN git clone --depth 1 https://github.com/raspberrypi/rpicam-apps.git /tmp/rpicam-apps \
    && cd /tmp/rpicam-apps \
    && meson setup build \
        --buildtype=release \
        -Denable_libav=enabled \
        -Denable_drm=enabled \
        -Denable_egl=disabled \
        -Denable_qt=disabled \
        -Denable_opencv=disabled \
        -Denable_tflite=disabled \
        -Denable_hailo=disabled \
        -Denable_imx500=false \
    && meson compile -C build \
    && meson install -C build \
    && ldconfig \
    && rm -rf /tmp/rpicam-apps

# Verify that the resulting rpicam build actually has libav support.
RUN rpicam-vid --version \
    && rpicam-hello --version \
    && rpicam-vid --version 2>&1 | grep -q 'libav:1'

WORKDIR /app

COPY requirements.txt .

RUN pip3 install \
        --break-system-packages \
        --no-cache-dir \
        -r requirements.txt

COPY app/ ./app/
COPY config/ ./config/

EXPOSE 8090

CMD ["python3", "-m", "app.main"]