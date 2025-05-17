# MTX-STREAMING

RTSP 스트림을 WebRTC를 통해 웹 브라우저로 전송하는 프로젝트입니다 (Pion 기반, 완전 네이티브! ffmpeg나 gstreamer를 사용하지 않음).

## 프로젝트 구조

```
.
├── web/                # 웹 클라이언트 관련 파일
│   ├── static/        # 정적 파일 (이미지, CSS, JS 등)
│   └── templates/     # HTML 템플릿
├── src/               # 소스 코드
│   ├── main.go        # 메인 애플리케이션 진입점
│   ├── http.go        # HTTP 서버 관련 코드
│   ├── stream.go      # 스트리밍 관련 코드
│   ├── config.go      # 설정 관련 코드
│   ├── status.go      # 상태 관리 및 API 관련 코드
│   ├── api/           # API 관련 코드
│   ├── go.mod         # Go 모듈 정의
│   └── go.sum         # Go 모듈 체크섬
├── config/            # 설정 파일
│   └── config.json    # 서버 설정 파일
├── logs/              # 로그 파일 디렉토리
├── Dockerfile         # Docker 이미지 빌드 설정
├── docker-compose.yml # Docker Compose 설정
├── start.sh           # 실행 스크립트
└── README.md          # 프로젝트 문서
```

## 시작하기

### 필수 요구사항

- Go 1.18 이상
- Docker (선택사항)

### 설치 및 실행

1. 의존성 설치
   ```bash
   go mod download
   ```

2. 서버 실행
   ```bash
   # 직접 실행
   go run *.go
   
   # 또는 스크립트 사용
   ./start.sh
   ```

3. Docker를 통한 실행
   ```bash
   # 이미지 빌드
   docker build -t mtx-streaming .
   
   # 컨테이너 실행
   docker run -p 8083:8083 mtx-streaming
   ```

4. 브라우저에서 접속
   ```
   http://localhost:8083
   ```

## 설정

### config.json 설정

프로젝트 루트의 `config/config.json` 파일을 수정하여 서버 설정을 변경할 수 있습니다:

```json
{
  "server": {
    "http_port": ":8083",
    "ice_servers": ["stun:stun.l.google.com:19302"]
  },
  "stream_defaults": {
    "on_demand": false,
    "disable_audio": true,
    "debug": false
  },
  "api": {
    "cctv_master_url": "http://192.168.1.251/its/basic/device/cctvMaster/select",
    "retry_interval": 30,
    "timeout": 10
  },
  "streams": {
    "금곡IC": {
      "url": "rtsp://183.101.40.92/live/1.stream"
    },
    "TEST2": {
      "url": "rtsp://183.101.40.92/live/2.stream"
    }
  }
}
```

## 실시간 스트림

여러 클라이언트가 연결될 때 끊김 현상과 성능 문제를 방지하려면 `"on_demand": false` 옵션을 사용하세요.

## 스트리밍 상태 모니터링 API

스트리밍 서비스의 상태를 모니터링하기 위한 API가 제공됩니다.

### 모든 스트림 상태 조회

```
GET /stream/api/status
```

응답 예시:
```json
{
  "streams": [
    {
      "uuid": "금곡IC",
      "url": "rtsp://183.101.40.92/live/1.stream",
      "status": true,
      "on_demand": false,
      "disable_audio": true,
      "debug": false,
      "viewer_count": 2,
      "last_error": null,
      "last_updated": "2023-04-23T08:30:00Z",
      "is_running": true,
      "reconnect_count": 0
    }
  ],
  "total": 1
}
```

### 특정 스트림 상태 조회

```
GET /stream/api/status/:uuid
```

응답 예시:
```json
{
  "uuid": "금곡IC",
  "url": "rtsp://183.101.40.92/live/1.stream",
  "status": true,
  "on_demand": false,
  "disable_audio": true,
  "debug": false,
  "viewer_count": 2,
  "last_error": null,
  "last_updated": "2023-04-23T08:30:00Z",
  "is_running": true,
  "reconnect_count": 0
}
```

### 서버 상태 모니터링 API

서버의 시스템 리소스 사용량과 런타임 정보를 모니터링하기 위한 API가 제공됩니다.

```
GET /stream/api/server/stats
```

