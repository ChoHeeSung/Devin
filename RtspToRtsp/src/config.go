package main

import (
	"crypto/rand"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/deepch/vdk/codec/h264parser"

	"github.com/deepch/vdk/av"
)

// Config global
var Config = loadConfig()

// ConfigST struct
type ConfigST struct {
	mutex          sync.RWMutex
	Server         ServerST            `json:"server"`
	StreamDefaults StreamST            `json:"stream_defaults"`
	API            APIST               `json:"api"`
	Streams        map[string]StreamST `json:"streams"`
	LastError      error
}

// APIST struct
type APIST struct {
	CCTVMasterURL string `json:"cctv_master_url"`
	RetryInterval int    `json:"retry_interval"`
	Timeout       int    `json:"timeout"`
}

// CCTVResponse struct
type CCTVResponse struct {
	EquipID string `json:"equipId"`
	RtspURL string `json:"rtspUrl"`
}

// ServerST struct
type ServerST struct {
	HTTPPort      string   `json:"http_port"`
	RTSPPort      string   `json:"rtsp_port"`
	ICEServers    []string `json:"ice_servers"`
	ICEUsername   string   `json:"ice_username"`
	ICECredential string   `json:"ice_credential"`
	WebRTCPortMin uint16   `json:"webrtc_port_min"`
	WebRTCPortMax uint16   `json:"webrtc_port_max"`
}

// StreamST struct
type StreamST struct {
	URL            string `json:"url"`
	Status         bool   `json:"status"`
	OnDemand       bool   `json:"on_demand"`
	DisableAudio   bool   `json:"disable_audio"`
	Debug          bool   `json:"debug"`
	RunLock        bool   `json:"-"`
	Codecs         []av.CodecData
	Cl             map[string]viewer
	LastError      error     `json:"last_error"`
	LastUpdated    time.Time `json:"last_updated"`
	ViewerCount    int       `json:"viewer_count"`
	IsRunning      bool      `json:"is_running"`
	ReconnectCount int       `json:"reconnect_count"`
}

type viewer struct {
	c chan av.Packet
}

func loadConfig() *ConfigST {
	var tmp ConfigST
	data, err := os.ReadFile("../config/config.json")
	if err == nil {
		err = json.Unmarshal(data, &tmp)
		if err != nil {
			log.Fatalln(err)
		}

		// REST API에서 streams 정보 가져오기 시도
		streams, err := loadStreamsFromAPI(tmp.API)
		if err == nil && len(streams) > 0 {
			tmp.Streams = streams
		} else {
			log.Printf("Failed to load streams from API: %v. Using config file streams.", err)
		}

		for i, v := range tmp.Streams {
			// 전역 옵션 적용
			if !v.OnDemand {
				v.OnDemand = tmp.StreamDefaults.OnDemand
			}
			if !v.DisableAudio {
				v.DisableAudio = tmp.StreamDefaults.DisableAudio
			}
			if !v.Debug {
				v.Debug = tmp.StreamDefaults.Debug
			}
			v.Cl = make(map[string]viewer)
			tmp.Streams[i] = v
		}
	} else {
		addr := flag.String("listen", "8083", "HTTP host:port")
		udpMin := flag.Int("udp_min", 0, "WebRTC UDP port min")
		udpMax := flag.Int("udp_max", 0, "WebRTC UDP port max")
		iceServer := flag.String("ice_server", "", "ICE Server")
		flag.Parse()

		tmp.Server.HTTPPort = *addr
		tmp.Server.WebRTCPortMin = uint16(*udpMin)
		tmp.Server.WebRTCPortMax = uint16(*udpMax)
		if len(*iceServer) > 0 {
			tmp.Server.ICEServers = []string{*iceServer}
		}

		tmp.Streams = make(map[string]StreamST)
	}
	return &tmp
}

func loadStreamsFromAPI(api APIST) (map[string]StreamST, error) {
	if api.CCTVMasterURL == "" {
		return nil, fmt.Errorf("CCTV master URL not configured")
	}

	client := &http.Client{
		Timeout: time.Duration(api.Timeout) * time.Second,
	}

	resp, err := client.Get(api.CCTVMasterURL)
	if err != nil {
		return nil, fmt.Errorf("failed to fetch CCTV data: %v", err)
	}
	defer resp.Body.Close()

	var cctvData []CCTVResponse
	if err := json.NewDecoder(resp.Body).Decode(&cctvData); err != nil {
		return nil, fmt.Errorf("failed to decode CCTV data: %v", err)
	}

	streams := make(map[string]StreamST)
	for _, cctv := range cctvData {
		if cctv.EquipID != "" && cctv.RtspURL != "" {
			streams[cctv.EquipID] = StreamST{
				URL: cctv.RtspURL,
			}
		}
	}

	return streams, nil
}

