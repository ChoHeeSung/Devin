package main

import (
	"fmt"
	"log"
	"net"
	"strings"
	"sync"

	"github.com/deepch/vdk/av"
	"github.com/deepch/vdk/format/rtspv2"
)

var rtspServer *RTSPServer

type RTSPServer struct {
	mutex       sync.RWMutex
	streams     map[string]*RTSPStream
	listener    net.Listener
	port        string
	serverState bool
}

type RTSPStream struct {
	UUID       string
	Conn       *rtspv2.Server
	URL        string
	clients    map[string]*RTSPClient
	clientsMtx sync.RWMutex
	active     bool
	codecs     []av.CodecData
}

type RTSPClient struct {
	ID         string
	Conn       *rtspv2.Conn
	disconnect chan bool
}

func NewRTSPServer(port string) *RTSPServer {
	return &RTSPServer{
		streams:     make(map[string]*RTSPStream),
		port:        port,
		serverState: false,
	}
}

func (s *RTSPServer) Start() error {
	var err error
	addr := fmt.Sprintf(":%s", s.port)
	s.listener, err = net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to start RTSP server: %v", err)
	}

	s.serverState = true
	go s.acceptConnections()
	return nil
}

func (s *RTSPServer) Stop() {
	s.serverState = false
	if s.listener != nil {
		s.listener.Close()
	}
}

func (s *RTSPServer) acceptConnections() {
	for s.serverState {
		conn, err := s.listener.Accept()
		if err != nil {
			log.Printf("RTSP server accept error: %v", err)
			continue
		}
		go s.handleConnection(conn)
	}
}

func (s *RTSPServer) handleConnection(conn net.Conn) {
	buffer := make([]byte, 4096)
	for {
		n, err := conn.Read(buffer)
		if err != nil {
			log.Printf("RTSP server read error: %v", err)
			return
		}
		
		request := string(buffer[:n])
		log.Printf("Received RTSP request: %s", request)
		
		lines := strings.Split(request, "\r\n")
		if len(lines) < 1 {
			continue
		}
		
		requestParts := strings.Split(lines[0], " ")
		if len(requestParts) < 3 {
			continue
		}
		
		method := requestParts[0]
		urlPath := requestParts[1]
		
		headers := make(map[string]string)
		for _, line := range lines[1:] {
			if line == "" {
				continue
			}
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				key := strings.TrimSpace(parts[0])
				value := strings.TrimSpace(parts[1])
				headers[key] = value
			}
		}
		
		cseq := "1" // Default CSeq
		if val, ok := headers["CSeq"]; ok {
			cseq = val
		}
		
		if method == "OPTIONS" && urlPath == "*" {
			s.sendOptionsResponse(conn, cseq)
			continue
		}
		
		streamUUID := s.extractStreamUUID(urlPath)
		if streamUUID == "" {
			s.sendOptionsResponse(conn, cseq)
			continue
		}
		
		s.mutex.RLock()
		streamFound := false
		var actualUUID string
		for uuid := range s.streams {
			if strings.EqualFold(uuid, streamUUID) {
				streamFound = true
				actualUUID = uuid
				break
			}
		}
		s.mutex.RUnlock()
		
		if !streamFound {
			log.Printf("Stream not found: %s", streamUUID)
			s.sendNotFoundResponse(conn, cseq)
			continue
		}
		
		streamUUID = actualUUID
		
		switch method {
		case "OPTIONS":
			s.sendOptionsResponse(conn, cseq)
		case "DESCRIBE":
			s.handleDescribe(conn, streamUUID, cseq)
		case "SETUP":
			transport := headers["Transport"]
			s.handleSetup(conn, streamUUID, cseq, transport)
		case "PLAY":
			s.handlePlay(conn, streamUUID, cseq)
		case "TEARDOWN":
			s.handleTeardown(conn, streamUUID, cseq)
		default:
			s.sendMethodNotAllowedResponse(conn, cseq)
		}
	}
}

func (s *RTSPServer) extractStreamUUID(urlPath string) string {
	if strings.HasPrefix(urlPath, "rtsp://") {
		parts := strings.Split(urlPath, "/")
		if len(parts) > 3 {
			return parts[len(parts)-1]
		}
		return ""
	}
	
	if strings.HasPrefix(urlPath, "/") {
		return urlPath[1:]
	}
	
	return urlPath
}

func (s *RTSPServer) sendOptionsResponse(conn net.Conn, cseq string) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n" +
		"\r\n"
	log.Printf("Sending OPTIONS response: %s", response)
	conn.Write([]byte(response))
}

