#!/bin/bash
# Complete camera streaming setup
# This script starts both the receiver and web server

set -e

# Configuration
REMOTE_HOST="${REMOTE_HOST:-}"
LOCAL_HOST="${LOCAL_HOST:-}"
PORT="${PORT:-5000}"
WEB_PORT="${WEB_PORT:-8080}"
VIRTUAL_DEVICE="${VIRTUAL_DEVICE:-/dev/video2}"

usage() {
  cat <<-EOT
Usage: $0 [mode]

Modes:
  setup       Setup virtual camera device (run once, requires sudo)
  receiver    Start ffmpeg receiver (writes to virtual camera)
  stream      Start camera stream from remote
  web         Start web server to view the feed
  all         Start receiver and web server (in background)

Environment variables:
  REMOTE_HOST    Remote host to stream from (required for 'stream' mode)
  LOCAL_HOST     Local host IP (required for 'stream' mode)
  PORT           Streaming port (default: 5000)
  WEB_PORT       Web server port (default: 8080)

Examples:
  # Setup (run once)
  $0 setup

  # Start receiver and web server
  $0 all

  # With custom settings
  REMOTE_HOST=user@192.168.1.10 LOCAL_HOST=192.168.1.20 $0 stream
  VIRTUAL_DEVICE=/dev/video10 $0 receiver

  # Or start manually in separate terminals:
  $0 receiver    # Terminal 1
  $0 stream      # Terminal 2
  $0 web         # Terminal 3
EOT
  exit 1
}

case "${1:-}" in
  setup)
    echo "Setting up virtual camera..."
    if ! lsmod | grep -q v4l2loopback; then
      echo "Loading v4l2loopback kernel module..."
      sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="Virtual Camera" exclusive_caps=1
    else
      echo "v4l2loopback already loaded"
    fi
    echo "Virtual camera devices:"
    v4l2-ctl --list-devices | grep -A 1 "Virtual Camera" || echo "Note: Virtual camera may be at $VIRTUAL_DEVICE"
    ls -la $VIRTUAL_DEVICE 2>/dev/null || echo "Warning: $VIRTUAL_DEVICE not found"
    ;;

  receiver)
    echo "Starting receiver on $LOCAL_HOST:$PORT -> $VIRTUAL_DEVICE"
    ./start_ffmpeg.sh -m listen -p $PORT -d $VIRTUAL_DEVICE
    ;;

  stream)
    if [[ -z "$REMOTE_HOST" ]] || [[ -z "$LOCAL_HOST" ]]; then
      echo "Error: REMOTE_HOST and LOCAL_HOST environment variables are required for stream mode"
      echo "Example: REMOTE_HOST=192.168.1.10 LOCAL_HOST=192.168.1.20 $0 stream"
      exit 1
    fi
    echo "Starting stream from $REMOTE_HOST to $LOCAL_HOST:$PORT"
    ./start_ffmpeg.sh -m stream -r $REMOTE_HOST -l $LOCAL_HOST -p $PORT
    ;;

  web)
    echo "Starting web server on port $WEB_PORT for device $VIRTUAL_DEVICE"
    echo "Open http://localhost:$WEB_PORT in your browser"
    python3 camera_feed_server.py --device $VIRTUAL_DEVICE --port $WEB_PORT --width 1280 --height 720
    ;;

  all)
    echo "Starting receiver and web server in background..."

    # Start receiver in background
    echo "Starting receiver..."
    ./start_ffmpeg.sh -m listen -p $PORT -d $VIRTUAL_DEVICE > /tmp/receiver.log 2>&1 &
    RECEIVER_PID=$!
    echo "Receiver started (PID: $RECEIVER_PID, log: /tmp/receiver.log)"

    # Wait a bit for receiver to start
    sleep 2

    # Start web server
    echo "Starting web server on http://localhost:$WEB_PORT"
    uv run camera_feed_server.py --device $VIRTUAL_DEVICE --port $WEB_PORT --width 1280 --height 720

    # Cleanup on exit
    trap "echo 'Stopping receiver...'; kill $RECEIVER_PID 2>/dev/null" EXIT
    ;;

  *)
    usage
    ;;
esac
