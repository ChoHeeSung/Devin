#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 로그 디렉토리 생성
mkdir -p logs

# GStreamer 설치 확인
if ! command -v gst-launch-1.0 &> /dev/null; then
    echo -e "${RED}GStreamer is not installed.${NC}"
    echo -e "${YELLOW}Installing GStreamer...${NC}"
    
    # OS 확인
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt-get update
        sudo apt-get install -y \
            gstreamer1.0-tools \
            gstreamer1.0-plugins-base \
            gstreamer1.0-plugins-good \
            gstreamer1.0-plugins-bad \
            gstreamer1.0-plugins-ugly \
            gstreamer1.0-libav
    else
        echo -e "${RED}Unsupported operating system. Please install GStreamer manually.${NC}"
        exit 1
    fi
fi

# Python 패키지 설치 확인
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Setting up virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install Python packages.${NC}"
        exit 1
    fi
else
    source venv/bin/activate
fi

# 서버 시작
echo -e "${GREEN}RTSP 서버를 시작합니다...${NC}"
python3 src/server.py

# 에러 처리
if [ $? -ne 0 ]; then
    echo -e "${RED}Server stopped with an error.${NC}"
    exit 1
fi 