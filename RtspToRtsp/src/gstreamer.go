package main

import (
	"fmt"
	"log"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// GStreamerStream represents a single RTSP stream
type GStreamerStream struct {
	UUID         string
	URL          string
	OnDemand     bool
	Status       bool
	StartTime    time.Time
	Viewers      int
	LowLatency   bool
	GstPipeline  *exec.Cmd
	RtspServer   *exec.Cmd
}

var (
	streams        map[string]*GStreamerStream
	serverMutex    sync.RWMutex
	serverPort     string
	serverStarted  time.Time
	serverRunning  bool
	mainRtspServer *exec.Cmd
)

func StartGStreamerServer(port string) error {
	serverMutex.Lock()
	defer serverMutex.Unlock()
	
	streams = make(map[string]*GStreamerStream)
	serverPort = port
	serverStarted = time.Now()
	serverRunning = true

	rtspServerCmd := fmt.Sprintf(
		"test-launch \"( videotestsrc is-live=true ! video/x-raw,width=640,height=480,framerate=30/1 ! "+
		"x264enc tune=zerolatency bitrate=500 speed-preset=superfast ! rtph264pay name=pay0 pt=96 )\"")
	
	cmd := exec.Command("gst-rtsp-launch", "-p", port)
	
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("RTSP 서버 시작 실패: %v", err)
	}
	
	mainRtspServer = cmd
	
	log.Printf("GStreamer RTSP 서버가 포트 %s에서 시작되었습니다", port)
	return nil
}

func StopGStreamerServer() {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return
	}

	log.Println("GStreamer RTSP 서버 종료 중...")

	for uuid, stream := range streams {
		if stream.GstPipeline != nil && stream.GstPipeline.Process != nil {
			log.Printf("스트림 종료 중: %s", uuid)
			stream.GstPipeline.Process.Kill()
		}
		if stream.RtspServer != nil && stream.RtspServer.Process != nil {
			stream.RtspServer.Process.Kill()
		}
	}
	
	if mainRtspServer != nil && mainRtspServer.Process != nil {
		mainRtspServer.Process.Kill()
		mainRtspServer = nil
	}

	serverRunning = false
	log.Println("GStreamer RTSP 서버가 종료되었습니다")
}

func RegisterStream(uuid string, url string, onDemand bool) error {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return fmt.Errorf("RTSP 서버가 실행 중이 아닙니다")
	}

	for existingUUID := range streams {
		if strings.EqualFold(existingUUID, uuid) {
			log.Printf("스트림이 이미 다른 대소문자로 등록되어 있습니다: %s vs %s", existingUUID, uuid)
			return nil
		}
	}

	streams[uuid] = &GStreamerStream{
		UUID:        uuid,
		URL:         url,
		OnDemand:    onDemand,
		Status:      false,
		StartTime:   time.Now(),
		Viewers:     0,
		LowLatency:  true,
		GstPipeline: nil,
		RtspServer:  nil,
	}

	log.Printf("RTSP 스트림 등록됨: %s", uuid)

	if !onDemand {
		go func() {
			if err := startStream(uuid); err != nil {
				log.Printf("스트림 시작 실패 %s: %v", uuid, err)
			}
		}()
	}

	return nil
}

func startStream(uuid string) error {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return fmt.Errorf("RTSP 서버가 실행 중이 아닙니다")
	}

	stream, exists := streams[uuid]
	if !exists {
		return fmt.Errorf("스트림을 찾을 수 없습니다: %s", uuid)
	}

	// Check if the stream is already running
	if stream.GstPipeline != nil && stream.GstPipeline.Process != nil {
		return nil // Stream already running
	}

	pipelineStr := fmt.Sprintf(
		"gst-launch-1.0 -v rtspsrc location=\"%s\" latency=0 buffer-mode=0 "+
		"drop-on-latency=true protocols=tcp do-retransmission=false ! "+
		"rtph264depay ! h264parse ! "+
		"rtspclientsink location=rtsp://0.0.0.0:%s/%s "+
		"protocols=tcp latency=0",
		stream.URL, serverPort, uuid)

	log.Printf("Starting GStreamer pipeline for stream %s: %s", uuid, pipelineStr)
	
	cmd := exec.Command("bash", "-c", pipelineStr)
	
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("GStreamer 파이프라인 시작 실패: %v", err)
	}

	stream.GstPipeline = cmd
	stream.Status = true
	stream.StartTime = time.Now()

	log.Printf("스트림 시작됨: %s", uuid)
	return nil
}

func StopStream(uuid string) error {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return fmt.Errorf("RTSP 서버가 실행 중이 아닙니다")
	}

	stream, exists := streams[uuid]
	if !exists {
		return fmt.Errorf("스트림을 찾을 수 없습니다: %s", uuid)
	}

	if stream.GstPipeline != nil && stream.GstPipeline.Process != nil {
		if err := stream.GstPipeline.Process.Kill(); err != nil {
			return fmt.Errorf("GStreamer 파이프라인 종료 실패: %v", err)
		}
		stream.GstPipeline = nil
	}
	
	if stream.RtspServer != nil && stream.RtspServer.Process != nil {
		if err := stream.RtspServer.Process.Kill(); err != nil {
			return fmt.Errorf("RTSP 서버 종료 실패: %v", err)
		}
		stream.RtspServer = nil
	}

	stream.Status = false
	log.Printf("스트림 종료됨: %s", uuid)
	return nil
}

func GetStreamStatus(uuid string) (*GStreamerStream, error) {
	serverMutex.RLock()
	defer serverMutex.RUnlock()

	if !serverRunning {
		return nil, fmt.Errorf("RTSP 서버가 실행 중이 아닙니다")
	}

	stream, exists := streams[uuid]
	if !exists {
		return nil, fmt.Errorf("스트림을 찾을 수 없습니다: %s", uuid)
	}

	return stream, nil
}

func GetAllStreams() map[string]*GStreamerStream {
	serverMutex.RLock()
	defer serverMutex.RUnlock()

	if !serverRunning {
		return nil
	}

	result := make(map[string]*GStreamerStream)
	for uuid, stream := range streams {
		result[uuid] = stream
	}

	return result
}

func GetRTSPURL(uuid string, hostname string) (string, error) {
	serverMutex.RLock()
	defer serverMutex.RUnlock()

	if !serverRunning {
		return "", fmt.Errorf("RTSP 서버가 실행 중이 아닙니다")
	}

	_, exists := streams[uuid]
	if !exists {
		return "", fmt.Errorf("스트림을 찾을 수 없습니다: %s", uuid)
	}

	return fmt.Sprintf("rtsp://%s:%s/%s", hostname, serverPort, uuid), nil
}

// RunIFNotRun starts a stream if it's not already running
func RunIFNotRun(uuid string) error {
	serverMutex.RLock()
	stream, exists := streams[uuid]
	onDemand := exists && stream.OnDemand
	serverMutex.RUnlock()

	if !exists {
		return fmt.Errorf("스트림을 찾을 수 없습니다: %s", uuid)
	}

	if onDemand {
		return startStream(uuid)
	}

	return nil
}
