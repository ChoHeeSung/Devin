FROM golang:1.24.2

WORKDIR /go/src/app

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

ENTRYPOINT ["/bin/bash", "/go/src/app/start.sh"]