func (element *ConfigST) RunIFNotRun(uuid string) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	if tmp, ok := element.Streams[uuid]; ok {
		if tmp.OnDemand && !tmp.RunLock {
			tmp.RunLock = true
			element.Streams[uuid] = tmp
			go RTSPWorkerLoop(uuid, tmp.URL, tmp.OnDemand, tmp.DisableAudio, tmp.Debug)
		}
	}
}

func (element *ConfigST) RunUnlock(uuid string) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	if tmp, ok := element.Streams[uuid]; ok {
		if tmp.OnDemand && tmp.RunLock {
			tmp.RunLock = false
			element.Streams[uuid] = tmp
		}
	}
}

func (element *ConfigST) HasViewer(uuid string) bool {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	if tmp, ok := element.Streams[uuid]; ok && len(tmp.Cl) > 0 {
		return true
	}
	return false
}

func (element *ConfigST) GetICEServers() []string {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	return element.Server.ICEServers
}

func (element *ConfigST) GetICEUsername() string {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	return element.Server.ICEUsername
}

func (element *ConfigST) GetICECredential() string {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	return element.Server.ICECredential
}

func (element *ConfigST) GetWebRTCPortMin() uint16 {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	return element.Server.WebRTCPortMin
}

func (element *ConfigST) GetWebRTCPortMax() uint16 {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	return element.Server.WebRTCPortMax
}

func (element *ConfigST) cast(uuid string, pck av.Packet) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	for _, v := range element.Streams[uuid].Cl {
		if len(v.c) < cap(v.c) {
			v.c <- pck
		}
	}
}

func (element *ConfigST) ext(suuid string) bool {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	_, ok := element.Streams[suuid]
	return ok
}

func (element *ConfigST) coAd(suuid string, codecs []av.CodecData) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	t := element.Streams[suuid]
	t.Codecs = codecs
	element.Streams[suuid] = t
}

func (element *ConfigST) coGe(suuid string) []av.CodecData {
	for i := 0; i < 100; i++ {
		element.mutex.RLock()
		tmp, ok := element.Streams[suuid]
		element.mutex.RUnlock()
		if !ok {
			return nil
		}
		if tmp.Codecs != nil {
			//TODO Delete test
			for _, codec := range tmp.Codecs {
				if codec.Type() == av.H264 {
					codecVideo := codec.(h264parser.CodecData)
					if codecVideo.SPS() != nil && codecVideo.PPS() != nil && len(codecVideo.SPS()) > 0 && len(codecVideo.PPS()) > 0 {
						//ok
						//log.Println("Ok Video Ready to play")
					} else {
						//video codec not ok
						log.Println("Bad Video Codec SPS or PPS Wait")
						time.Sleep(50 * time.Millisecond)
						continue
					}
				}
			}
			return tmp.Codecs
		}
		time.Sleep(50 * time.Millisecond)
	}
	return nil
}

func (element *ConfigST) clAd(suuid string) (string, chan av.Packet) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	cuuid := pseudoUUID()
	ch := make(chan av.Packet, 100)
	element.Streams[suuid].Cl[cuuid] = viewer{c: ch}
	return cuuid, ch
}

func (element *ConfigST) list() (string, []string) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	var res []string
	var fist string
	for k := range element.Streams {
		if fist == "" {
			fist = k
		}
		res = append(res, k)
	}
	return fist, res
}
func (element *ConfigST) clDe(suuid, cuuid string) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	delete(element.Streams[suuid].Cl, cuuid)
}

func pseudoUUID() (uuid string) {
	b := make([]byte, 16)
	_, err := rand.Read(b)
	if err != nil {
		fmt.Println("Error: ", err)
		return
	}
	uuid = fmt.Sprintf("%X-%X-%X-%X-%X", b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
	return
}

func (element *ConfigST) UpdateStreamState(uuid string, status bool) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	if stream, ok := element.Streams[uuid]; ok {
		stream.Status = status
		stream.LastUpdated = time.Now()
		// is_running은 수정하지 않음 (스트림 루프가 여전히 실행 중인지 여부는 RTSPWorkerLoop에서 결정)
		element.Streams[uuid] = stream
	}
}

func (element *ConfigST) HandleStreamError(uuid string, err error) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	if stream, ok := element.Streams[uuid]; ok {
		// StreamST 직접 업데이트
		stream.LastError = err
		stream.LastUpdated = time.Now()
		stream.Status = false
		// is_running은 수정하지 않음 (스트림 루프가 여전히 실행 중인지 여부는 RTSPWorkerLoop에서 결정)
		element.Streams[uuid] = stream
	}
}

func (element *ConfigST) UpdateViewerCount(uuid string, count int) {
	element.mutex.Lock()
	defer element.mutex.Unlock()
	if stream, ok := element.Streams[uuid]; ok {
		// StreamST 직접 업데이트
		stream.ViewerCount = count
		stream.LastUpdated = time.Now()
		if count > 0 {
			stream.Status = true
		}
		element.Streams[uuid] = stream
	}
}
