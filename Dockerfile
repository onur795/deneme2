FROM ubuntu:24.04

# Metadata
LABEL maintainer="PlutoSDR Sensor"
LABEL description="PlutoSDR FMCW Radar Presence Sensor"
LABEL version="1.0"

# Timezone ayarla
ENV TZ=Europe/Istanbul
ENV DEBIAN_FRONTEND=noninteractive

# Sistem paketlerini güncelle ve gerekli paketleri kur
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    python3-dev \
    libusb-1.0-0-dev \
    libxml2-dev \
    liborc-0.4-dev \
    gnuradio \
    gnuradio-dev \
    libboost-all-dev \
    wget \
    udev \
    && rm -rf /var/lib/apt/lists/*

# libiio kurulumu
WORKDIR /tmp
RUN git clone https://github.com/analogdevicesinc/libiio.git && \
    cd libiio && \
    cmake . && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd .. && rm -rf libiio

# gr-iio kurulumu
RUN git clone https://github.com/analogdevicesinc/gr-iio.git && \
    cd gr-iio && \
    mkdir build && cd build && \
    cmake .. && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd ../.. && rm -rf gr-iio

# Python bağımlılıkları
RUN pip3 install --no-cache-dir --break-system-packages \
    numpy \
    scipy \
    matplotlib \
    scikit-learn \
    flask \
    flask-socketio \
    flask-cors \
    pandas \
    pyadi-iio \
    pillow \
    seaborn \
    python-socketio \
    simple-websocket

# Çalışma dizini oluştur
WORKDIR /app

# Uygulama dosyalarını kopyala
COPY signal_processor.py /app/
COPY train_model.py /app/
COPY web_server.py /app/
COPY dashboard.html /app/
COPY test_pluto.py /app/

# Model eğitimi (ilk çalıştırmada)
RUN python3 /app/train_model.py

# USB cihazlar için yetki
RUN mkdir -p /etc/udev/rules.d

# Port aç
EXPOSE 5000

# Başlangıç komutu
CMD ["python3", "/app/web_server.py"]

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1
