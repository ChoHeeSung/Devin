package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/deepch/vdk/av"

	webrtc "github.com/deepch/vdk/format/webrtcv3"
	"github.com/gin-gonic/gin"
)

type JCodec struct {
	Type string
}

// StreamStatus는 스트리밍 상태 정보를 담는 구조체입니다.
type StreamStatus struct {
	UUID           string    `json:"uuid"`
	URL            string    `json:"url"`
	RtspUrl        string    `json:"rtspUrl"`
	Status         bool      `json:"status"`
	OnDemand       bool      `json:"onDemand"`
	DisableAudio   bool      `json:"disableAudio"`
	Debug          bool      `json:"debug"`
	ViewerCount    int       `json:"viewerCount"`
	LastError      string    `json:"lastError,omitempty"`
	LastUpdated    time.Time `json:"lastUpdated"`
	IsRunning      bool      `json:"isRunning"`
	ReconnectCount int       `json:"reconnectCount"`
}

// StreamStatusResponse는 API 응답을 위한 구조체입니다.
type StreamStatusResponse struct {
	Streams     []StreamStatus `json:"streams"`
	Total       int            `json:"total"`
	ActiveCount int            `json:"activeCount"`
}

// ServerStatus는 서버 상태 정보를 담는 구조체입니다.
type ServerStatus struct {
	CPU struct {
		LoadAvg1  float64 `json:"loadAvg1"`
		LoadAvg5  float64 `json:"loadAvg5"`
		LoadAvg15 float64 `json:"loadAvg15"`
		NumCPU    int     `json:"numCpu"`
	} `json:"cpu"`
	Memory struct {
		Total        uint64  `json:"total"`
		Used         uint64  `json:"used"`
		Free         uint64  `json:"free"`
		UsagePercent float64 `json:"usagePercent"`
	} `json:"memory"`
	GoRuntime struct {
		Version      string `json:"version"`
		NumGoroutine int    `json:"numGoroutine"`
		GOMAXPROCS   int    `json:"gomaxprocs"`
		NumCPU       int    `json:"numCpu"`
		CGOCalls     int64  `json:"cgoCalls"`
		NumGC        uint32 `json:"numGc"`
		HeapObjects  uint64 `json:"heapObjects"`
		HeapAlloc    uint64 `json:"heapAlloc"`
		HeapSys      uint64 `json:"heapSys"`
	} `json:"runtime"`
	Process struct {
		NumFD        int32   `json:"numFd"`
		NumThreads   int32   `json:"numThreads"`
		VirtualSize  uint64  `json:"virtualSize"`
		ResidentSize uint64  `json:"residentSize"`
		CPUTime      float64 `json:"cpuTime"`
	} `json:"process"`
	Network struct {
		BytesSent       uint64  `json:"bytesSent"`
		BytesReceived   uint64  `json:"bytesReceived"`
		PacketsSent     uint64  `json:"packetsSent"`
		PacketsReceived uint64  `json:"packetsReceived"`
		BytesSentRate   float64 `json:"bytesSentRate"`     // 초당 전송 바이트
		BytesRecvRate   float64 `json:"bytesReceivedRate"` // 초당 수신 바이트
		LastUpdate      string  `json:"lastUpdate"`
	} `json:"network"`
	Uptime float64 `json:"uptime"`
}

// 서버 시작 시간을 저장하는 변수
var serverStartTime = time.Now()

// 네트워크 통계를 저장하는 변수
var networkStats = struct {
	BytesSent       uint64
	BytesReceived   uint64
	PacketsSent     uint64
	PacketsReceived uint64
	LastUpdate      time.Time
}{
	LastUpdate: time.Now(),
}

// 이전 네트워크 통계를 저장하는 변수
var prevNetworkStats = struct {
	BytesSent       uint64
	BytesReceived   uint64
	PacketsSent     uint64
	PacketsReceived uint64
	LastUpdate      time.Time
}{
	LastUpdate: time.Now(),
}

