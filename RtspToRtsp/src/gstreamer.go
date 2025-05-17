package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
	"io/ioutil"
	"bufio"
	"net"
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
	RTSPListener net.Listener
}

var (
	streams        map[string]*GStreamerStream
	serverMutex    sync.RWMutex
	serverPort     string
	serverStarted  time.Time
	serverRunning  bool
	rtspServer     *RTSPServer
)

type RTSPServer struct {
	listener net.Listener
	port     string
	streams  map[string]*GStreamerStream
	mutex    sync.RWMutex
	running  bool
}

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
	
	listener, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		return fmt.Errorf("RTSP 서버 시작 실패: %v", err)
	}
	
	rtspServer = &RTSPServer{
		listener: listener,
		port:     port,
		streams:  streams,
		running:  true,
	}
	
	go rtspServer.serve()
	
	log.Printf("GStreamer RTSP 서버 준비 완료 (포트: %s)", port)
	return nil
}

func (s *RTSPServer) serve() {
	for s.running {
		conn, err := s.listener.Accept()
		if err != nil {
			if s.running {
				log.Printf("RTSP 연결 수락 실패: %v", err)
			}
			continue
		}
		
		go s.handleConnection(conn)
	}
}

func (s *RTSPServer) handleConnection(conn net.Conn) {
	defer conn.Close()
	
	reader := bufio.NewReader(conn)
	
	for {
		request, err := readRTSPRequest(reader)
		if err != nil {
			log.Printf("RTSP 요청 읽기 실패: %v", err)
			return
		}
		
		log.Printf("RTSP 요청 수신: %s", request.Method)
		
		method := request.Method
		path := request.Path
		cseq := request.CSeq
		
		streamUUID := strings.TrimPrefix(path, "/")
		
		switch method {
		case "OPTIONS":
			response := fmt.Sprintf("RTSP/1.0 200 OK\r\n"+
				"CSeq: %s\r\n"+
				"Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n"+
				"\r\n", cseq)
			conn.Write([]byte(response))
			
		case "DESCRIBE":
			s.mutex.RLock()
			stream, exists := s.streams[streamUUID]
			s.mutex.RUnlock()
			
			if !exists {
				s.mutex.RLock()
				for uuid, str := range s.streams {
					if strings.EqualFold(uuid, streamUUID) {
						stream = str
						exists = true
						streamUUID = uuid
						break
					}
				}
				s.mutex.RUnlock()
			}
			
			if !exists {
				response := fmt.Sprintf("RTSP/1.0 404 Stream Not Found\r\n"+
					"CSeq: %s\r\n"+
					"\r\n", cseq)
				conn.Write([]byte(response))
				continue
			}
			
			if stream.OnDemand && !stream.Status {
				go startStream(streamUUID)
			}
			
			sdp := fmt.Sprintf("v=0\r\n"+
				"o=- 0 0 IN IP4 127.0.0.1\r\n"+
				"s=RTSP Server\r\n"+
				"t=0 0\r\n"+
				"m=video 0 RTP/AVP 96\r\n"+
				"a=rtpmap:96 H264/90000\r\n"+
				"a=control:track1\r\n")
			
			response := fmt.Sprintf("RTSP/1.0 200 OK\r\n"+
				"CSeq: %s\r\n"+
				"Content-Type: application/sdp\r\n"+
				"Content-Length: %d\r\n"+
				"\r\n%s", cseq, len(sdp), sdp)
			conn.Write([]byte(response))
			
		case "SETUP":
			s.mutex.RLock()
			stream, exists := s.streams[streamUUID]
			s.mutex.RUnlock()
			
			if !exists {
				s.mutex.RLock()
				for uuid, str := range s.streams {
					if strings.EqualFold(uuid, streamUUID) {
						stream = str
						exists = true
						streamUUID = uuid
						break
					}
				}
				s.mutex.RUnlock()
			}
			
			if !exists {
				response := fmt.Sprintf("RTSP/1.0 404 Stream Not Found\r\n"+
					"CSeq: %s\r\n"+
					"\r\n", cseq)
				conn.Write([]byte(response))
				continue
			}
			
			if stream.OnDemand && !stream.Status {
				go startStream(streamUUID)
			}
			
			transport := request.Headers["Transport"]
			clientPorts := "8000-8001" // Default
			
			if transport != "" {
				parts := strings.Split(transport, ";")
				for _, part := range parts {
					if strings.HasPrefix(part, "client_port=") {
						clientPorts = strings.TrimPrefix(part, "client_port=")
						break
					}
				}
			}
			
			sessionID := fmt.Sprintf("%d", time.Now().UnixNano())
			
			response := fmt.Sprintf("RTSP/1.0 200 OK\r\n"+
				"CSeq: %s\r\n"+
				"Transport: RTP/AVP;unicast;client_port=%s;server_port=5000-5001\r\n"+
				"Session: %s\r\n"+
				"\r\n", cseq, clientPorts, sessionID)
			conn.Write([]byte(response))
			
		case "PLAY":
			s.mutex.RLock()
			stream, exists := s.streams[streamUUID]
			s.mutex.RUnlock()
			
			if !exists {
				s.mutex.RLock()
				for uuid, str := range s.streams {
					if strings.EqualFold(uuid, streamUUID) {
						stream = str
						exists = true
						streamUUID = uuid
						break
					}
				}
				s.mutex.RUnlock()
			}
			
			if !exists {
				response := fmt.Sprintf("RTSP/1.0 404 Stream Not Found\r\n"+
					"CSeq: %s\r\n"+
					"\r\n", cseq)
				conn.Write([]byte(response))
				continue
			}
			
			if stream.OnDemand && !stream.Status {
				go startStream(streamUUID)
			}
			
			sessionID := request.Headers["Session"]
			
			response := fmt.Sprintf("RTSP/1.0 200 OK\r\n"+
				"CSeq: %s\r\n"+
				"Session: %s\r\n"+
				"Range: npt=0.000-\r\n"+
				"\r\n", cseq, sessionID)
			conn.Write([]byte(response))
			
			s.mutex.Lock()
			stream.Viewers++
			s.mutex.Unlock()
			
		case "TEARDOWN":
			s.mutex.RLock()
			stream, exists := s.streams[streamUUID]
			s.mutex.RUnlock()
			
			if !exists {
				response := fmt.Sprintf("RTSP/1.0 404 Stream Not Found\r\n"+
					"CSeq: %s\r\n"+
					"\r\n", cseq)
				conn.Write([]byte(response))
				continue
			}
			
			sessionID := request.Headers["Session"]
			
			response := fmt.Sprintf("RTSP/1.0 200 OK\r\n"+
				"CSeq: %s\r\n"+
				"Session: %s\r\n"+
				"\r\n", cseq, sessionID)
			conn.Write([]byte(response))
			
			s.mutex.Lock()
			if stream.Viewers > 0 {
				stream.Viewers--
			}
			s.mutex.Unlock()
			
			if stream.OnDemand && stream.Viewers == 0 {
				go StopStream(streamUUID)
			}
			
			return
			
		default:
			response := fmt.Sprintf("RTSP/1.0 405 Method Not Allowed\r\n"+
				"CSeq: %s\r\n"+
				"\r\n", cseq)
			conn.Write([]byte(response))
		}
	}
}

