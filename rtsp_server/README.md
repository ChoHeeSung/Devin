# RTSP 스트리밍 서버

이 프로젝트는 RTSP 스트림을 수신하여 다른 RTSP 스트림으로 전달하는 서버입니다. FFmpeg를 사용하여 스트림을 바이패스 모드로 처리하며, 온디맨드 방식으로 리소스를 효율적으로 관리합니다.

## 주요 기능

- RTSP 스트림 수신 및 전달
- 온디맨드 스트리밍 지원
- 멀티 클라이언트 지원
- 설정 파일을 통한 유연한 스트림 관리
- Docker 컨테이너 지원
- 자동 유휴 스트림 정리
- 상세한 로깅 시스템

## 요구사항

- Python 3.9 이상
- FFmpeg
- Docker (선택사항)

## 설치 및 실행

### 로컬 환경에서 실행

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. FFmpeg 설치:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

3. 서버 실행:
```bash
# 실행 스크립트 사용
./start.sh

# 또는 직접 실행
python src/server.py
```

### Docker를 사용한 실행

1. Docker 이미지 빌드 및 실행:
```bash
docker-compose up --build
```

## 설정

`config/config.json` 파일에서 서버 설정을 관리할 수 있습니다:

### 전역 설정
```json
{
    "global_settings": {
        "on_demand": {
            "enabled": true,
            "default_max_clients": 5,
            "default_idle_timeout": 300,
            "default_buffer_size": "5M"
        },
        "stream_settings": {
            "default_codec": "copy",
            "default_format": "rtsp",
            "reconnect_attempts": 3,
            "reconnect_delay": 5
        }
    }
}
```

### 스트림별 설정
```json
{
    "streams": {
        "금곡IC": {
            "input_url": "rtsp://input_stream_url",
            "output_path": "/금곡IC",
            "on_demand": true,
            "max_clients": 10,
            "idle_timeout": 300,
            "buffer_size": "10M"
        }
    }
}
```

## 설정 옵션 설명

### 전역 설정
- `on_demand.enabled`: 온디맨드 모드 활성화 여부
- `on_demand.default_max_clients`: 기본 최대 클라이언트 수
- `on_demand.default_idle_timeout`: 기본 유휴 타임아웃 (초)
- `on_demand.default_buffer_size`: 기본 버퍼 크기
- `stream_settings.default_codec`: 기본 코덱 설정
- `stream_settings.default_format`: 기본 포맷 설정
- `stream_settings.reconnect_attempts`: 재연결 시도 횟수
- `stream_settings.reconnect_delay`: 재연결 시도 간격 (초)

### 스트림별 설정
- `input_url`: 입력 RTSP 스트림 URL
- `output_path`: 출력 RTSP 스트림 경로
- `on_demand`: 스트림별 온디맨드 설정
- `max_clients`: 스트림별 최대 클라이언트 수
- `idle_timeout`: 스트림별 유휴 타임아웃 (초)
- `buffer_size`: 스트림별 버퍼 크기

## 스트림 접근

설정된 스트림은 다음 URL 형식으로 접근할 수 있습니다:
```
rtsp://localhost:8554/금곡IC
```

## 로깅

로그 파일은 `logs/rtsp_server.log`에 저장됩니다. 로그 레벨과 포맷은 `config.json`의 `logging` 섹션에서 설정할 수 있습니다.

## 모니터링

서버는 다음 정보를 모니터링합니다:
- 활성 스트림 수
- 각 스트림별 연결된 클라이언트 수
- 스트림 시작/중지 이벤트
- 에러 및 경고 메시지

## 라이선스

MIT License 