package main

import (
	"archive/zip"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

// LogWriter는 로그 파일을 관리하는 구조체입니다.
type LogWriter struct {
	file    *os.File
	dir     string
	prefix  string
	maxSize int64
	curSize int64
}

// Write는 로그 데이터를 파일에 쓰고 필요시 로테이션을 수행합니다.
func (w *LogWriter) Write(p []byte) (n int, err error) {
	// 파일 크기 확인 및 로테이션
	if w.curSize+int64(len(p)) > w.maxSize {
		w.rotate()
	}

	// 데이터 쓰기
	n, err = w.file.Write(p)
	w.curSize += int64(n)
	return
}

// rotate는 로그 파일을 로테이션합니다.
func (w *LogWriter) rotate() {
	// 현재 파일 닫기
	w.file.Close()

	// 새 파일명 생성 (날짜_시간.log)
	newFileName := filepath.Join(w.dir, time.Now().Format("2006-01-02_15-04-05")+".log")

	// 새 파일 열기
	newFile, err := os.OpenFile(newFileName, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Printf("로그 파일 로테이션 실패: %v", err)
		return
	}

	// 이전 파일 참조 업데이트
	w.file = newFile
	w.curSize = 0

	// 오래된 로그 파일 정리 및 압축
	go w.cleanOldLogs()
}

// cleanOldLogs는 7일이 지난 로그 파일을 찾아 압축하고, 30일이 지난 압축 파일을 삭제합니다.
func (w *LogWriter) cleanOldLogs() {
	// 7일 전 날짜 계산 (로그 파일 압축용)
	cutoffDate := time.Now().AddDate(0, 0, -7)
	// 30일 전 날짜 계산 (압축 파일 삭제용)
	zipCutoffDate := time.Now().AddDate(0, 0, -30)

	// logs 디렉토리의 모든 파일 검사
	files, err := os.ReadDir(w.dir)
	if err != nil {
		log.Printf("로그 디렉토리 읽기 실패: %v", err)
		return
	}

	for _, file := range files {
		if file.IsDir() {
			continue
		}

		// 파일 정보 가져오기
		info, err := file.Info()
		if err != nil {
			continue
		}

		// .zip 파일인 경우 30일이 지났는지 확인
		if filepath.Ext(file.Name()) == ".zip" {
			if info.ModTime().Before(zipCutoffDate) {
				// 30일이 지난 압축 파일 삭제
				err := os.Remove(filepath.Join(w.dir, file.Name()))
				if err != nil {
					log.Printf("압축 파일 삭제 실패: %v", err)
				} else {
					log.Printf("오래된 압축 파일 삭제 완료: %s", file.Name())
				}
			}
			continue
		}

		// .log 파일만 처리
		if filepath.Ext(file.Name()) != ".log" {
			continue
		}

		// 파일 수정 시간이 7일보다 오래된 경우
		if info.ModTime().Before(cutoffDate) {
			// 압축 파일명 생성
			zipFileName := filepath.Join(w.dir, file.Name()+".zip")

			// 압축 파일 생성
			zipFile, err := os.Create(zipFileName)
			if err != nil {
				log.Printf("압축 파일 생성 실패: %v", err)
				continue
			}

			// ZIP writer 생성
			zipWriter := zip.NewWriter(zipFile)

			// 원본 파일 열기
			srcFile, err := os.Open(filepath.Join(w.dir, file.Name()))
			if err != nil {
				zipFile.Close()
				zipWriter.Close()
				continue
			}

			// ZIP 파일에 추가
			writer, err := zipWriter.Create(file.Name())
			if err != nil {
				srcFile.Close()
				zipFile.Close()
				zipWriter.Close()
				continue
			}

			// 파일 내용 복사
			_, err = io.Copy(writer, srcFile)
			srcFile.Close()
			zipWriter.Close()
			zipFile.Close()

			if err == nil {
				// 원본 파일 삭제
				os.Remove(filepath.Join(w.dir, file.Name()))
				log.Printf("로그 파일 압축 완료: %s", file.Name())
			}
		}
	}
}

func updateStreamsPeriodically() {
	ticker := time.NewTicker(time.Duration(Config.API.RetryInterval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			streams, err := loadStreamsFromAPI(Config.API)
			if err == nil && len(streams) > 0 {
				Config.mutex.Lock()
				// 기존 streams의 상태 정보 보존
				for id, newStream := range streams {
					if oldStream, exists := Config.Streams[id]; exists {
						newStream.Status = oldStream.Status
						newStream.OnDemand = oldStream.OnDemand
						newStream.DisableAudio = oldStream.DisableAudio
						newStream.Debug = oldStream.Debug
						newStream.RunLock = oldStream.RunLock
						newStream.Cl = oldStream.Cl
						newStream.Codecs = oldStream.Codecs
						newStream.IsRunning = oldStream.IsRunning
						newStream.LastError = oldStream.LastError
						newStream.LastUpdated = oldStream.LastUpdated
						newStream.ViewerCount = oldStream.ViewerCount
						newStream.ReconnectCount = oldStream.ReconnectCount
					} else {
						// 새로운 stream에 기본값 적용
						newStream.OnDemand = Config.StreamDefaults.OnDemand
						newStream.DisableAudio = Config.StreamDefaults.DisableAudio
						newStream.Debug = Config.StreamDefaults.Debug
						newStream.Cl = make(map[string]viewer)
					}
					streams[id] = newStream
				}
				Config.Streams = streams
				Config.mutex.Unlock()
				log.Println("Streams 정보가 성공적으로 업데이트되었습니다.")
			} else {
				log.Printf("Streams 정보 업데이트 실패: %v", err)
			}
		}
	}
}

func main() {
	// logs 디렉토리 생성 (상대 경로 수정)
	logsDir := "../logs"
	if err := os.MkdirAll(logsDir, 0755); err != nil {
		log.Fatalf("로그 디렉토리 생성 실패: %v", err)
	}

	// 로그 파일 설정
	logFileName := filepath.Join(logsDir, time.Now().Format("2006-01-02")+".log")
	logFile, err := os.OpenFile(logFileName, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Fatalf("로그 파일 열기 실패: %v", err)
	}
	defer logFile.Close()

	// 로그 파일 크기 확인
	fileInfo, err := logFile.Stat()
	if err != nil {
		log.Fatalf("로그 파일 정보 확인 실패: %v", err)
	}

	// 로그 라이터 설정 (최대 10MB)
	logWriter := &LogWriter{
		file:    logFile,
		dir:     logsDir,
		prefix:  "rtsp-rtsp",
		maxSize: 10 * 1024 * 1024, // 10MB
		curSize: fileInfo.Size(),
	}

	// 로그 출력을 파일과 표준 출력으로 설정
	multiWriter := io.MultiWriter(os.Stdout, logWriter)
	log.SetOutput(multiWriter)
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)

	// 시작 시 오래된 로그 파일 정리
	go logWriter.cleanOldLogs()

	// API 라우트 설정
	http.HandleFunc("/api/status", HandleStreamStatus)
	http.HandleFunc("/api/status/", func(w http.ResponseWriter, r *http.Request) {
		uuid := strings.TrimPrefix(r.URL.Path, "/api/status/")
		HandleSingleStreamStatus(w, r, uuid)
	})
	http.HandleFunc("/api/server/stats", HandleServerStats)

	err = StartGStreamerServer(strings.TrimPrefix(Config.Server.RTSPPort, ":"))
	if err != nil {
		log.Fatalf("RTSP 서버 시작 실패: %v", err)
	}
	log.Println("RTSP Server started on port", Config.Server.RTSPPort)

	go serveHTTP()
	go serveStreams()
	// go updateStreamsPeriodically() // streams 정보 주기적 업데이트 시작

	sigs := make(chan os.Signal, 1)
	done := make(chan bool, 1)
	signal.Notify(sigs, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigs
		log.Println(sig)
		StopGStreamerServer() // Stop GStreamer RTSP server on shutdown
		done <- true
	}()
	log.Println("Server Start Awaiting Signal")
	<-done
	log.Println("Exiting")
}
