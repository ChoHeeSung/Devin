package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"
)

type RTSPStreamInfo struct {
	UUID    string `json:"uuid"`
	RTSPURL string `json:"rtsp_url"`
	Status  bool   `json:"status"`
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

	rtspURL, err := GetRTSPURL(streamUUID, r.Host)
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
