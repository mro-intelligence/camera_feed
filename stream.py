#!/usr/bin/env python3
"""Camera feed streaming - listen, stream, or serve web."""
import argparse, subprocess, sys, os

def run(cmd, **kw): subprocess.run(cmd, shell=isinstance(cmd, str), **kw)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["setup", "listen", "stream", "web", "all"])
    p.add_argument("-r", "--remote", help="Remote host for stream mode")
    p.add_argument("-l", "--local", help="Local IP for stream mode")
    p.add_argument("-p", "--port", default="5000")
    p.add_argument("-u", "--udp", action="store_true", help="Use UDP instead of TCP")
    p.add_argument("-w", "--web-port", default="8080")
    p.add_argument("-d", "--device", default="/dev/video2")
    a = p.parse_args()

    if a.mode == "setup":
        run("sudo modprobe v4l2loopback devices=1 video_nr=2 card_label='Virtual Camera' exclusive_caps=1")
    elif a.mode == "listen":
        proto = "udp" if a.udp else "tcp"
        listen_flag = "" if a.udp else "-listen 1"
        run(f"ffmpeg {listen_flag} -i {proto}://0.0.0.0:{a.port} -f v4l2 {a.device}")
    elif a.mode == "stream":
        if not a.remote or not a.local:
            sys.exit("stream mode requires --remote and --local")
        remote_script = "/var/tmp/remote_camera_script.sh"
        proto = "udp" if a.udp else "tcp"
        destination = f"{proto}://{a.local}:{a.port}"
        # Wrapper script that takes destination as $1 - matches start_ffmpeg.sh
        # Note: \" escapes quotes for the outer SSH double-quote context
        wrapper = r'''#!/bin/bash
osascript <<APPLESCRIPT
tell application \"iTerm\"
    create window with default profile command \"/opt/local/bin/ffmpeg -f avfoundation -pixel_format uyvy422 -framerate 30 -video_size 1280x720 -i '0' -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -f mpegts \$1\"
end tell
APPLESCRIPT'''
        # Write script to remote (using heredoc with single-quoted delimiter to prevent expansion)
        run(f"ssh {a.remote} \"cat > {remote_script} << 'WRAPPER_EOF'\n{wrapper}\nWRAPPER_EOF\nchmod +x {remote_script}\"")
        # Execute the script with destination argument
        run(f"ssh {a.remote} '{remote_script} {destination}'")
    elif a.mode == "web":
        run(f"uv run camera_feed_server.py --device {a.device} --port {a.web_port} --width 1280 --height 720")
    elif a.mode == "all":
        proto = "udp" if a.udp else "tcp"
        listen_flag = "" if a.udp else "-listen 1"
        proc = subprocess.Popen(f"ffmpeg {listen_flag} -i {proto}://0.0.0.0:{a.port} -f v4l2 {a.device}", shell=True)
        try:
            run(f"uv run camera_feed_server.py --device {a.device} --port {a.web_port} --width 1280 --height 720")
        finally:
            proc.terminate()

if __name__ == "__main__": main()
