# RTSP to RTSP Server

A Python-based RTSP to RTSP server using GStreamer with on-demand streaming functionality, API integration, and low-latency optimization.

## Features

- On-demand streaming
- API-driven camera information retrieval with fallback to config file
- Low-latency streaming optimization
- Multiple client support with shared source streams
- Docker environment for production deployment
- Cross-platform support (Linux and macOS)

## Installation

### Linux

```bash
# Install dependencies
sudo apt-get update && sudo apt-get install -y \
    python3-gi \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-rtsp \
    libgstrtspserver-1.0-dev

# Install Python dependencies
pip install -r requirements.txt
```

### macOS

1. Install GStreamer framework from the official website:
   - Download and install the runtime package: `gstreamer-1.0-{VERSION}-x86_64.pkg`
   - Download and install the development package: `gstreamer-1.0-devel-{VERSION}-x86_64.pkg`
   - Download link: https://gstreamer.freedesktop.org/download/#macos

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

### Local Testing

```bash
# Make the start script executable
chmod +x start.sh

# Run the server
./start.sh
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

## Configuration

The server is configured via the `config.json` file. Key configuration options:

- `server.server_rtsp_port`: RTSP server port (default: `:8554`)
- `stream_defaults.on_demand`: Enable on-demand streaming (default: `true`)
- `stream_defaults.disable_audio`: Disable audio streaming (default: `true`)
- `api.cctv_master_url`: URL for retrieving camera information
- `api.retry_interval`: Retry interval for API calls in seconds
- `api.timeout`: API call timeout in seconds
- `streams`: Fallback stream definitions used when API calls fail

## Accessing Streams

After starting the server, streams can be accessed at:

```
rtsp://localhost:8554/{stream_name}
```

For example:
```
rtsp://localhost:8554/금곡IC
```

## Testing with GStreamer

You can test the streams using GStreamer:

### For H.264 streams (when source streams are accessible):

```bash
gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/금곡IC protocols=tcp ! application/x-rtp,media=video ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

### For H.264 test pattern streams (when source streams are not accessible):

```bash
gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/금곡IC protocols=tcp ! application/x-rtp,encoding-name=H264 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

### Simple playbin (may not work in all environments):

```bash
gst-launch-1.0 playbin uri=rtsp://localhost:8554/금곡IC
```

### Using VLC Media Player:

VLC can directly play the RTSP stream:
1. Open VLC Media Player
2. Select Media > Open Network Stream
3. Enter the URL: `rtsp://localhost:8554/금곡IC`
4. For best results, increase the network caching to 300-500ms in VLC preferences
5. Click Play

## Troubleshooting

### macOS

- Make sure GStreamer framework is installed at `/Library/Frameworks/GStreamer.framework/`
- Check if GStreamer tools are in your PATH: `which gst-launch-1.0`
- If using Python virtual environment, make sure it has access to the GStreamer Python bindings
- If you encounter segmentation faults, ensure that the environment variables are set correctly in the start.sh script

### Linux

- Verify GStreamer packages are installed: `dpkg -l | grep gstreamer`
- Check if GStreamer Python bindings are available: `python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None)"`

### Docker Environment

- If you encounter "SDP contains no streams" error when connecting to the RTSP server:
  - Check if the source RTSP streams are accessible from the Docker container
  - Try using `docker-compose down && docker-compose up -d` to restart the container
  - The server will automatically use a test pattern if the source streams are not accessible
  - You can modify the timeout settings in the `rtsp_server.py` file

- If you need to access the Docker container for debugging:
  - Run `docker-compose exec rtsp-server bash` to get a shell in the container
  - Use `gst-launch-1.0` to test RTSP connectivity from within the container

- Make sure your Docker network allows connections to the source RTSP streams
