package main

import (
	"fmt"
	"log"
	"net"
	"sync"
	"time"

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
	rtspConn := rtspv2.NewConn(conn)
	
	server := &rtspv2.Server{
		HandleDescribe: func(conn *rtspv2.Conn) {
			urlPath := conn.URL.Path
			streamUUID := urlPath[1:] // Remove leading slash
			
			s.mutex.RLock()
			stream, ok := s.streams[streamUUID]
			s.mutex.RUnlock()
			
			if !ok {
				log.Printf("Stream not found: %s", streamUUID)
				return
			}
			
			Config.RunIFNotRun(streamUUID)
			
			codecs := Config.coGe(streamUUID)
			if codecs == nil {
				log.Printf("No codec data available for stream: %s", streamUUID)
				return
			}
			
			err := conn.WriteHeader(codecs)
			if err != nil {
				log.Printf("Failed to write header: %v", err)
				return
			}
		},
		HandlePlay: func(conn *rtspv2.Conn) {
			urlPath := conn.URL.Path
			streamUUID := urlPath[1:] // Remove leading slash
			
			s.mutex.RLock()
			stream, ok := s.streams[streamUUID]
			s.mutex.RUnlock()
			
			if !ok {
				log.Printf("Stream not found: %s", streamUUID)
				return
			}
			
			clientID := pseudoUUID()
			
			client := &RTSPClient{
				ID:         clientID,
				Conn:       conn,
				disconnect: make(chan bool),
			}
			
			stream.clientsMtx.Lock()
			stream.clients[clientID] = client
			stream.clientsMtx.Unlock()
			
			_, ch := Config.clAd(streamUUID)
			
			go func() {
				defer func() {
					stream.clientsMtx.Lock()
					delete(stream.clients, clientID)
					stream.clientsMtx.Unlock()
					Config.clDe(streamUUID, clientID)
				}()
				
				for {
					select {
					case pkt := <-ch:
						err := conn.WritePacket(&pkt)
						if err != nil {
							log.Printf("Failed to write packet: %v", err)
							return
						}
					case <-client.disconnect:
						return
					}
				}
			}()
		},
		HandleOptions: func(conn *rtspv2.Conn) {
		},
		HandleSetup: func(conn *rtspv2.Conn) {
			conn.protocol = rtspv2.TCPTransferPassive
		},
	}
	
	err := server.handleConn(rtspConn)
	if err != nil {
		log.Printf("RTSP connection handling error: %v", err)
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
