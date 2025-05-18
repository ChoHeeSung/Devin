package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// startTime은 서버 시작 시간을 저장하는 전역 변수입니다.
var startTime = time.Now()

// StreamStatusInfo는 API 응답에서 사용되는 스트림 상태 정보 구조체입니다.
// StreamST 구조체의 모든 필드를 포함하도록 설계되었습니다.
type StreamStatusInfo struct {
	UUID           string    `json:"uuid"`
	URL            string    `json:"url"`
	RtspUrl        string    `json:"rtspUrl"`
	Status         bool      `json:"status"`
	OnDemand       bool      `json:"onDemand"`
	DisableAudio   bool      `json:"disableAudio"`
	Debug          bool      `json:"debug"`
	LastError      error     `json:"lastError,omitempty"`
	LastUpdated    time.Time `json:"lastUpdated"`
	ViewerCount    int       `json:"viewerCount"`
	IsRunning      bool      `json:"isRunning"`
	ReconnectCount int       `json:"reconnectCount"`
}

type StatusResponse struct {
	Streams     []StreamStatusInfo `json:"streams"`
	Total       int                `json:"total"`
	ActiveCount int                `json:"active_count"`
}

// HandleStreamStatus는 모든 스트림의 상태를 반환하는 HTTP 핸들러입니다.
func HandleStreamStatus(w http.ResponseWriter, r *http.Request) {
	Config.mutex.RLock()
	defer Config.mutex.RUnlock()

	var response StatusResponse
	response.Streams = make([]StreamStatusInfo, 0, len(Config.Streams))

	// StreamST 구조체의 모든 필드를 StreamStatusInfo로 복사
	for uuid, stream := range Config.Streams {
		hostname := r.Host
		if idx := strings.Index(hostname, ":"); idx > 0 {
			hostname = hostname[:idx]
		}
		
		rtspPort := Config.Server.RTSPPort
		if rtspPort[0] == ':' {
			rtspPort = rtspPort[1:]
		}
		
		rtspURL := fmt.Sprintf("rtsp://%s:%s/%s", hostname, rtspPort, uuid)
		
		status := StreamStatusInfo{
			UUID:           uuid,
			URL:            stream.URL,
			RTSPURL:        rtspURL,
			Status:         stream.Status,
			OnDemand:       stream.OnDemand,
			DisableAudio:   stream.DisableAudio,
			Debug:          stream.Debug,
			LastError:      stream.LastError,
			LastUpdated:    stream.LastUpdated,
			ViewerCount:    stream.ViewerCount,
			IsRunning:      stream.IsRunning,
			ReconnectCount: stream.ReconnectCount,
		}
		response.Streams = append(response.Streams, status)
		if stream.Status {
			response.ActiveCount++
		}
	}
	response.Total = len(response.Streams)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// HandleSingleStreamStatus는 특정 스트림의 상태를 반환하는 HTTP 핸들러입니다.
func HandleSingleStreamStatus(w http.ResponseWriter, r *http.Request, uuid string) {
	Config.mutex.RLock()
	defer Config.mutex.RUnlock()

	stream, ok := Config.Streams[uuid]
	if !ok {
		http.Error(w, "Stream not found", http.StatusNotFound)
		return
	}

	// StreamST 구조체의 모든 필드를 StreamStatusInfo로 복사
	hostname := r.Host
	if idx := strings.Index(hostname, ":"); idx > 0 {
		hostname = hostname[:idx]
	}
	
	rtspPort := Config.Server.RTSPPort
	if rtspPort[0] == ':' {
		rtspPort = rtspPort[1:]
	}
	
	rtspURL := fmt.Sprintf("rtsp://%s:%s/%s", hostname, rtspPort, uuid)
	
	status := StreamStatusInfo{
		UUID:           uuid,
		URL:            stream.URL,
		RTSPURL:        rtspURL,
		Status:         stream.Status,
		OnDemand:       stream.OnDemand,
		DisableAudio:   stream.DisableAudio,
		Debug:          stream.Debug,
		LastError:      stream.LastError,
		LastUpdated:    stream.LastUpdated,
		ViewerCount:    stream.ViewerCount,
		IsRunning:      stream.IsRunning,
		ReconnectCount: stream.ReconnectCount,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// HandleServerStats는 서버 통계 정보를 반환하는 HTTP 핸들러입니다.
func HandleServerStats(w http.ResponseWriter, r *http.Request) {
	stats := struct {
		Uptime      time.Duration `json:"uptime"`
		StreamCount int           `json:"stream_count"`
		ViewerCount int           `json:"viewer_count"`
		LastUpdated time.Time     `json:"last_updated"`
	}{
		Uptime:      time.Since(startTime),
		StreamCount: len(Config.Streams),
		LastUpdated: time.Now(),
	}

	// StreamST 구조체의 Cl 필드를 참고하여 시청자 수 계산
	Config.mutex.RLock()
	for _, stream := range Config.Streams {
		stats.ViewerCount += len(stream.Cl)
	}
	Config.mutex.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}
