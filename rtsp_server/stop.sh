#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if ps -p $PID > /dev/null; then
        echo -e "${YELLOW}RTSP 서버를 중지합니다... (PID: $PID)${NC}"
        kill $PID
        rm server.pid
        echo -e "${GREEN}서버가 중지되었습니다.${NC}"
    else
        echo -e "${YELLOW}서버가 이미 중지되었습니다.${NC}"
        rm server.pid
    fi
else
    echo -e "${YELLOW}서버가 실행 중이지 않습니다.${NC}"
fi 