package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
)

type RTSPStreamInfo struct {
	UUID    string `json:"uuid"`
	RTSPURL string `json:"rtsp_url"`
	Status  bool   `json:"status"`
}

func GetRTSPURLForAPI(uuid string, hostname string) (string, error) {
	if idx := strings.Index(hostname, ":"); idx > 0 {
		hostname = hostname[:idx]
	}
	
	var streamUUID string
	var streamFound bool
	
	Config.mutex.RLock()
	defer Config.mutex.RUnlock()
	
	for existingUUID := range Config.Streams {
		if strings.EqualFold(existingUUID, uuid) {
			streamUUID = existingUUID
			streamFound = true
			break
		}
	}
	
	if !streamFound {
		return "", fmt.Errorf("Stream not found: %s", uuid)
	}
	
	rtspPort := Config.Server.RTSPPort
	if rtspPort[0] == ':' {
		rtspPort = rtspPort[1:]
	}
	
	return fmt.Sprintf("rtsp://%s:%s/%s", hostname, rtspPort, streamUUID), nil
}

func HandleRTSPStreamInfo(w http.ResponseWriter, r *http.Request, uuid string) {
	Config.mutex.RLock()
	defer Config.mutex.RUnlock()

	var streamUUID string
	var streamFound bool

	for existingUUID := range Config.Streams {
		if strings.EqualFold(existingUUID, uuid) {
			streamUUID = existingUUID
			streamFound = true
			break
		}
	}

	if !streamFound {
		http.Error(w, "Stream not found", http.StatusNotFound)
		return
	}

	stream := Config.Streams[streamUUID]

	if stream.OnDemand {
		go func() {
			if err := RunIFNotRun(streamUUID); err != nil {
				log.Printf("온디맨드 스트림 시작 실패 %s: %v", streamUUID, err)
			}
		}()
	}

	rtspURL, err := GetRTSPURLForAPI(streamUUID, r.Host)
	if err != nil {
		http.Error(w, "Failed to get RTSP URL", http.StatusInternalServerError)
		return
	}

	info := RTSPStreamInfo{
		UUID:    streamUUID,
		RTSPURL: rtspURL,
		Status:  stream.Status,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(info)
}
