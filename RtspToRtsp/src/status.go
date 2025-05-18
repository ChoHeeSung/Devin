package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

var startTime = time.Now()

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

func HandleStreamStatus(w http.ResponseWriter, r *http.Request) {
	Config.mutex.RLock()
	defer Config.mutex.RUnlock()

	var response StatusResponse
	response.Streams = make([]StreamStatusInfo, 0, len(Config.Streams))

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
			RtspUrl:        rtspURL,
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

func HandleSingleStreamStatus(w http.ResponseWriter, r *http.Request, uuid string) {
	Config.mutex.RLock()
	defer Config.mutex.RUnlock()

	stream, ok := Config.Streams[uuid]
	if !ok {
		http.Error(w, "Stream not found", http.StatusNotFound)
		return
	}

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
		RtspUrl:        rtspURL,
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

	Config.mutex.RLock()
	for _, stream := range Config.Streams {
		stats.ViewerCount += len(stream.Cl)
	}
	Config.mutex.RUnlock()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}
