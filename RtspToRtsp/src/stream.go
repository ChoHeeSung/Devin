package main

import (
	"errors"
	"log"
	"time"

	"github.com/deepch/vdk/av"
	"github.com/deepch/vdk/format/rtspv2"
)

var (
	ErrorStreamExitNoVideoOnStream = errors.New("Stream Exit No Video On Stream")
	ErrorStreamExitRtspDisconnect  = errors.New("Stream Exit Rtsp Disconnect")
	ErrorStreamExitNoViewer        = errors.New("Stream Exit On Demand No Viewer")
	ErrorStreamExitStatusFalse     = errors.New("Stream Exit Status False")
)

func serveStreams() {
	for k, v := range Config.Streams {
		RegisterStream(k, v.URL, v.OnDemand)
		if !v.OnDemand {
			go RTSPWorkerLoop(k, v.URL, v.OnDemand, v.DisableAudio, v.Debug)
		}
	}
}
func RTSPWorkerLoop(name, url string, OnDemand, DisableAudio, Debug bool) {
	defer func() {
		// 루프가 종료될 때 is_running을 false로 설정
		Config.mutex.Lock()
		if stream, ok := Config.Streams[name]; ok {
			stream.IsRunning = false
			stream.Status = false
			Config.Streams[name] = stream
		}
		Config.mutex.Unlock()
		Config.RunUnlock(name)
	}()

	// 초기 상태 설정
	Config.UpdateStreamState(name, true)

	// 루프 시작 시 is_running을 true로 설정
	Config.mutex.Lock()
	if stream, ok := Config.Streams[name]; ok {
		stream.IsRunning = true
		Config.Streams[name] = stream
	}
	Config.mutex.Unlock()

	for {
		log.Println("Stream Try Connect", name)
		err := RTSPWorker(name, url, OnDemand, DisableAudio, Debug)
		if err != nil {
			log.Println(err)
			Config.LastError = err
			Config.HandleStreamError(name, err)

			// 재연결 시도 횟수 증가
			Config.mutex.Lock()
			if stream, ok := Config.Streams[name]; ok {
				stream.ReconnectCount++
				// is_running은 여전히 true로 유지 (루프가 실행 중이므로)
				stream.Status = false
				Config.Streams[name] = stream
			}
			Config.mutex.Unlock()
		}

		if OnDemand && !Config.HasViewer(name) {
			log.Println(ErrorStreamExitNoViewer)
			return
		}
		time.Sleep(1 * time.Second)
	}
}
func RTSPWorker(name, url string, OnDemand, DisableAudio, Debug bool) error {
	keyTest := time.NewTimer(20 * time.Second)
	clientTest := time.NewTimer(20 * time.Second)

	// 스트림 상태 업데이트 (is_running은 수정하지 않음)
	Config.mutex.Lock()
	if stream, ok := Config.Streams[name]; ok {
		stream.LastUpdated = time.Now()
		stream.Status = true
		Config.Streams[name] = stream
	}
	Config.mutex.Unlock()

	RTSPClient, err := rtspv2.Dial(rtspv2.RTSPClientOptions{
		URL:              url,
		DisableAudio:     DisableAudio,
		DialTimeout:      5 * time.Second, // 타임아웃 증가
		ReadWriteTimeout: 5 * time.Second, // 타임아웃 증가
		Debug:            Debug,
	})
	if err != nil {
		return err
	}
	defer RTSPClient.Close()

	if RTSPClient.CodecData != nil {
		Config.coAd(name, RTSPClient.CodecData)
	}

	var AudioOnly bool
	if len(RTSPClient.CodecData) == 1 && RTSPClient.CodecData[0].Type().IsAudio() {
		AudioOnly = true
	}

	// 패킷 버퍼링을 위한 채널
	packetBuffer := make(chan av.Packet, 1000) // 버퍼 크기 증가

	// 패킷 처리 고루틴
	go func() {
		for pck := range packetBuffer {
			if AudioOnly || pck.IsKeyFrame {
				keyTest.Reset(20 * time.Second)
			}
			Config.cast(name, pck)

			// 시청자 수 업데이트
			Config.mutex.RLock()
			viewerCount := len(Config.Streams[name].Cl)
			Config.mutex.RUnlock()
			Config.UpdateViewerCount(name, viewerCount)
		}
	}()

	for {
		select {
		case <-clientTest.C:
			if OnDemand {
				if !Config.HasViewer(name) {
					return ErrorStreamExitNoViewer
				} else {
					clientTest.Reset(20 * time.Second)
				}
			}

		case <-keyTest.C:
			Config.mutex.Lock()
			if stream, ok := Config.Streams[name]; ok {
				stream.Status = false
				Config.Streams[name] = stream
			}
			Config.mutex.Unlock()
			return ErrorStreamExitNoVideoOnStream

		case signals := <-RTSPClient.Signals:
			switch signals {
			case rtspv2.SignalCodecUpdate:
				Config.coAd(name, RTSPClient.CodecData)
			case rtspv2.SignalStreamRTPStop:
				Config.mutex.Lock()
				if stream, ok := Config.Streams[name]; ok {
					stream.Status = false
					Config.Streams[name] = stream
				}
				Config.mutex.Unlock()
				return ErrorStreamExitRtspDisconnect
			}

		case packetAV := <-RTSPClient.OutgoingPacketQueue:
			select {
			case packetBuffer <- *packetAV:
				// 패킷이 성공적으로 버퍼에 추가됨
			default:
				// 버퍼가 가득 찼을 때는 가장 오래된 패킷을 버림
				<-packetBuffer            // 가장 오래된 패킷 제거
				packetBuffer <- *packetAV // 새 패킷 추가
			}
		}
	}
}
