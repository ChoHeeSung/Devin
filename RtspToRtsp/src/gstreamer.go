package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"sync"
	"time"
	"unsafe"
)

//
//
//
//
//
//   
//   
//
//
//   
//   
//   
//   
//   
//
//
//
import "C"

type GStreamerData struct {
	data      *C.GstRTSPData
	mutex     sync.RWMutex
	streams   map[string]*GStreamerStream
	startTime time.Time
	isRunning bool
}

type GStreamerStream struct {
	UUID       string
	URL        string
	OnDemand   bool
	ClientList map[string]bool
	Status     bool
	LowLatency bool
}

var gstData *GStreamerData

func initGStreamer() {
	args := os.Args
	argc := C.int(len(args))
	argv := make([]*C.char, argc)
	for i, arg := range args {
		argv[i] = C.CString(arg)
	}
	defer func() {
		for _, arg := range argv {
			C.free(unsafe.Pointer(arg))
		}
	}()

	C.gst_init((*C.int)(unsafe.Pointer(&argc)), (**C.char)(unsafe.Pointer(&argv[0])))
}

func StartGStreamerServer(port string) error {
	initGStreamer()

	portStr := C.CString(port)
	defer C.free(unsafe.Pointer(portStr))

	gstData = &GStreamerData{
		data:      C.create_rtsp_server(portStr),
		streams:   make(map[string]*GStreamerStream),
		startTime: time.Now(),
		isRunning: true,
	}

	log.Printf("GStreamer RTSP server starting on port %s", port)

	go C.start_rtsp_server(gstData.data)

	return nil
}

func StopGStreamerServer() {
	if gstData != nil && gstData.isRunning {
		log.Println("Stopping GStreamer RTSP server")
		gstData.isRunning = false
		C.stop_rtsp_server(gstData.data)
		C.destroy_rtsp_server(gstData.data)
		gstData = nil
	}
}

func RegisterStream(uuid string, url string, onDemand bool) error {
	if gstData == nil || !gstData.isRunning {
		return fmt.Errorf("GStreamer RTSP server not running")
	}

	gstData.mutex.Lock()
	defer gstData.mutex.Unlock()

	for existingUUID := range gstData.streams {
		if strings.EqualFold(existingUUID, uuid) {
			log.Printf("Stream already registered with different case: %s vs %s", existingUUID, uuid)
			return nil
		}
	}

	pipelineStr := fmt.Sprintf(
		"rtspsrc location=\"%s\" latency=0 buffer-mode=0 drop-on-latency=true protocols=tcp do-retransmission=false ! "+
			"rtph264depay ! h264parse ! rtph264pay name=pay0 config-interval=1 pt=96",
		url)

	pathStr := C.CString("/" + uuid)
	pipelineStrC := C.CString(pipelineStr)
	defer C.free(unsafe.Pointer(pathStr))
	defer C.free(unsafe.Pointer(pipelineStrC))

	C.add_rtsp_stream(gstData.data, pathStr, pipelineStrC, C.gboolean(boolToInt(onDemand)))

	gstData.streams[uuid] = &GStreamerStream{
		UUID:       uuid,
		URL:        url,
		OnDemand:   onDemand,
		ClientList: make(map[string]bool),
		Status:     true,
		LowLatency: true,
	}

	log.Printf("Registered GStreamer RTSP stream: %s", uuid)
	return nil
}

func UnregisterStream(uuid string) error {
	if gstData == nil || !gstData.isRunning {
		return fmt.Errorf("GStreamer RTSP server not running")
	}

	gstData.mutex.Lock()
	defer gstData.mutex.Unlock()

	if _, exists := gstData.streams[uuid]; !exists {
		return fmt.Errorf("Stream not found: %s", uuid)
	}

	pathStr := C.CString("/" + uuid)
	defer C.free(unsafe.Pointer(pathStr))

	C.remove_rtsp_stream(gstData.data, pathStr)

	delete(gstData.streams, uuid)

	log.Printf("Unregistered GStreamer RTSP stream: %s", uuid)
	return nil
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

func goMediaConfigureCallback(factory *C.GstRTSPMediaFactory, media *C.GstRTSPMedia, userData C.gpointer) {
	log.Println("Media configured")
}

func goClientConnectedCallback(server *C.GstRTSPServer, client *C.GstRTSPClient, userData C.gpointer) {
	log.Println("Client connected to RTSP server")
}
