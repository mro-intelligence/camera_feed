ffmpeg -f mpegts -i udp://@:12345 -f v4l2 -pix_fmt yuyv422 /dev/video10
