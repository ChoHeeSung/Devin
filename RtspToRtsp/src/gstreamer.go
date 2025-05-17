package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

type GStreamerServer struct {
	Port      string
	Streams   map[string]*GStreamerStream
	mutex     sync.RWMutex
	startTime time.Time
	isRunning bool
	processes map[string]*os.Process
}

type GStreamerStream struct {
	UUID       string
	URL        string
	OnDemand   bool
	Status     bool
	Process    *os.Process
	StartTime  time.Time
	Viewers    int
	LowLatency bool
}

var gstServer *GStreamerServer

func StartGStreamerServer(port string) error {
	rtspDir := "/tmp/rtsp-server"
	if err := os.MkdirAll(rtspDir, 0755); err != nil {
		return fmt.Errorf("failed to create RTSP server directory: %v", err)
	}

	gstServer = &GStreamerServer{
		Port:      port,
		Streams:   make(map[string]*GStreamerStream),
		startTime: time.Now(),
		isRunning: true,
		processes: make(map[string]*os.Process),
	}

	log.Printf("GStreamer RTSP server starting on port %s", port)

	scriptPath := filepath.Join(rtspDir, "start-rtsp-server.sh")
	scriptContent := fmt.Sprintf(`#!/bin/bash
# Start the RTSP server using gst-rtsp-server-1.0
test-launch "( videotestsrc is-live=1 ! video/x-raw,width=640,height=480 ! videoconvert ! x264enc ! rtph264pay name=pay0 pt=96 )" &
echo "RTSP server started on port %s"
# Keep the script running
while true; do
  sleep 10
done
`, port)
	
	if err := os.WriteFile(scriptPath, []byte(scriptContent), 0755); err != nil {
		return fmt.Errorf("failed to create RTSP server script: %v", err)
	}
	
	cmd := exec.Command("/bin/bash", scriptPath)
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start RTSP server: %v", err)
	}
	
	gstServer.processes["server"] = cmd.Process
	
	return nil
}

func StopGStreamerServer() {
	if gstServer != nil && gstServer.isRunning {
		log.Println("Stopping GStreamer RTSP server")
		gstServer.mutex.Lock()
		defer gstServer.mutex.Unlock()
		
		for uuid, stream := range gstServer.Streams {
			if stream.Process != nil {
				log.Printf("Stopping stream: %s", uuid)
				stream.Process.Signal(syscall.SIGTERM)
			}
		}
		
		if serverProcess, exists := gstServer.processes["server"]; exists {
			serverProcess.Signal(syscall.SIGTERM)
		}
		
		gstServer.isRunning = false
		gstServer = nil
	}
}

func RegisterStream(uuid string, url string, onDemand bool) error {
	if gstServer == nil || !gstServer.isRunning {
		return fmt.Errorf("GStreamer RTSP server not running")
	}

	gstServer.mutex.Lock()
	defer gstServer.mutex.Unlock()

	for existingUUID := range gstServer.Streams {
		if strings.EqualFold(existingUUID, uuid) {
			log.Printf("Stream already registered with different case: %s vs %s", existingUUID, uuid)
			return nil
		}
	}

	streamDir := filepath.Join("/tmp/rtsp-server", uuid)
	if err := os.MkdirAll(streamDir, 0755); err != nil {
		return fmt.Errorf("failed to create stream directory: %v", err)
	}

	scriptPath := filepath.Join(streamDir, "start-stream.sh")
	
	pipelineStr := fmt.Sprintf(`#!/bin/bash
# Start the RTSP stream using gst-launch-1.0
gst-launch-1.0 -v \
  rtspsrc location="%s" latency=0 buffer-mode=0 drop-on-latency=true protocols=tcp do-retransmission=false ! \
  rtph264depay ! h264parse ! \
  rtph264pay name=pay0 config-interval=1 pt=96 ! \
  udpsink host=127.0.0.1 port=%s
`, url, gstServer.Port)

	if err := os.WriteFile(scriptPath, []byte(pipelineStr), 0755); err != nil {
		return fmt.Errorf("failed to create stream script: %v", err)
	}

	gstServer.Streams[uuid] = &GStreamerStream{
		UUID:       uuid,
		URL:        url,
		OnDemand:   onDemand,
		Status:     true,
		StartTime:  time.Now(),
		Viewers:    0,
		LowLatency: true,
	}

	if !onDemand {
		if err := startStream(uuid); err != nil {
			log.Printf("Failed to start stream %s: %v", uuid, err)
		}
	}

	log.Printf("Registered GStreamer RTSP stream: %s", uuid)
	return nil
}

