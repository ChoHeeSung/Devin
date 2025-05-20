import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from config_manager import ConfigManager
from api_client import APIClient

# 로그 디렉토리 생성
Path('logs').mkdir(exist_ok=True)

def setup_logging(config: Dict[str, Any]) -> None:
    """로깅 설정을 초기화합니다."""
    log_config = config.get('logging', {})
    log_level = getattr(logging, log_config.get('level', 'DEBUG'))
    
    # 로그 포맷을 Python logging 형식으로 변환
    default_format = '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s'
    log_format = log_config.get('format', default_format)
    
    # 로그 포맷이 config에서 제공된 경우, Python logging 형식으로 변환
    if log_format != default_format:
        log_format = log_format.replace('{time:YYYY-MM-DD HH:mm:ss.SSS}', '%(asctime)s.%(msecs)03d')
        log_format = log_format.replace('{level: <8}', '%(levelname)-8s')
        log_format = log_format.replace('{name}', '%(name)s')
        log_format = log_format.replace('{function}', '%(funcName)s')
        log_format = log_format.replace('{line}', '%(lineno)d')
        log_format = log_format.replace('{message}', '%(message)s')
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('logs/rtsp_server.log'),
            logging.StreamHandler()
        ]
    )

class RTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, stream_config: Dict[str, Any]):
        super(RTSPMediaFactory, self).__init__()
        self.stream_config = stream_config
        self.logger = logging.getLogger('RTSP-Server')
        self.active_clients = 0
        self.pipeline = None
        self.rtspsrc = None
        self.logger.info(f'RTSPMediaFactory 초기화 완료: {stream_config["input_url"]}')
        
        # 온디맨드 설정 적용
        if stream_config.get('on_demand', True):
            self.set_shared(False)
            self.logger.info(f'온디맨드 모드 활성화 (max_clients: {stream_config.get("max_clients")})')

    def _stop_pipeline(self):
        """메인 스레드에서 파이프라인을 중지합니다."""
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.logger.info('파이프라인 종료됨')

    def _on_pad_removed(self, element, pad):
        self.logger.info('스트림 패드 제거됨')
        self.active_clients -= 1
        self.logger.info(f'현재 활성 클라이언트 수: {self.active_clients}')
        
        if self.active_clients == 0:
            self.logger.info('모든 클라이언트 연결 종료됨')
            # 메인 스레드에서 파이프라인 중지
            GLib.idle_add(self._stop_pipeline)

    def do_create_element(self, url):
        self.logger.info(f'do_create_element 호출됨: {url}')
        
        try:
            # GStreamer 파이프라인 생성
            pipeline_parts = [
                # 입력 소스 설정
                f'rtspsrc name=src location={self.stream_config["input_url"]}',
                f'latency=500',
                f'protocols={self.stream_config["rtsp_transport"]}',
                f'buffer-mode=none',  # 버퍼 모드 비활성화
                f'timeout=5',  # 타임아웃 감소
                f'user-id={self.stream_config.get("username", "")}',
                f'user-pw={self.stream_config.get("password", "")}',
                
                # 디코딩 및 파싱
                '! rtph264depay',
                '! h264parse',
                
                # 버퍼링 설정
                '! queue',
                f'max-size-buffers=100',  # 버퍼 크기 감소
                f'max-size-bytes=0',
                f'max-size-time=0',
                f'leaky=downstream',
                
                # 인코딩 및 패킷화
                f'! rtph264pay name=pay0 pt=96'
            ]
            
            pipeline_str = f'( {" ".join(pipeline_parts)} )'
            self.logger.info(f'파이프라인 생성: {pipeline_str}')
            
            # 파이프라인 생성 및 버스 모니터링 설정
            self.pipeline = Gst.parse_launch(pipeline_str)
            if not self.pipeline:
                self.logger.error('파이프라인 생성 실패')
                return None
                
            self.rtspsrc = self.pipeline.get_by_name('src')
            if not self.rtspsrc:
                self.logger.error('rtspsrc 요소를 찾을 수 없음')
                return None
            
            # 버스 모니터링 설정
            bus = self.pipeline.get_bus()
            if bus:
                bus.add_signal_watch()
                bus.connect('message', self._on_bus_message)
            
            # rtspsrc 상태 모니터링
            self.rtspsrc.connect('pad-added', self._on_pad_added)
            self.rtspsrc.connect('pad-removed', self._on_pad_removed)
            
            # 파이프라인 상태 설정
            self.pipeline.set_state(Gst.State.PLAYING)
            
            return self.pipeline
            
        except Exception as e:
            self.logger.error(f'파이프라인 생성 중 에러 발생: {str(e)}')
            return None

    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            self.logger.error(f'GStreamer 에러: {err.message}')
            self.logger.debug(f'디버그 정보: {debug}')
            
            # 에러 발생 시 파이프라인 재시작
            if self.pipeline:
                self.logger.info('파이프라인 재시작 시도...')
                self.pipeline.set_state(Gst.State.NULL)
                self.pipeline.set_state(Gst.State.PLAYING)
                
        elif t == Gst.MessageType.EOS:
            self.logger.info('스트림 종료 (EOS)')
            # EOS 발생 시 파이프라인 재시작
            if self.pipeline:
                self.logger.info('파이프라인 재시작 시도...')
                self.pipeline.set_state(Gst.State.NULL)
                self.pipeline.set_state(Gst.State.PLAYING)
                
        elif t == Gst.MessageType.STATE_CHANGED:
            old, new, pending = message.parse_state_changed()
            if message.src == self.pipeline:
                self.logger.debug(f'파이프라인 상태 변경: {old.value_nick} -> {new.value_nick}')

    def _on_pad_added(self, element, pad):
        self.logger.info('스트림 패드 추가됨')
        self.active_clients += 1
        self.logger.info(f'현재 활성 클라이언트 수: {self.active_clients}')

    def do_configure(self, url):
        self.logger.info(f'스트림 설정: {url}')
        return True