type RTSPRequest struct {
	Method   string
	Path     string
	Version  string
	Headers  map[string]string
	CSeq     string
	Body     string
}

func readRTSPRequest(reader *bufio.Reader) (*RTSPRequest, error) {
	requestLine, err := reader.ReadString('\n')
	if err != nil {
		return nil, err
	}
	
	requestLine = strings.TrimSpace(requestLine)
	parts := strings.Split(requestLine, " ")
	if len(parts) != 3 {
		return nil, fmt.Errorf("잘못된 RTSP 요청 라인: %s", requestLine)
	}
	
	request := &RTSPRequest{
		Method:  parts[0],
		Path:    parts[1],
		Version: parts[2],
		Headers: make(map[string]string),
	}
	
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return nil, err
		}
		
		line = strings.TrimSpace(line)
		if line == "" {
			break
		}
		
		headerParts := strings.SplitN(line, ":", 2)
		if len(headerParts) != 2 {
			continue
		}
		
		key := strings.TrimSpace(headerParts[0])
		value := strings.TrimSpace(headerParts[1])
		request.Headers[key] = value
		
		if key == "CSeq" {
			request.CSeq = value
		}
	}
	
	if contentLengthStr, ok := request.Headers["Content-Length"]; ok {
		var contentLength int
		fmt.Sscanf(contentLengthStr, "%d", &contentLength)
		
		if contentLength > 0 {
			body := make([]byte, contentLength)
			_, err := reader.Read(body)
			if err != nil {
				return nil, err
			}
			request.Body = string(body)
		}
	}
	
	log.Printf("RTSP 요청 파싱 완료: %s %s", request.Method, request.Path)
	return request, nil
}

func StopGStreamerServer() {
	serverMutex.Lock()
	defer serverMutex.Unlock()

	if !serverRunning {
		return
	}

	log.Println("RTSP 서버 종료 중...")

	if rtspServer != nil && rtspServer.running {
		rtspServer.running = false
		rtspServer.listener.Close()
	}

	for uuid, stream := range streams {
		if stream.GstCmd != nil && stream.GstCmd.Process != nil {
			log.Printf("스트림 종료 중: %s", uuid)
			stream.GstCmd.Process.Kill()
		}
		if stream.RTSPListener != nil {
			stream.RTSPListener.Close()
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

	pipeline := fmt.Sprintf(
		"rtspsrc location=%s latency=0 buffer-mode=0 drop-on-latency=true protocols=tcp do-retransmission=false ! " +
		"rtph264depay ! h264parse ! rtph264pay config-interval=1 pt=96 name=pay0",
		stream.URL)
	
	log.Printf("Starting GStreamer pipeline for %s: %s", uuid, pipeline)
	
	pipelineFile, err := ioutil.TempFile("", "pipeline-*.launch")
	if err != nil {
		return fmt.Errorf("파이프라인 파일 생성 실패: %v", err)
	}
	defer os.Remove(pipelineFile.Name())
	
	if _, err := pipelineFile.WriteString(pipeline); err != nil {
		return fmt.Errorf("파이프라인 파일 작성 실패: %v", err)
	}
	pipelineFile.Close()
	
	cmd := exec.Command("test-launch", pipelineFile.Name())
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Env = append(os.Environ(), fmt.Sprintf("GST_RTSP_SERVER_PORT=%s", serverPort))
	
	if err := cmd.Start(); err != nil {
		log.Printf("test-launch 실행 실패, gst-rtsp-server 직접 실행 시도: %v", err)
		
		args := []string{
			"-v",
			"--gst-debug=3",
			fmt.Sprintf("( %s )", pipeline),
		}
		
		cmd = exec.Command("gst-launch-1.0", args...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		
		if err := cmd.Start(); err != nil {
			return fmt.Errorf("GStreamer 시작 실패: %v", err)
		}
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

	if stream.RTSPListener != nil {
		stream.RTSPListener.Close()
		stream.RTSPListener = nil
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
