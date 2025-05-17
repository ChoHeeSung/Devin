package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// FFmpegStream represents a single RTSP stream
type FFmpegStream struct {
	UUID         string
	URL          string
	OnDemand     bool
	Status       bool
	StartTime    time.Time
	Viewers      int
	LowLatency   bool
	FFmpegCmd    *exec.Cmd
}

var (
	streams        map[string]*FFmpegStream
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
	
	streams = make(map[string]*FFmpegStream)
	serverPort = port
	serverStarted = time.Now()
	serverRunning = true
	
	cmd := exec.Command("ffmpeg", "-version")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("FFmpeg 확인 실패: %v", err)
	}
	
	log.Printf("FFmpeg 버전: %s", string(output))
	log.Printf("RTSP 서버가 포트 %s에서 시작되었습니다", port)
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
		if stream.FFmpegCmd != nil && stream.FFmpegCmd.Process != nil {
			log.Printf("스트림 종료 중: %s", uuid)
			stream.FFmpegCmd.Process.Kill()
		}
	}
	
	if rtspServerCmd != nil && rtspServerCmd.Process != nil {
		rtspServerCmd.Process.Kill()
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

	streams[uuid] = &FFmpegStream{
		UUID:        uuid,
		URL:         url,
		OnDemand:    onDemand,
		Status:      false,
		StartTime:   time.Now(),
		Viewers:     0,
		LowLatency:  true,
		FFmpegCmd:   nil,
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
	if stream.FFmpegCmd != nil && stream.FFmpegCmd.Process != nil {
		return nil // Stream already running
	}

	outputURL := fmt.Sprintf("rtsp://0.0.0.0:%s/%s", serverPort, uuid)
	
	// 1. Connects to the source RTSP stream
	args := []string{
		"-nostdin",
		"-loglevel", "warning",
		"-rtsp_transport", "tcp",
		"-i", stream.URL,
		"-c:v", "copy",
		"-c:a", "copy",
		"-f", "rtsp",
		"-rtsp_transport", "tcp",
		"-muxdelay", "0.1",
		outputURL,
	}

	log.Printf("Starting FFmpeg for stream %s: ffmpeg %s", uuid, strings.Join(args, " "))
	
	cmd := exec.Command("ffmpeg", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("FFmpeg 시작 실패: %v", err)
	}

	stream.FFmpegCmd = cmd
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

	if stream.FFmpegCmd != nil && stream.FFmpegCmd.Process != nil {
		if err := stream.FFmpegCmd.Process.Kill(); err != nil {
			return fmt.Errorf("FFmpeg 종료 실패: %v", err)
		}
		stream.FFmpegCmd = nil
	}

	stream.Status = false
	log.Printf("스트림 종료됨: %s", uuid)
	return nil
}

func GetStreamStatus(uuid string) (*FFmpegStream, error) {
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

func GetAllStreams() map[string]*FFmpegStream {
	serverMutex.RLock()
	defer serverMutex.RUnlock()

	if !serverRunning {
		return nil
	}

	result := make(map[string]*FFmpegStream)
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