// 네트워크 통계를 업데이트하는 함수
func updateNetworkStats() {
	// 이전 통계를 현재 통계로 복사
	prevNetworkStats = networkStats

	// 운영체제별로 다른 방법을 사용합니다.
	switch runtime.GOOS {
	case "darwin": // macOS
		// macOS에서는 netstat 명령어를 사용하여 네트워크 통계를 가져옵니다.
		cmd := exec.Command("netstat", "-ib")
		output, err := cmd.Output()
		if err != nil {
			log.Printf("네트워크 통계 수집 실패: %v", err)
			return
		}

		// 출력 결과를 파싱합니다.
		lines := strings.Split(string(output), "\n")
		var totalBytesIn, totalBytesOut uint64

		for _, line := range lines {
			// 헤더 라인은 건너뜁니다.
			if strings.Contains(line, "Name") || strings.Contains(line, "Mtu") {
				continue
			}

			fields := strings.Fields(line)
			if len(fields) < 10 {
				continue
			}

			// 인터페이스 이름이 lo0(루프백)인 경우 건너뜁니다.
			if fields[0] == "lo0" {
				continue
			}

			// 바이트 수신량 (ibytes)
			if bytesIn, err := strconv.ParseUint(fields[6], 10, 64); err == nil {
				totalBytesIn += bytesIn
			}

			// 바이트 전송량 (obytes)
			if bytesOut, err := strconv.ParseUint(fields[9], 10, 64); err == nil {
				totalBytesOut += bytesOut
			}
		}

		// 통계 업데이트
		networkStats.BytesReceived = totalBytesIn
		networkStats.BytesSent = totalBytesOut
		networkStats.LastUpdate = time.Now()

		// 패킷 수는 정확하게 측정하기 어려우므로 간단한 추정치 사용
		// 평균 패킷 크기를 1500 바이트로 가정
		networkStats.PacketsReceived = totalBytesIn / 1500
		networkStats.PacketsSent = totalBytesOut / 1500

	case "linux": // Linux
		// Linux에서는 /proc/net/dev 파일을 읽어 네트워크 통계를 가져옵니다.
		data, err := os.ReadFile("/proc/net/dev")
		if err != nil {
			log.Printf("네트워크 통계 수집 실패: %v", err)
			return
		}

		// 파일 내용을 파싱합니다.
		lines := strings.Split(string(data), "\n")
		var totalBytesIn, totalBytesOut, totalPacketsIn, totalPacketsOut uint64

		for _, line := range lines {
			// 헤더 라인은 건너뜁니다.
			if strings.Contains(line, "Inter-") || strings.Contains(line, "face") {
				continue
			}

			fields := strings.Fields(line)
			if len(fields) < 17 {
				continue
			}

			// 인터페이스 이름에서 콜론 제거
			fields[0] = strings.TrimSuffix(fields[0], ":")

			// lo(루프백) 인터페이스는 건너뜁니다.
			if fields[0] == "lo" {
				continue
			}

			// 바이트 수신량 (rx_bytes)
			if bytesIn, err := strconv.ParseUint(fields[1], 10, 64); err == nil {
				totalBytesIn += bytesIn
			}

			// 패킷 수신량 (rx_packets)
			if packetsIn, err := strconv.ParseUint(fields[2], 10, 64); err == nil {
				totalPacketsIn += packetsIn
			}

			// 바이트 전송량 (tx_bytes)
			if bytesOut, err := strconv.ParseUint(fields[9], 10, 64); err == nil {
				totalBytesOut += bytesOut
			}

			// 패킷 전송량 (tx_packets)
			if packetsOut, err := strconv.ParseUint(fields[10], 10, 64); err == nil {
				totalPacketsOut += packetsOut
			}
		}

		// 통계 업데이트
		networkStats.BytesReceived = totalBytesIn
		networkStats.BytesSent = totalBytesOut
		networkStats.PacketsReceived = totalPacketsIn
		networkStats.PacketsSent = totalPacketsOut
		networkStats.LastUpdate = time.Now()

	case "windows":
		// Windows에서는 netstat 명령어를 사용하여 네트워크 통계를 가져옵니다.
		cmd := exec.Command("netstat", "-e")
		output, err := cmd.Output()
		if err != nil {
			log.Printf("네트워크 통계 수집 실패: %v", err)
			return
		}

		// 출력 결과를 파싱합니다.
		lines := strings.Split(string(output), "\n")
		var totalBytesIn, totalBytesOut uint64

		for i, line := range lines {
			// 헤더 라인은 건너뜁니다.
			if i < 2 {
				continue
			}

			fields := strings.Fields(line)
			if len(fields) < 2 {
				continue
			}

			// 바이트 수신량
			if bytesIn, err := strconv.ParseUint(fields[0], 10, 64); err == nil {
				totalBytesIn += bytesIn
			}

			// 바이트 전송량
			if bytesOut, err := strconv.ParseUint(fields[1], 10, 64); err == nil {
				totalBytesOut += bytesOut
			}
		}

		// 통계 업데이트
		networkStats.BytesReceived = totalBytesIn
		networkStats.BytesSent = totalBytesOut
		networkStats.LastUpdate = time.Now()

		// 패킷 수는 정확하게 측정하기 어려우므로 간단한 추정치 사용
		// 평균 패킷 크기를 1500 바이트로 가정
		networkStats.PacketsReceived = totalBytesIn / 1500
		networkStats.PacketsSent = totalBytesOut / 1500

	default:
		log.Printf("지원하지 않는 운영체제: %s", runtime.GOOS)
	}
}

