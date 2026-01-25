#!/usr/bin/env python3
"""
Simple camera streaming server
Usage: python camera_server.py [--device DEVICE] [--port PORT]
"""

from flask import Flask, Response, render_template_string
import cv2
import argparse
import logging
import sys

app = Flask(__name__)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Global camera object
camera = None
DEVICE = 0
QUALITY = 50
WIDTH = 640
HEIGHT = 480
FPS_LIMIT = None
DEBUG = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Camera Stream</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: white;
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 {
            margin-bottom: 20px;
        }
        img {
            max-width: 100%;
            border: 2px solid #333;
            border-radius: 8px;
        }
        .info {
            margin-top: 10px;
            color: #888;
        }
    </style>
</head>
<body>
    <h1>Camera Feed</h1>
    <img src="{{ url_for('video_feed') }}" />
    <div class="info">Streaming from device: {{ device }}</div>
</body>
</html>
"""

def get_camera():
    """Initialize camera if not already done"""
    global camera
    if camera is None:
        logger.info(f"Initializing camera device: {DEVICE}")
        camera = cv2.VideoCapture(DEVICE)
        
        if not camera.isOpened():
            logger.error(f"Failed to open camera device: {DEVICE}")
            raise RuntimeError(f"Could not open camera device {DEVICE}")
        
        # Set buffer size to 1 to reduce latency
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Log camera properties
        actual_width = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = camera.get(cv2.CAP_PROP_FPS)
        backend = camera.getBackendName()
        
        logger.info(f"Camera opened successfully")
        logger.info(f"Backend: {backend}")
        logger.info(f"Native resolution: {int(actual_width)}x{int(actual_height)}")
        logger.info(f"Native FPS: {actual_fps}")
        logger.info(f"Output resolution: {WIDTH}x{HEIGHT}")
        logger.info(f"JPEG quality: {QUALITY}")
        if FPS_LIMIT:
            logger.info(f"FPS limit: {FPS_LIMIT}")
        
    return camera

def generate_frames():
    """Generator function to yield camera frames"""
    import time
    cam = get_camera()
    last_frame_time = 0
    frame_count = 0
    start_time = time.time()
    last_log_time = start_time
    
    logger.info("Starting frame generation")
    
    while True:
        # Limit FPS if specified
        if FPS_LIMIT:
            current_time = time.time()
            time_since_last = current_time - last_frame_time
            min_frame_time = 1.0 / FPS_LIMIT
            if time_since_last < min_frame_time:
                time.sleep(min_frame_time - time_since_last)
            last_frame_time = time.time()
        
        success, frame = cam.read()
        if not success:
            logger.error("Failed to read frame from camera")
            break
        
        frame_count += 1
        
        # Log stats every 5 seconds in debug mode
        if DEBUG:
            current_time = time.time()
            if current_time - last_log_time >= 5.0:
                elapsed = current_time - start_time
                fps = frame_count / elapsed
                logger.debug(f"Stats: {frame_count} frames, {fps:.2f} FPS average")
                last_log_time = current_time
        
        # Reduce resolution to save bandwidth
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        
        # Encode frame as JPEG with adjustable quality
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
        if not ret:
            logger.error("Failed to encode frame as JPEG")
            continue
        
        frame_bytes = buffer.tobytes()
        
        if DEBUG and frame_count == 1:
            logger.debug(f"First frame size: {len(frame_bytes)} bytes")
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    """Main page with video feed"""
    logger.info("Index page requested")
    return render_template_string(HTML_TEMPLATE, device=DEVICE)

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    logger.info("Video feed requested")
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'device': DEVICE}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple camera streaming server')
    parser.add_argument('--device', type=str, default='0', 
                        help='Camera device (number or path like /dev/video10)')
    parser.add_argument('--list-devices', action='store_true',
                        help='List available camera devices and exit')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to run server on')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind to (0.0.0.0 for all interfaces)')
    parser.add_argument('--quality', type=int, default=50,
                        help='JPEG quality (1-100, lower=smaller file)')
    parser.add_argument('--width', type=int, default=640,
                        help='Frame width in pixels')
    parser.add_argument('--height', type=int, default=480,
                        help='Frame height in pixels')
    parser.add_argument('--fps', type=int, default=None,
                        help='Limit FPS (e.g., 15 for lower bandwidth)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        DEBUG = True
        logger.debug("Debug logging enabled")
    
    # List devices if requested
    if args.list_devices:
        logger.info("Scanning for camera devices...")
        found_devices = []
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                backend = cap.getBackendName()
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.info(f"Device {i}: {backend} - {int(width)}x{int(height)}")
                found_devices.append(i)
                cap.release()
        
        # Also check common device paths on Linux
        import os
        if os.path.exists('/dev'):
            for i in range(20):
                dev_path = f'/dev/video{i}'
                if os.path.exists(dev_path):
                    if i not in found_devices:
                        logger.info(f"Found device path: {dev_path}")
        
        sys.exit(0)
    
    # Handle device argument (could be number or path)
    try:
        DEVICE = int(args.device)
    except ValueError:
        DEVICE = args.device
    
    QUALITY = args.quality
    WIDTH = args.width
    HEIGHT = args.height
    FPS_LIMIT = args.fps
    
    logger.info("="*60)
    logger.info("Starting camera streaming server")
    logger.info("="*60)
    logger.info(f"Device: {DEVICE}")
    logger.info(f"Resolution: {WIDTH}x{HEIGHT}")
    logger.info(f"JPEG Quality: {QUALITY}")
    if FPS_LIMIT:
        logger.info(f"FPS Limit: {FPS_LIMIT}")
    logger.info(f"Host: {args.host}:{args.port}")
    logger.info(f"URL: http://localhost:{args.port}")
    logger.info("="*60)
    
    try:
        app.run(host=args.host, port=args.port, threaded=True, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if camera is not None:
            logger.info("Releasing camera")
            camera.release()