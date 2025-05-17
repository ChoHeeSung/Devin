FROM golang:1.24.2

WORKDIR /go/src/app

# Install GStreamer and dependencies
RUN apt-get update && apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-rtsp \
    libgstreamer1.0-dev \
    libgstrtspserver-1.0-dev \
    pkg-config \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Go 모듈 시스템 활성화
ENV GO111MODULE=on
ENV GIN_MODE=release

# 소스 코드 복사
COPY . .

# Go 모듈 초기화 및 의존성 설치
RUN go mod init mtx-streaming
RUN go mod tidy
RUN go build -v ./...

EXPOSE 8083
EXPOSE 8554

ENTRYPOINT ["/bin/bash", "/go/src/app/start.sh"]
