# Camera Feed Streaming

Stream camera feed from a remote Mac to local machine and view in web browser.

## Setup

1. **Install dependencies** (local machine):
```bash
sudo apt install v4l2loopback-dkms v4l2loopback-utils
pip3 install flask opencv-python
```

2. **Setup virtual camera** (run once):
```bash
./start_stream.sh setup
```

3. **Grant camera permissions** (remote Mac):
   - Run the stream command once, it will open iTerm
   - Go to System Settings → Privacy & Security → Camera
   - Enable camera access for iTerm

## Quick Start

**Option 1: Automatic (easiest)**
```bash
# Terminal 1 (local): Start receiver + web server
./start_stream.sh all

# Terminal 2 (local): Start remote camera stream
./start_stream.sh stream

# Open browser to http://localhost:8080
```

**Option 2: Manual control**
```bash
# Terminal 1: Receive stream and write to virtual camera
./start_stream.sh receiver

# Terminal 2: Stream from remote Mac camera
./start_stream.sh stream

# Terminal 3: Start web server
./start_stream.sh web
```

## Configuration

Set environment variables to customize:
```bash
export REMOTE_HOST=<remote-ip>   # Remote Mac IP address
export LOCAL_HOST=<local-ip>     # Local machine IP address
export PORT=5000                  # Streaming port (optional, default: 5000)
export WEB_PORT=8080              # Web server port (optional, default: 8080)

./start_stream.sh all
```

Examples:
```bash
# Using IP addresses
export REMOTE_HOST=user@192.168.1.10
export LOCAL_HOST=192.168.1.20
./start_stream.sh stream

# Using hostnames (e.g., SSH config hostname)
export REMOTE_HOST=remote-host
export LOCAL_HOST=192.168.1.20
./start_stream.sh stream

# One-liner
REMOTE_HOST=user@192.168.1.10 LOCAL_HOST=192.168.1.20 ./start_stream.sh stream
```

## Architecture

```
Remote Mac                      Local Linux
┌──────────────────┐           ┌─────────────────────┐
│  Camera          │           │ ffmpeg receiver     │
│     ↓            │           │        ↓            │
│  iTerm + ffmpeg  │  TCP/UDP  │  /dev/video2        │
│  (H.264 encode)  │  -----→   │  (virtual camera)   │
└──────────────────┘           │        ↓            │
                               │  camera_feed_server │
                               │        ↓            │
                               │  http://localhost   │
                               └─────────────────────┘
```

## Troubleshooting

**Camera not working on remote Mac:**
- Make sure iTerm has camera permissions in System Settings
- Try running the ffmpeg command directly in iTerm on remote Mac first

**No video in browser:**
- Check that `/dev/video2` exists: `ls -la /dev/video2`
- Check receiver logs: `tail -f /tmp/receiver.log`
- List available cameras: `python3 camera_feed_server.py --list-devices`

**Virtual camera not found:**
- Run setup again: `./start_stream.sh setup`
- Check module is loaded: `lsmod | grep v4l2loopback`
- Manual load: `sudo modprobe v4l2loopback devices=1 video_nr=2 card_label="Virtual Camera" exclusive_caps=1`

## Files

- `start_ffmpeg.sh` - Low-level ffmpeg streaming script
- `start_stream.sh` - High-level convenience wrapper
- `camera_feed_server.py` - Web server for viewing the feed
