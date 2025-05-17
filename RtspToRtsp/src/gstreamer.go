package main

import (
	"fmt"
	"log"
	"net"
	"os"
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
	GstCmd       *exec.Cmd
}

var (
	streams        map[string]*GStreamerStream
	serverMutex    sync.RWMutex
	serverPort     string
	serverStarted  time.Time
	serverRunning  bool
	rtspServerCmd  *exec.Cmd
)

func StartGStreamerServer(port string) error {
	serverMutex.Lock()
	defer serverMutex.Unlock()
	
	if err := os.MkdirAll("streams", 0755); err != nil {
		return fmt.Errorf("스트림 디렉토리 생성 실패: %v", err)
	}
	
	streams = make(map[string]*GStreamerStream)
	serverPort = port
	serverStarted = time.Now()
	serverRunning = true
	
	// Check if GStreamer is installed
	cmd := exec.Command("gst-launch-1.0", "--version")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("GStreamer 확인 실패: %v", err)
	}
	log.Printf("GStreamer 버전: %s", string(output))
	
	
	log.Printf("GStreamer RTSP 서버 준비 완료 (포트: %s)", port)
	return nil
}

func StopGStreamerServer() {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return
	}

	log.Println("RTSP 서버 종료 중...")

	for uuid, stream := range streams {
		if stream.GstCmd != nil && stream.GstCmd.Process != nil {
			log.Printf("스트림 종료 중: %s", uuid)
			stream.GstCmd.Process.Kill()
		}
	}

	serverRunning = false
	log.Println("RTSP 서버가 종료되었습니다")
}

// RegisterStream registers a new RTSP stream
func RegisterStream(uuid string, url string, onDemand bool) error {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return fmt.Errorf("RTSP 서버가 실행 중이 아닙니다")
	}

	// Check if stream already exists (case-insensitive)
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
		GstCmd:      nil,
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

// startStream starts an RTSP stream
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
	if stream.GstCmd != nil && stream.GstCmd.Process != nil {
		return nil // Stream already running
	}

	rtspSocket, err := net.Listen("tcp", fmt.Sprintf(":%s", serverPort))
	if err != nil {
		return fmt.Errorf("RTSP 소켓 생성 실패: %v", err)
	}
	
	rtspSocket.Close()
	
	pipeline := fmt.Sprintf(
		"rtspsrc location=%s latency=0 buffer-mode=0 drop-on-latency=true protocols=tcp do-retransmission=false ! " +
		"rtph264depay ! h264parse ! rtph264pay config-interval=1 pt=96 ! " +
		"tcpserversink host=0.0.0.0 port=%s",
		stream.URL, serverPort)
	
	log.Printf("Starting GStreamer pipeline for %s: %s", uuid, pipeline)
	
	args := append([]string{"-v"}, strings.Split(pipeline, " ")...)
	cmd := exec.Command("gst-launch-1.0", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("GStreamer 시작 실패: %v", err)
	}

	stream.GstCmd = cmd
	stream.Status = true
	stream.StartTime = time.Now()

	log.Printf("스트림 시작됨: %s", uuid)
	return nil
}

// StopStream stops a specific RTSP stream
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

	if stream.GstCmd != nil && stream.GstCmd.Process != nil {
		if err := stream.GstCmd.Process.Kill(); err != nil {
			return fmt.Errorf("GStreamer 종료 실패: %v", err)
		}
		stream.GstCmd = nil
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

// RunIFNotRun starts a stream if it's not already running (for on-demand streaming)
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
