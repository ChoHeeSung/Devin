FROM ubuntu:22.04

# Set non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    python3-gst-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-rtsp \
    gstreamer1.0-libav \
    gstreamer1.0-x264 \
    libgstrtspserver-1.0-dev \
    meson \
    ninja-build \
    build-essential \
    pkg-config \
    libcairo2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy application files
COPY . /app/

# Update requirements.txt to use system packages for GStreamer bindings
RUN sed -i 's/PyGObject==3.44.1//' requirements.txt

# Install Python requirements
RUN pip3 install -r requirements.txt

# Expose RTSP port
EXPOSE 8554

# Run the RTSP server
CMD ["python3", "main.py"]