func (s *RTSPServer) sendNotFoundResponse(conn net.Conn, cseq string) {
	response := "RTSP/1.0 404 Not Found\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"\r\n"
	log.Printf("Sending 404 response: %s", response)
	conn.Write([]byte(response))
}

func (s *RTSPServer) sendMethodNotAllowedResponse(conn net.Conn, cseq string) {
	response := "RTSP/1.0 405 Method Not Allowed\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"\r\n"
	log.Printf("Sending 405 response: %s", response)
	conn.Write([]byte(response))
}

func (s *RTSPServer) handleDescribe(conn net.Conn, streamUUID string, cseq string) {
	Config.RunIFNotRun(streamUUID)
	
	codecs := Config.coGe(streamUUID)
	if codecs == nil {
		log.Printf("No codec data available for stream: %s", streamUUID)
		return
	}
	
	sdp := "v=0\r\n" +
		"o=- 0 0 IN IP4 127.0.0.1\r\n" +
		"s=RTSP Server\r\n" +
		"t=0 0\r\n" +
		"m=video 0 RTP/AVP 96\r\n" +
		"a=rtpmap:96 H264/90000\r\n"
	
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"Content-Type: application/sdp\r\n" +
		"Content-Length: " + fmt.Sprintf("%d", len(sdp)) + "\r\n" +
		"\r\n" +
		sdp
	
	log.Printf("Sending DESCRIBE response: %s", response)
	conn.Write([]byte(response))
}

func (s *RTSPServer) handleSetup(conn net.Conn, streamUUID string, cseq string, transport string) {
	Config.RunIFNotRun(streamUUID)
	
	transportResponse := "RTP/AVP/TCP;unicast;interleaved=0-1"
	if transport != "" {
		if strings.Contains(transport, "RTP/AVP;unicast") {
			clientPorts := ""
			if strings.Contains(transport, "client_port=") {
				parts := strings.Split(transport, "client_port=")
				if len(parts) > 1 {
					portParts := strings.Split(parts[1], ";")
					clientPorts = portParts[0]
				}
			}
			
			if clientPorts != "" {
				transportResponse = "RTP/AVP;unicast;client_port=" + clientPorts + ";server_port=5000-5001"
			} else {
				transportResponse = "RTP/AVP;unicast;client_port=5000-5001;server_port=5000-5001"
			}
		}
	}
	
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"Transport: " + transportResponse + "\r\n" +
		"Session: 12345678\r\n" +
		"\r\n"
	log.Printf("Sending SETUP response: %s", response)
	conn.Write([]byte(response))
}

func (s *RTSPServer) handlePlay(conn net.Conn, streamUUID string, cseq string) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"Session: 12345678\r\n" +
		"Range: npt=0.000-\r\n" +
		"\r\n"
	log.Printf("Sending PLAY response: %s", response)
	conn.Write([]byte(response))
	
	clientID := pseudoUUID()
	
	_, ch := Config.clAd(streamUUID)
	
	go s.streamToClient(conn, streamUUID, clientID, ch)
}

func (s *RTSPServer) handleTeardown(conn net.Conn, streamUUID string, cseq string) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: " + cseq + "\r\n" +
		"Session: 12345678\r\n" +
		"\r\n"
	log.Printf("Sending TEARDOWN response: %s", response)
	conn.Write([]byte(response))
}

func (s *RTSPServer) streamToClient(conn net.Conn, streamUUID string, clientID string, ch chan av.Packet) {
	defer Config.clDe(streamUUID, clientID)
	
	for pkt := range ch {
		header := []byte{0x24, 0x00, 0x00, 0x00}
		
		
		packetLength := len(pkt.Data)
		header[2] = byte(packetLength >> 8)
		header[3] = byte(packetLength & 0xFF)
		
		conn.Write(header)
		conn.Write(pkt.Data)
	}
}

func (s *RTSPServer) RegisterStream(uuid string, url string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	
	for existingUUID := range s.streams {
		if strings.EqualFold(existingUUID, uuid) {
			log.Printf("Stream already registered with different case: %s vs %s", existingUUID, uuid)
			return
		}
	}
	
	stream := &RTSPStream{
		UUID:    uuid,
		URL:     url,
		clients: make(map[string]*RTSPClient),
		active:  false,
	}
	
	s.streams[uuid] = stream
	log.Printf("Registered RTSP stream: %s", uuid)
}

func (s *RTSPServer) UnregisterStream(uuid string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	
	stream, exists := s.streams[uuid]
	if !exists {
		return
	}
	
	stream.clientsMtx.Lock()
	for _, client := range stream.clients {
		client.disconnect <- true
	}
	stream.clientsMtx.Unlock()
	
	delete(s.streams, uuid)
	log.Printf("Unregistered RTSP stream: %s", uuid)
}
