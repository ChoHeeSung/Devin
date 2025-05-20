FROM ubuntu:22.04

# Python 버전 설정
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Seoul

# GStreamer 환경 변수 설정
ENV GST_DEBUG=3
ENV GST_DEBUG_DUMP_DOT_DIR=/app/logs
ENV GST_DEBUG_NO_COLOR=1

# Python 및 GStreamer 설치
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    python3-gi \
    python3-gst-1.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-rtsp-server-1.0 \
    libgstrtspserver-1.0-dev \
    python3-cairo-dev \
    libcairo2-dev \
    pkg-config \
    meson \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 생성
WORKDIR /app

# 소스 코드 복사
COPY src/ /app/src/
COPY config/ /app/config/
COPY requirements.txt /app/

# Python 패키지 설치
RUN pip3 install --no-cache-dir -r requirements.txt

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 포트 노출
EXPOSE 8554

# 시스템 리소스 제한 설정
RUN echo "* soft nofile 65535" >> /etc/security/limits.conf && \
    echo "* hard nofile 65535" >> /etc/security/limits.conf

# 실행 명령
CMD ["python3", "src/server.py"] 