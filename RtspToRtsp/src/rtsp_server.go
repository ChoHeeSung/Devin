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
		
		if !strings.HasPrefix(urlPath, "/") {
			continue
		}
		
		streamUUID := urlPath[1:] // Remove leading slash
		if streamUUID == "" {
			s.sendOptionsResponse(conn)
			continue
		}
		
		s.mutex.RLock()
		_, streamExists := s.streams[streamUUID]
		s.mutex.RUnlock()
		
		if !streamExists {
			s.sendNotFoundResponse(conn)
			continue
		}
		
		switch method {
		case "OPTIONS":
			s.sendOptionsResponse(conn)
		case "DESCRIBE":
			s.handleDescribe(conn, streamUUID)
		case "SETUP":
			s.handleSetup(conn, streamUUID)
		case "PLAY":
			s.handlePlay(conn, streamUUID)
		case "TEARDOWN":
			s.handleTeardown(conn, streamUUID)
		default:
			s.sendMethodNotAllowedResponse(conn)
		}
	}
}

func (s *RTSPServer) sendOptionsResponse(conn net.Conn) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: 1\r\n" +
		"Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN\r\n" +
		"\r\n"
	conn.Write([]byte(response))
}

func (s *RTSPServer) sendNotFoundResponse(conn net.Conn) {
	response := "RTSP/1.0 404 Not Found\r\n" +
		"CSeq: 1\r\n" +
		"\r\n"
	conn.Write([]byte(response))
}

func (s *RTSPServer) sendMethodNotAllowedResponse(conn net.Conn) {
	response := "RTSP/1.0 405 Method Not Allowed\r\n" +
		"CSeq: 1\r\n" +
		"\r\n"
	conn.Write([]byte(response))
}

func (s *RTSPServer) handleDescribe(conn net.Conn, streamUUID string) {
	Config.RunIFNotRun(streamUUID)
	
	codecs := Config.coGe(streamUUID)
	if codecs == nil {
		log.Printf("No codec data available for stream: %s", streamUUID)
		return
	}
	
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: 1\r\n" +
		"Content-Type: application/sdp\r\n" +
		"Content-Length: 100\r\n" +
		"\r\n" +
		"v=0\r\n" +
		"o=- 0 0 IN IP4 127.0.0.1\r\n" +
		"s=RTSP Server\r\n" +
		"t=0 0\r\n" +
		"m=video 0 RTP/AVP 96\r\n" +
		"a=rtpmap:96 H264/90000\r\n"
	
	conn.Write([]byte(response))
}

func (s *RTSPServer) handleSetup(conn net.Conn, streamUUID string) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: 1\r\n" +
		"Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n" +
		"Session: 12345678\r\n" +
		"\r\n"
	conn.Write([]byte(response))
}

func (s *RTSPServer) handlePlay(conn net.Conn, streamUUID string) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: 1\r\n" +
		"Session: 12345678\r\n" +
		"Range: npt=0.000-\r\n" +
		"\r\n"
	conn.Write([]byte(response))
	
	clientID := pseudoUUID()
	
	_, ch := Config.clAd(streamUUID)
	
	go s.streamToClient(conn, streamUUID, clientID, ch)
}

func (s *RTSPServer) handleTeardown(conn net.Conn, streamUUID string) {
	response := "RTSP/1.0 200 OK\r\n" +
		"CSeq: 1\r\n" +
		"Session: 12345678\r\n" +
		"\r\n"
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
	
	if _, exists := s.streams[uuid]; exists {
		return
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
