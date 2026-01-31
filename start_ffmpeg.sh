#!/bin/bash
# Camera feed streaming script
# Run on local machine to either:
#   1. Start a receiver (listen mode)
#   2. SSH to remote and start camera streaming to local

# Defaults
remote_ffmpeg="/opt/local/bin/ffmpeg"
remote_script="~/remote_camera_script.sh"  # Wrapper script with camera permissions
port=5000
proto=tcp

usage() {
  cat <<-EOT
Usage: $0 -m <mode> [options]

Modes:
  -m listen                Start local receiver (listens for incoming stream)
  -m stream -r <remote> -l <local>   SSH to remote and start camera stream to local

Options:
  -r <remote>             Remote host to SSH into (required for stream mode)
  -l <local>              Local host IP to stream to (required for stream mode)
  -p <port>               Port number (default: 5000)
  -P <proto>              Protocol tcp or udp (default: tcp)

Examples:
  $0 -m listen
  $0 -m stream -r pi@192.168.1.100 -l 192.168.1.50
  $0 -m stream -r pi@192.168.1.100 -l 192.168.1.50 -P udp -p 6000
EOT
  exit 1
}

# Parse arguments
while getopts "m:r:l:p:P:" opt; do
  case $opt in
    m) mode=$OPTARG ;;
    r) remote=$OPTARG ;;
    l) local=$OPTARG ;;
    p) port=$OPTARG ;;
    P) proto=$OPTARG ;;
    *) usage ;;
  esac
done

# Validate mode
if [[ -z "$mode" ]]; then
  echo "Error: Mode (-m) is required"
  usage
fi

if [[ "$mode" == "listen" ]]; then
  echo "Starting local receiver on $proto://0.0.0.0:$port"

  input_source="$proto://0.0.0.0:$port"  # Network stream input

  # TCP needs -listen 1 flag to act as server waiting for connections
  if [[ "$proto" == "tcp" ]]; then
    listen_flag="-listen 1"
  else
    listen_flag=""
  fi

  output_format="-f null -"  # Null output for testing (discards frames)

  echo "Running: ffmpeg $listen_flag -i $input_source -f v4l2 /dev/video2"
  ffmpeg $listen_flag -i $input_source -f v4l2 /dev/video2

  # Alternative: discard frames for testing (uncomment to use)
  #ffmpeg $listen_flag -i $input_source $output_format

elif [[ "$mode" == "stream" ]]; then
  # Stream mode - SSH to remote and capture camera
  if [[ -z "$remote" ]] || [[ -z "$local" ]]; then
    echo "Error: Stream mode requires both -r (remote) and -l (local) arguments"
    usage
  fi

  echo "Starting camera stream from $remote to $local on port $port using $proto"

  # === INPUT OPTIONS ===
  input_format="avfoundation"  # AVFoundation (macOS camera framework)
  pixel_format="uyvy422"       # Pixel format for input capture
  framerate="30"               # Frames per second
  video_size="1280x720"        # Video resolution (width x height)
  input_device="0"             # Input device ("0" is default camera)

  # === ENCODING OPTIONS ===
  video_codec="libx264"        # H.264 codec for compression
  encoder_preset="ultrafast"   # Prioritizes speed over compression
  tune_option="zerolatency"    # Optimizes for live streaming
  output_pixfmt="yuv420p"      # Pixel format for compatibility

  # === OUTPUT OPTIONS ===
  output_format="mpegts"                 # MPEG-TS format for streaming
  destination="$proto://$local:$port"    # Destination protocol://host:port

  # Create simple wrapper script that launches iTerm with ffmpeg
  echo "Creating wrapper script on remote..."
  ssh $remote "cat > $remote_script << 'WRAPPER_EOF'
#!/bin/bash
# Launch ffmpeg in iTerm which has camera access
osascript <<APPLESCRIPT
tell application \"iTerm\"
    create window with default profile command \"$remote_ffmpeg -f $input_format -pixel_format $pixel_format -framerate $framerate -video_size $video_size -i '$input_device' -c:v $video_codec -preset $encoder_preset -tune $tune_option -pix_fmt $output_pixfmt -f $output_format \$1\"
end tell
APPLESCRIPT
WRAPPER_EOF
chmod +x $remote_script"

  # Execute camera script on remote machine
  echo "Running: ssh $remote $remote_script $destination"
  echo ""
  ssh $remote $remote_script $destination

else
  echo "Error: Invalid mode '$mode'. Must be 'listen' or 'stream'"
  usage
fi