응답 예시:
```json
{
  "cpu": {
    "load_avg_1": 1.5,
    "load_avg_5": 1.2,
    "load_avg_15": 1.0,
    "num_cpu": 4
  },
  "memory": {
    "total": 8589934592,
    "used": 4294967296,
    "free": 4294967296,
    "usage_percent": 50.0
  },
  "go_runtime": {
    "version": "go1.18",
    "num_goroutine": 10,
    "gomaxprocs": 4,
    "num_cpu": 4,
    "cgo_calls": 100,
    "num_gc": 5,
    "heap_objects": 10000,
    "heap_alloc": 10485760,
    "heap_sys": 20971520
  },
  "process": {
    "num_fd": 10,
    "num_threads": 5,
    "virtual_size": 1073741824,
    "resident_size": 536870912,
    "cpu_time": 10.5
  },
  "network": {
    "bytes_sent": 1048576,
    "bytes_received": 2097152,
    "packets_sent": 1000,
    "packets_received": 2000,
    "bytes_sent_rate": 1024.0,
    "bytes_received_rate": 2048.0,
    "last_update": "2023-04-23T08:30:00Z"
  },
  "uptime": 3600.5
}
```

## 로그 관리 시스템

MTX-STREAMING은 자동화된 로그 관리 시스템을 제공합니다.

### 주요 기능

1. **로그 파일 자동 로테이션**
   - 로그 파일 크기가 10MB를 초과하면 자동으로 로테이션
   - 로그 파일명에 날짜와 시간 정보 포함

2. **로그 파일 압축 및 정리**
   - 7일이 지난 로그 파일은 자동으로 압축
   - 30일이 지난 압축 파일은 자동으로 삭제

3. **로그 저장 위치**
   - 로그 파일은 `logs` 디렉토리에 저장
   - 로그 파일명 형식: `YYYY-MM-DD_HH-MM-SS.log`

## 상태 관리 시스템

MTX-STREAMING은 스트림의 상태를 실시간으로 추적하고 관리하는 강력한 상태 관리 시스템을 제공합니다.

### 주요 기능

1. **스트림 상태 추적**
   - 실행 상태 모니터링
   - 에러 발생 시 자동 감지
   - 시청자 수 실시간 추적
   - 재연결 시도 횟수 기록

2. **자동 복구 메커니즘**
   - 연결 끊김 감지
   - 자동 재연결 시도
   - 재연결 실패 시 로깅

3. **성능 최적화**
   - 뮤텍스 기반 동시성 제어
   - 읽기/쓰기 락 분리로 성능 향상
   - 메모리 사용량 최적화

4. **모니터링 및 알림**
   - API 기반 상태 조회
   - 실시간 상태 변경 감지
   - 서버 리소스 사용량 모니터링

### 상태 관리 API 사용 예시

```bash
# 모든 스트림 상태 조회
curl http://localhost:8083/stream/api/status

# 특정 스트림 상태 조회
curl http://localhost:8083/stream/api/status/금곡IC

# 서버 통계 정보 조회
curl http://localhost:8083/stream/api/server/status
```

## 제한사항

- 지원되는 비디오 코덱: H264
- 지원되는 오디오 코덱: pcm alaw 및 pcm mulaw
- 현재 Chrome, Safari, Firefox에서 테스트 완료
- MAC OS에서는 작동하지 않음

## 라이선스

MIT License

## 스트리밍 주소 체계

### 기본 URL 구조
```
http://[서버주소]:[포트]/stream/player/[스트림ID]
```

### 구성 요소 설명
- 서버주소: 기본값 `127.0.0.1` (로컬호스트)
- 포트: 기본값 `8083` (config.json에서 설정)
- 스트림ID: config.json의 streams 섹션에 정의된 스트림 식별자

### 예시 URL
```
http://127.0.0.1:8083/stream/player/금곡IC
```

### 주요 특징
- URL의 스트림ID는 config.json에 정의된 키와 일치해야 합니다
- 한글 스트림ID는 URL 인코딩되어 전송됩니다 (예: 금곡IC -> %ea%b8%88%ea%b3%a1IC)
- on_demand 옵션으로 스트림의 요청 시 시작 여부를 제어할 수 있습니다
- disable_audio 옵션으로 오디오 스트리밍 여부를 제어할 수 있습니다

### 지원되는 코덱
- 비디오: H264
- 오디오: pcm alaw, pcm mulaw, opus