def main():
    # 설정 관리자 초기화
    config_manager = ConfigManager()
    
    # 로깅 설정
    setup_logging(config_manager.config)
    logger = logging.getLogger('RTSP-Server')
    logger.info('RTSP 서버 시작 중...')
    
    # GStreamer 초기화
    Gst.init(None)
    
    # 서버 설정 로드
    server_config = config_manager.get_server_config()
    
    # API 클라이언트 초기화 및 CCTV 목록 가져오기
    api_client = APIClient(config_manager.config, logger)
    cctv_list = api_client.fetch_cctv_list()
    
    # 스트림 설정 준비
    if cctv_list:
        streams_config = config_manager.create_stream_config(cctv_list)
        logger.info('API에서 가져온 CCTV 정보로 스트림을 설정합니다.')
    else:
        streams_config = config_manager.get_streams_config()
        logger.info('config.json의 스트림 설정을 사용합니다.')
    
    # RTSP 서버 생성
    server = GstRtspServer.RTSPServer()
    
    # 서버 설정 최적화
    port = str(server_config.get('port', 8554))  # 포트를 문자열로 변환
    server.set_service(port)
    server.set_backlog(server_config.get('backlog', 10))  # 백로그 설정
    server.set_address(server_config.get('host', '0.0.0.0'))
    
    # 각 스트림에 대해 RTSPMediaFactory 생성
    for stream_name, stream_config in streams_config.items():
        # RTSPMediaFactory 생성 및 설정
        factory = RTSPMediaFactory(stream_config)
        
        # 마운트 포인트 추가
        output_path = stream_config.get('output_path', f'/{stream_name}')
        mounts = server.get_mount_points()
        mounts.add_factory(output_path, factory)
        logger.info(f'스트림 마운트 완료: {output_path} -> {stream_config["input_url"]}')
    
    # 서버 시작
    server.attach(None)
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8554)
    logger.info(f'RTSP 서버가 rtsp://{host}:{port} 에서 실행 중입니다.')
    print(f'RTSP 서버가 rtsp://{host}:{port} 에서 실행 중입니다.')
    
    try:
        loop = GLib.MainLoop()
        loop.run()
    except KeyboardInterrupt:
        logger.info('서버 종료 중...')
        print('서버 종료 중...')
        sys.exit(0)

if __name__ == '__main__':
    main() 