// getLoadAverage는 시스템의 평균 부하를 가져옵니다.
func getLoadAverage() (float64, float64, float64, error) {
	// 운영 체제에 따라 다른 방법을 사용합니다.
	switch runtime.GOOS {
	case "darwin": // macOS
		// macOS에서는 sysctl 명령어를 사용하여 평균 부하를 가져옵니다.
		cmd := exec.Command("sysctl", "-n", "vm.loadavg")
		output, err := cmd.Output()
		if err != nil {
			return 0, 0, 0, err
		}

		// 출력 결과를 파싱합니다.
		// 출력 형식: { 1.23 0.45 0.12 }
		outputStr := string(output)
		outputStr = strings.Trim(outputStr, "{} \n")
		parts := strings.Split(outputStr, " ")

		if len(parts) < 3 {
			return 0, 0, 0, fmt.Errorf("예상치 못한 출력 형식: %s", outputStr)
		}

		loadAvg1, err := strconv.ParseFloat(parts[0], 64)
		if err != nil {
			return 0, 0, 0, err
		}

		loadAvg5, err := strconv.ParseFloat(parts[1], 64)
		if err != nil {
			return 0, 0, 0, err
		}

		loadAvg15, err := strconv.ParseFloat(parts[2], 64)
		if err != nil {
			return 0, 0, 0, err
		}

		return loadAvg1, loadAvg5, loadAvg15, nil

	case "linux": // Linux
		// Linux에서는 /proc/loadavg 파일을 읽어 평균 부하를 가져옵니다.
		data, err := os.ReadFile("/proc/loadavg")
		if err != nil {
			return 0, 0, 0, err
		}

		// 파일 내용을 파싱합니다.
		// 형식: 1.23 0.45 0.12 1/123 45678
		parts := strings.Split(string(data), " ")

		if len(parts) < 3 {
			return 0, 0, 0, fmt.Errorf("예상치 못한 출력 형식: %s", string(data))
		}

		loadAvg1, err := strconv.ParseFloat(parts[0], 64)
		if err != nil {
			return 0, 0, 0, err
		}

		loadAvg5, err := strconv.ParseFloat(parts[1], 64)
		if err != nil {
			return 0, 0, 0, err
		}

		loadAvg15, err := strconv.ParseFloat(parts[2], 64)
		if err != nil {
			return 0, 0, 0, err
		}

		return loadAvg1, loadAvg5, loadAvg15, nil

	default:
		return 0, 0, 0, fmt.Errorf("지원하지 않는 운영 체제: %s", runtime.GOOS)
	}
}