func startStream(uuid string) error {
	if gstServer == nil || !gstServer.isRunning {
		return fmt.Errorf("GStreamer RTSP server not running")
	}

	gstServer.mutex.Lock()
	defer gstServer.mutex.Unlock()

	stream, exists := gstServer.Streams[uuid]
	if !exists {
		return fmt.Errorf("stream not found: %s", uuid)
	}

	if stream.Process != nil {
		return nil
	}

	scriptPath := filepath.Join("/tmp/rtsp-server", uuid, "start-stream.sh")
	cmd := exec.Command("/bin/bash", scriptPath)
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start stream: %v", err)
	}

	stream.Process = cmd.Process
	stream.StartTime = time.Now()
	stream.Status = true

	log.Printf("Started stream: %s", uuid)
	return nil
}

func StopStream(uuid string) error {
	if gstServer == nil || !gstServer.isRunning {
		return fmt.Errorf("GStreamer RTSP server not running")
	}

	gstServer.mutex.Lock()
	defer gstServer.mutex.Unlock()

	stream, exists := gstServer.Streams[uuid]
	if !exists {
		return fmt.Errorf("stream not found: %s", uuid)
	}

	if stream.Process != nil {
		if err := stream.Process.Signal(syscall.SIGTERM); err != nil {
			return fmt.Errorf("failed to stop stream: %v", err)
		}
		stream.Process = nil
		stream.Status = false
	}

	log.Printf("Stopped stream: %s", uuid)
	return nil
}

func GetStreamStatus(uuid string) (*GStreamerStream, error) {
	if gstServer == nil || !gstServer.isRunning {
		return nil, fmt.Errorf("GStreamer RTSP server not running")
	}

	gstServer.mutex.RLock()
	defer gstServer.mutex.RUnlock()

	stream, exists := gstServer.Streams[uuid]
	if !exists {
		return nil, fmt.Errorf("stream not found: %s", uuid)
	}

	return stream, nil
}

func GetAllStreams() map[string]*GStreamerStream {
	if gstServer == nil || !gstServer.isRunning {
		return nil
	}

	gstServer.mutex.RLock()
	defer gstServer.mutex.RUnlock()

	streams := make(map[string]*GStreamerStream)
	for uuid, stream := range gstServer.Streams {
		streams[uuid] = stream
	}

	return streams
}

func GetRTSPURL(uuid string, hostname string) (string, error) {
	if gstServer == nil || !gstServer.isRunning {
		return "", fmt.Errorf("GStreamer RTSP server not running")
	}

	gstServer.mutex.RLock()
	defer gstServer.mutex.RUnlock()

	_, exists := gstServer.Streams[uuid]
	if !exists {
		return "", fmt.Errorf("stream not found: %s", uuid)
	}

	return fmt.Sprintf("rtsp://%s:%s/%s", hostname, gstServer.Port, uuid), nil
}

func RunIFNotRun(uuid string) error {
	if gstServer == nil || !gstServer.isRunning {
		return fmt.Errorf("GStreamer RTSP server not running")
	}

	gstServer.mutex.RLock()
	stream, exists := gstServer.Streams[uuid]
	gstServer.mutex.RUnlock()

	if !exists {
		return fmt.Errorf("stream not found: %s", uuid)
	}

	if stream.OnDemand && stream.Process == nil {
		return startStream(uuid)
	}

	return nil
}
