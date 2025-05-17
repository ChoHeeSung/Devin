# RTSP to RTSP Streaming Server

이 프로젝트는 RTSP 스트림을 입력으로 받아 RTSP 스트림으로 출력하는 서버를 구현합니다. 
FFmpeg을 사용하여 저지연 RTSP 스트리밍을 제공합니다.

## 주요 기능

- RTSP 입력 스트림을 RTSP 출력 스트림으로 변환
- 데이터베이스에서 스트림 정보 로드 (데이터베이스 연결 실패 시 Config 파일 사용)
- 온디맨드 스트리밍 설정 지원 (서버 부하 감소)
- FFmpeg을 활용한 저지연 스트리밍
- Docker 환경에서 손쉬운 배포 및 테스트

## 기술 스택

- Go 1.24.2
- FFmpeg
- Docker
- RTSP 프로토콜

## 프로젝트 구조

```
RtspToRtsp/
├── config/           # 설정 파일
│   └── config.json   # 메인 설정 파일
├── logs/             # 로그 파일 디렉토리
├── streams/          # 스트림 임시 파일 디렉토리
├── src/              # 소스 코드
│   ├── main.go       # 메인 애플리케이션 진입점
│   ├── http.go       # HTTP 서버 관련 코드
│   ├── stream.go     # 스트리밍 관련 코드
│   ├── config.go     # 설정 관련 코드
│   ├── status.go     # 상태 관리 및 API 관련 코드
│   └── gstreamer.go  # FFmpeg RTSP 서버 구현 (파일명은 유지)
├── Dockerfile        # Docker 빌드 파일
├── docker-compose.yml # Docker 구성 파일
└── start.sh          # 시작 스크립트
```

## 설치 및 실행

### 요구 사항

- Docker 및 docker-compose가 설치된 환경

### Docker를 사용한 실행

1. 이 리포지토리를 클론합니다:
   ```bash
   git clone <repository-url>
   cd RtspToRtsp
   ```

2. Docker 컨테이너를 빌드하고 시작합니다:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. 로그를 확인합니다:
   ```bash
   docker-compose logs -f
   ```

## 설정

### config.json

설정 파일은 `config/config.json`에 위치하며 다음과 같은 구조를 가집니다:

```json
{
  "server": {
    "http_port": ":8083",
    "rtsp_port": ":8554",
    "ice_servers": [
      "stun:stun.l.google.com:19302"
    ]
  },
  "stream_defaults": {
    "on_demand": true,
    "disable_audio": true,
    "debug": false
  },
  "api": {
    "cctv_master_url": "http://example.com/api",
    "retry_interval": 30,
    "timeout": 10
  },
  "streams": {
    "stream1": {
      "url": "rtsp://example.com/stream1"
    },
    "stream2": {
      "url": "rtsp://example.com/stream2"
    }
  }
}
```

## RTSP URL 구조

RTSP 스트림은 다음과 같은 URL 형식으로 접근할 수 있습니다:

```
rtsp://서버IP:8554/스트림UUID
```

예를 들어:
- 금곡IC 스트림: `rtsp://서버IP:8554/금곡IC`
- TEST2 스트림: `rtsp://서버IP:8554/TEST2` 또는 `rtsp://서버IP:8554/test2` (대소문자 구분 없음)

스트림 UUID는 config.json 파일의 "streams" 섹션에 정의된 키 값입니다. 스트림 접근 시 대소문자를 구분하지 않으므로 "TEST2"와 "test2"는 동일한 스트림으로 인식됩니다.

## API 엔드포인트

### RTSP 스트림 정보 조회

```
GET /stream/rtsp/:uuid
```

응답 예시:
```json
{
  "uuid": "stream1",
  "rtsp_url": "rtsp://server-ip:8554/stream1",
  "status": true
}
```

### 스트림 상태 조회

```
GET /stream/api/status
```

응답 예시:
```json
{
  "streams": [
    {
      "uuid": "stream1",
      "url": "rtsp://example.com/stream1",
      "status": true,
      "onDemand": true,
      "disableAudio": true,
      "debug": false,
      "viewerCount": 0,
      "lastUpdated": "2025-05-17T00:00:00Z",
      "isRunning": true,
      "reconnectCount": 0
    }
  ],
  "total": 1,
  "activeCount": 1
}
```

## 구현 상세

### RTSP 서버 구현

이 프로젝트는 FFmpeg을 사용하여 RTSP 서버를 구현하고 저지연 스트리밍을 최적화합니다:

1. **FFmpeg 파이프라인**: 각 스트림에 대해 저지연 최적화된 파이프라인을 생성합니다.
2. **온디맨드 스트리밍**: 클라이언트 요청이 있을 때만 스트림을 시작하여 서버 리소스를 절약합니다.
3. **대소문자 구분 없는 스트림 접근**: 스트림 UUID 검색 시 대소문자를 구분하지 않습니다.
4. **직접 스트림 전달**: 소스 RTSP 스트림을 FFmpeg을 통해 직접 RTSP로 전달하여 안정성과 성능을 높입니다.

### 저지연 RTSP 스트리밍 설정

FFmpeg을 사용하여 다음과 같은 저지연 설정을 적용했습니다:

- `-rtsp_transport tcp`: 더 안정적인 전송을 위해 TCP 프로토콜 사용
- `-c:v copy`: 비디오 트랜스코딩 없이 직접 복사하여 지연 최소화
- `-c:a copy`: 오디오 트랜스코딩 없이 직접 복사하여 지연 최소화
- `-muxdelay 0.1`: 멀티플렉싱 지연을 최소화하여 전체 지연 감소

### 구현 아키텍처

```
[소스 RTSP 스트림] → [FFmpeg] → [RTSP 출력] → [클라이언트]
```

1. 소스 RTSP 스트림에서 데이터를 가져옵니다.
2. FFmpeg을 통해 저지연 최적화를 적용합니다.
3. RTSP 출력을 통해 클라이언트에게 스트림을 전달합니다.
4. 온디맨드 설정이 활성화된 경우, 클라이언트 요청이 있을 때만 스트림을 시작합니다.

### FFmpeg 명령어 구조

각 스트림은 다음과 같은 FFmpeg 명령어로 처리됩니다:

```
ffmpeg -nostdin -loglevel warning -rtsp_transport tcp -i rtsp://example.com/stream \
  -c:v copy -c:a copy -f rtsp -rtsp_transport tcp -muxdelay 0.1 \
  rtsp://0.0.0.0:8554/stream
```

이 명령어는 다음과 같은 구성 요소로 이루어져 있습니다:

1. **입력 옵션**: 소스 RTSP 스트림에 연결하기 위한 설정
   - `-nostdin`: 표준 입력 비활성화
   - `-loglevel warning`: 로그 레벨 설정
   - `-rtsp_transport tcp`: RTSP 전송에 TCP 사용
   - `-i rtsp://example.com/stream`: 입력 스트림 URL

2. **출력 옵션**: RTSP 출력 스트림 설정
   - `-c:v copy`: 비디오 코덱 복사 (트랜스코딩 없음)
   - `-c:a copy`: 오디오 코덱 복사 (트랜스코딩 없음)
   - `-f rtsp`: RTSP 출력 형식
   - `-rtsp_transport tcp`: 출력 RTSP 전송에 TCP 사용
   - `-muxdelay 0.1`: 멀티플렉싱 지연 최소화
   - `rtsp://0.0.0.0:8554/stream`: 출력 RTSP URL