func serveHTTP() {
	gin.SetMode(gin.ReleaseMode)

	router := gin.Default()
	router.Use(CORSMiddleware())

	if _, err := os.Stat("./web"); !os.IsNotExist(err) {
		router.LoadHTMLGlob("web/templates/*")
		router.GET("/", HTTPAPIServerIndex)
		router.GET("/stream/player/:uuid", HTTPAPIServerStreamPlayer)
	}
	router.GET("/stream/codec/:uuid", HTTPAPIServerStreamCodec)
	
	router.GET("/stream/rtsp/:uuid", func(c *gin.Context) {
		uuid := c.Param("uuid")
		
		if !Config.ext(uuid) {
			c.JSON(http.StatusNotFound, gin.H{"error": "Stream not found"})
			return
		}
		
		Config.RunIFNotRun(uuid)
		
		rtspPort := Config.Server.RTSPPort
		if rtspPort[0] == ':' {
			rtspPort = rtspPort[1:]
		}
		
		hostname := c.Request.Host
		if hostname == "" {
			hostname = "localhost"
		} else {
			if portIndex := strings.Index(hostname, ":"); portIndex > 0 {
				hostname = hostname[:portIndex]
			}
		}
		
		rtspURL := fmt.Sprintf("rtsp://%s:%s/%s", hostname, rtspPort, uuid)
		
		c.JSON(http.StatusOK, gin.H{
			"uuid":     uuid,
			"rtsp_url": rtspURL,
			"status":   true,
		})
		
		log.Printf("RTSP stream requested: %s", uuid)
	})

	// 스트리밍 상태 모니터링 API 추가
	router.GET("/stream/api/status", HTTPAPIServerStatus)
	router.GET("/stream/api/status/:uuid", HTTPAPIServerStatusByUUID)

	// 서버 상태 모니터링 API 추가
	router.GET("/stream/api/server/status", HTTPAPIServerSystemStatus)

	// 네트워크 통계를 주기적으로 업데이트하는 고루틴 시작
	go func() {
		// 초기 네트워크 통계 수집
		updateNetworkStats()

		// 5초마다 네트워크 통계 업데이트
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()

		for range ticker.C {
			updateNetworkStats()
		}
	}()

	router.StaticFS("/static", http.Dir("web/static"))
	err := router.Run(Config.Server.HTTPPort)
	if err != nil {
		log.Fatalln("Start HTTP Server error", err)
	}
}

// HTTPAPIServerStatus는 모든 스트림의 상태 정보를 반환합니다.
func HTTPAPIServerStatus(c *gin.Context) {
	_, all := Config.list()
	sort.Strings(all)

	var streams []StreamStatus
	var activeCount int
	for _, uuid := range all {
		stream := Config.getStreamStatus(uuid)
		streams = append(streams, stream)
		if stream.Status {
			activeCount++
		}
	}

	response := StreamStatusResponse{
		Streams:     streams,
		Total:       len(streams),
		ActiveCount: activeCount,
	}

	c.JSON(http.StatusOK, response)
}

// HTTPAPIServerStatusByUUID는 특정 UUID의 스트림 상태 정보를 반환합니다.
func HTTPAPIServerStatusByUUID(c *gin.Context) {
	uuid := c.Param("uuid")

	if !Config.ext(uuid) {
		c.JSON(http.StatusNotFound, gin.H{"error": "Stream not found"})
		return
	}

	stream := Config.getStreamStatus(uuid)
	c.JSON(http.StatusOK, stream)
}

// HTTPAPIServerIndex  index
func HTTPAPIServerIndex(c *gin.Context) {
	_, all := Config.list()
	if len(all) > 0 {
		c.Header("Cache-Control", "no-cache, max-age=0, must-revalidate, no-store")
		c.Header("Access-Control-Allow-Origin", "*")
		c.Redirect(http.StatusMovedPermanently, "stream/player/"+all[0])
	} else {
		c.HTML(http.StatusOK, "index.tmpl", gin.H{
			"port":    Config.Server.HTTPPort,
			"version": time.Now().String(),
		})
	}
}

