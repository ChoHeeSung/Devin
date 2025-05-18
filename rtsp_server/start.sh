#!/bin/bash

export CONFIG_PATH="./config.json"

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Running on macOS, setting up GStreamer environment"
    export PATH="/Library/Frameworks/GStreamer.framework/Versions/1.0/bin:$PATH"
    export PKG_CONFIG_PATH="/Library/Frameworks/GStreamer.framework/Versions/1.0/lib/pkgconfig"
    export DYLD_LIBRARY_PATH="/Library/Frameworks/GStreamer.framework/Versions/1.0/lib"
    export GST_PLUGIN_PATH="/Library/Frameworks/GStreamer.framework/Versions/1.0/lib/gstreamer-1.0"
    export PYTHONPATH="/Library/Frameworks/GStreamer.framework/Versions/1.0/lib/python3/site-packages:$PYTHONPATH"
    
    if ! which gst-launch-1.0 > /dev/null; then
        echo "Warning: GStreamer command-line tools not found. Make sure GStreamer is installed properly."
        echo "Download from: https://gstreamer.freedesktop.org/download/#macos"
    fi
    
    pip install -r requirements.txt
    
    python3 -v main.py
else
    echo "Running on Linux"
    pip install -r requirements.txt
    
    python3 main.py
fi