// HTTPAPIServerStreamPlayer stream player
func HTTPAPIServerStreamPlayer(c *gin.Context) {
	_, all := Config.list()
	sort.Strings(all)
	c.HTML(http.StatusOK, "player.tmpl", gin.H{
		"port":     Config.Server.HTTPPort,
		"suuid":    c.Param("uuid"),
		"suuidMap": all,
		"version":  time.Now().String(),
	})
}

// HTTPAPIServerStreamCodec stream codec
func HTTPAPIServerStreamCodec(c *gin.Context) {
	if Config.ext(c.Param("uuid")) {
		Config.RunIFNotRun(c.Param("uuid"))
		codecs := Config.coGe(c.Param("uuid"))
		if codecs == nil {
			return
		}
		var tmpCodec []JCodec
		for _, codec := range codecs {
			if codec.Type() != av.H264 && codec.Type() != av.PCM_ALAW && codec.Type() != av.PCM_MULAW && codec.Type() != av.OPUS {
				log.Println("Codec Not Supported WebRTC ignore this track", codec.Type())
				continue
			}
			if codec.Type().IsVideo() {
				tmpCodec = append(tmpCodec, JCodec{Type: "video"})
			} else {
				tmpCodec = append(tmpCodec, JCodec{Type: "audio"})
			}
		}
		b, err := json.Marshal(tmpCodec)
		if err == nil {
			_, err = c.Writer.Write(b)
			if err != nil {
				log.Println("Write Codec Info error", err)
				return
			}
		}
	}
}

// HTTPAPIServerStreamWebRTC stream video over WebRTC
func HTTPAPIServerStreamWebRTC(c *gin.Context) {
	if !Config.ext(c.PostForm("suuid")) {
		log.Println("Stream Not Found")
		return
	}
	Config.RunIFNotRun(c.PostForm("suuid"))
	codecs := Config.coGe(c.PostForm("suuid"))
	if codecs == nil {
		log.Println("Stream Codec Not Found")
		return
	}
	var AudioOnly bool
	if len(codecs) == 1 && codecs[0].Type().IsAudio() {
		AudioOnly = true
	}
	muxerWebRTC := webrtc.NewMuxer(webrtc.Options{
		ICEServers:    Config.GetICEServers(),
		ICEUsername:   Config.GetICEUsername(),
		ICECredential: Config.GetICECredential(),
		PortMin:       Config.GetWebRTCPortMin(),
		PortMax:       Config.GetWebRTCPortMax(),
	})
	answer, err := muxerWebRTC.WriteHeader(codecs, c.PostForm("data"))
	if err != nil {
		log.Println("WriteHeader", err)
		return
	}
	_, err = c.Writer.Write([]byte(answer))
	if err != nil {
		log.Println("Write", err)
		return
	}
	go func() {
		cid, ch := Config.clAd(c.PostForm("suuid"))
		defer Config.clDe(c.PostForm("suuid"), cid)
		defer muxerWebRTC.Close()
		var videoStart bool
		noVideo := time.NewTimer(10 * time.Second)

		// 패킷 버퍼링을 위한 채널
		packetBuffer := make(chan av.Packet, 100)

		// 패킷 처리 고루틴
		go func() {
			for pck := range packetBuffer {
				if pck.IsKeyFrame || AudioOnly {
					noVideo.Reset(10 * time.Second)
					videoStart = true
				}
				if !videoStart && !AudioOnly {
					continue
				}
				err = muxerWebRTC.WritePacket(pck)
				if err != nil {
					log.Println("WritePacket", err)
					return
				}
			}
		}()

		for {
			select {
			case <-noVideo.C:
				log.Println("noVideo")
				return
			case pck := <-ch:
				select {
				case packetBuffer <- pck:
					// 패킷이 성공적으로 버퍼에 추가됨
				default:
					// 버퍼가 가득 찼을 때는 가장 오래된 패킷을 버림
					<-packetBuffer      // 가장 오래된 패킷 제거
					packetBuffer <- pck // 새 패킷 추가
				}
			}
		}
	}()
}

func CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Credentials", "true")
		c.Header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization, x-access-token")
		c.Header("Access-Control-Expose-Headers", "Content-Length, Access-Control-Allow-Origin, Access-Control-Allow-Headers, Cache-Control, Content-Language, Content-Type")
		c.Header("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

type Response struct {
	Tracks []string `json:"tracks"`
	Sdp64  string   `json:"sdp64"`
}

type ResponseError struct {
	Error string `json:"error"`
}

func HTTPAPIServerStreamWebRTC2(c *gin.Context) {
	url := c.PostForm("url")
	if _, ok := Config.Streams[url]; !ok {
		Config.Streams[url] = StreamST{
			URL:      url,
			OnDemand: true,
			Cl:       make(map[string]viewer),
		}
	}

	Config.RunIFNotRun(url)

	codecs := Config.coGe(url)
	if codecs == nil {
		log.Println("Stream Codec Not Found")
		c.JSON(500, ResponseError{Error: Config.LastError.Error()})
		return
	}

	muxerWebRTC := webrtc.NewMuxer(
		webrtc.Options{
			ICEServers: Config.GetICEServers(),
			PortMin:    Config.GetWebRTCPortMin(),
			PortMax:    Config.GetWebRTCPortMax(),
		},
	)

	sdp64 := c.PostForm("sdp64")
	answer, err := muxerWebRTC.WriteHeader(codecs, sdp64)
	if err != nil {
		log.Println("Muxer WriteHeader", err)
		c.JSON(500, ResponseError{Error: err.Error()})
		return
	}

	response := Response{
		Sdp64: answer,
	}

	for _, codec := range codecs {
		if codec.Type() != av.H264 &&
			codec.Type() != av.PCM_ALAW &&
			codec.Type() != av.PCM_MULAW &&
			codec.Type() != av.OPUS {
			log.Println("Codec Not Supported WebRTC ignore this track", codec.Type())
			continue
		}
		if codec.Type().IsVideo() {
			response.Tracks = append(response.Tracks, "video")
		} else {
			response.Tracks = append(response.Tracks, "audio")
		}
	}

	c.JSON(200, response)

	AudioOnly := len(codecs) == 1 && codecs[0].Type().IsAudio()

	go func() {
		cid, ch := Config.clAd(url)
		defer Config.clDe(url, cid)
		defer muxerWebRTC.Close()
		var videoStart bool
		noVideo := time.NewTimer(10 * time.Second)
		for {
			select {
			case <-noVideo.C:
				log.Println("noVideo")
				return
			case pck := <-ch:
				if pck.IsKeyFrame || AudioOnly {
					noVideo.Reset(10 * time.Second)
					videoStart = true
				}
				if !videoStart && !AudioOnly {
					continue
				}
				err = muxerWebRTC.WritePacket(pck)
				if err != nil {
					log.Println("WritePacket", err)
					return
				}
			}
		}
	}()
}

// HTTPAPIServerSystemStatus는 서버의 현재 상태를 반환합니다.
func HTTPAPIServerSystemStatus(c *gin.Context) {
	status := ServerStatus{}

	// CPU 정보 수집
	status.CPU.NumCPU = runtime.NumCPU()

	// 시스템 평균 부하 정보 수집
	loadAvg1, loadAvg5, loadAvg15, err := getLoadAverage()
	if err == nil {
		status.CPU.LoadAvg1 = loadAvg1
		status.CPU.LoadAvg5 = loadAvg5
		status.CPU.LoadAvg15 = loadAvg15
	} else {
		log.Printf("시스템 평균 부하 정보 수집 실패: %v", err)
	}

	// 메모리 정보 수집 - 가비지 컬렉션 강제 실행 후 측정
	runtime.GC() // 가비지 컬렉션 강제 실행

	// 여러 번 측정하여 평균 계산 (더 안정적인 결과를 위해)
	var totalMemStats runtime.MemStats
	const numSamples = 3

	for i := 0; i < numSamples; i++ {
		var memStats runtime.MemStats
		runtime.ReadMemStats(&memStats)

		totalMemStats.Sys += memStats.Sys
		totalMemStats.Alloc += memStats.Alloc
		totalMemStats.HeapObjects += memStats.HeapObjects
		totalMemStats.HeapAlloc += memStats.HeapAlloc
		totalMemStats.HeapSys += memStats.HeapSys

		// 측정 간 짧은 대기
		time.Sleep(10 * time.Millisecond)
	}

	// 평균 계산
	status.Memory.Total = totalMemStats.Sys / uint64(numSamples)
	status.Memory.Used = totalMemStats.Alloc / uint64(numSamples)
	status.Memory.Free = (totalMemStats.Sys - totalMemStats.Alloc) / uint64(numSamples)
	status.Memory.UsagePercent = float64(totalMemStats.Alloc) / float64(totalMemStats.Sys) * 100

	// Go 런타임 정보 수집
	status.GoRuntime.Version = runtime.Version()
	status.GoRuntime.NumGoroutine = runtime.NumGoroutine()
	status.GoRuntime.GOMAXPROCS = runtime.GOMAXPROCS(0)
	status.GoRuntime.NumCPU = runtime.NumCPU()
	status.GoRuntime.CGOCalls = runtime.NumCgoCall()

	// 가비지 컬렉션 정보 수집
	var memStats runtime.MemStats
	runtime.ReadMemStats(&memStats)
	status.GoRuntime.NumGC = memStats.NumGC
	status.GoRuntime.HeapObjects = totalMemStats.HeapObjects / uint64(numSamples)
	status.GoRuntime.HeapAlloc = totalMemStats.HeapAlloc / uint64(numSamples)
	status.GoRuntime.HeapSys = totalMemStats.HeapSys / uint64(numSamples)

	// 프로세스 정보 수집 (운영체제별 구현)
	var rusage syscall.Rusage
	syscall.Getrusage(syscall.RUSAGE_SELF, &rusage)

	// NumFD 설정 (Maxrss는 최대 상주 세트 크기)
	status.Process.NumFD = int32(rusage.Maxrss)

	// CPUTime 설정
	status.Process.CPUTime = float64(rusage.Utime.Sec+rusage.Stime.Sec) +
		float64(rusage.Utime.Usec+rusage.Stime.Usec)/1e6

	// 운영체제별 프로세스 정보 수집
	switch runtime.GOOS {
	case "darwin", "linux":
		// NumThreads 설정 (Darwin과 Linux)
		status.Process.NumThreads = int32(runtime.GOMAXPROCS(0))

		// VirtualSize와 ResidentSize 설정
		// Darwin과 Linux에서는 /proc/self/statm 또는 sysctl을 통해 정보를 가져올 수 있습니다.
		if runtime.GOOS == "linux" {
			// Linux: /proc/self/statm 파일에서 정보 읽기
			if data, err := os.ReadFile("/proc/self/statm"); err == nil {
				fields := strings.Fields(string(data))
				if len(fields) >= 2 {
					// 첫 번째 필드는 가상 메모리 크기 (페이지 단위)
					if vsize, err := strconv.ParseUint(fields[0], 10, 64); err == nil {
						// 페이지 크기(4096)를 곱하여 바이트 단위로 변환
						status.Process.VirtualSize = vsize * 4096
					}

					// 두 번째 필드는 상주 메모리 크기 (페이지 단위)
					if rsize, err := strconv.ParseUint(fields[1], 10, 64); err == nil {
						// 페이지 크기(4096)를 곱하여 바이트 단위로 변환
						status.Process.ResidentSize = rsize * 4096
					}
				}
			}
		} else if runtime.GOOS == "darwin" {
			// macOS: sysctl을 통해 정보 가져오기
			// 가상 메모리 크기
			if cmd := exec.Command("sysctl", "-n", "vm.swapusage"); cmd != nil {
				if _, err := cmd.Output(); err == nil {
					// 출력 형식: vm.swapusage: total = 1024.00M  used = 512.00M  free = 512.00M
					// 여기서는 간단히 메모리 사용량을 ResidentSize로 설정
					status.Process.ResidentSize = totalMemStats.HeapAlloc / uint64(numSamples)
					status.Process.VirtualSize = totalMemStats.HeapSys / uint64(numSamples)
				}
			}
		}
	case "windows":
		// Windows에서는 다른 방식으로 정보를 가져와야 합니다.
		// 여기서는 간단히 Go 런타임 정보를 사용합니다.
		status.Process.NumThreads = int32(runtime.NumGoroutine())
		status.Process.VirtualSize = totalMemStats.HeapSys / uint64(numSamples)
		status.Process.ResidentSize = totalMemStats.HeapAlloc / uint64(numSamples)
	default:
		// 지원하지 않는 운영체제
		log.Printf("지원하지 않는 운영체제: %s", runtime.GOOS)
	}

	// 네트워크 통계 수집
	updateNetworkStats()

	// 네트워크 통계 정보 설정
	status.Network.BytesSent = networkStats.BytesSent
	status.Network.BytesReceived = networkStats.BytesReceived
	status.Network.PacketsSent = networkStats.PacketsSent
	status.Network.PacketsReceived = networkStats.PacketsReceived
	status.Network.LastUpdate = networkStats.LastUpdate.Format(time.RFC3339)

	// 초당 전송/수신 바이트 계산 (이전 통계와 비교)
	elapsedSeconds := networkStats.LastUpdate.Sub(prevNetworkStats.LastUpdate).Seconds()
	if elapsedSeconds > 0 {
		// 이전 통계와 비교하여 초당 전송/수신 바이트 계산
		bytesSentDiff := networkStats.BytesSent - prevNetworkStats.BytesSent
		bytesRecvDiff := networkStats.BytesReceived - prevNetworkStats.BytesReceived

		status.Network.BytesSentRate = float64(bytesSentDiff) / elapsedSeconds
		status.Network.BytesRecvRate = float64(bytesRecvDiff) / elapsedSeconds
	}

	// 서버 가동 시간
	status.Uptime = time.Since(serverStartTime).Seconds()

	c.JSON(http.StatusOK, status)
}

// getStreamStatus는 특정 UUID의 스트림 상태 정보를 반환합니다.
func (element *ConfigST) getStreamStatus(uuid string) StreamStatus {
	element.mutex.RLock()
	defer element.mutex.RUnlock()

	stream, exists := element.Streams[uuid]
	if !exists {
		return StreamStatus{
			UUID:        uuid,
			LastUpdated: time.Now(),
		}
	}

	// 뷰어 수 계산
	viewerCount := len(stream.Cl)

	// 마지막 오류 정보 가져오기
	lastError := ""
	if element.LastError != nil {
		lastError = element.LastError.Error()
	}

	// 옵션이 없는 경우에만 전역 옵션 사용
	onDemand := stream.OnDemand
	disableAudio := stream.DisableAudio
	debug := stream.Debug

	// 각 옵션이 기본값(false)인 경우에만 전역 옵션 사용
	if !onDemand {
		onDemand = element.StreamDefaults.OnDemand
	}
	if !disableAudio {
		disableAudio = element.StreamDefaults.DisableAudio
	}
	if !debug {
		debug = element.StreamDefaults.Debug
	}

	rtspPort := element.Server.RTSPPort
	if rtspPort[0] == ':' {
		rtspPort = rtspPort[1:]
	}
	
	rtspURL := fmt.Sprintf("rtsp://localhost:%s/%s", rtspPort, uuid)
	
	return StreamStatus{
		UUID:           uuid,
		URL:            stream.URL,
		RtspUrl:        rtspURL,
		Status:         stream.Status,
		OnDemand:       onDemand,
		DisableAudio:   disableAudio,
		Debug:          debug,
		ViewerCount:    viewerCount,
		LastError:      lastError,
		LastUpdated:    time.Now(),
		IsRunning:      stream.IsRunning,
		ReconnectCount: stream.ReconnectCount,
	}
}
