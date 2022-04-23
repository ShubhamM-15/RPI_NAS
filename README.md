# RPI_NAS
RSTP based NAS for Raspberry Pi

This application is to be used to store videos from IP cameras making RPI as DVR.

Hardware Requirements:
1) Tapo-C110
2) RPI3 b+ (or any future variant)

How to setup:
1) Setup tapo camera and setup its camera account with username and password
2) Setup RPI with raspbian and connect to same network as camera.
3) Install required dependencies in RPI using install_deps.sh file.
4) copy all the codes to a directory in RPI and configure config.json
5) Add this application to run at startup by adding run.sh to rc.local file.
6) create a folder for storing videos and add it to the config file.
7) restart RPI and then monitor debug_logs.txt for output.

config information:
1) rstp_string: rstp api for connecting with camera. Need to fill username and password from tapo account. Ip will be taken care of by application.
2) save_dir: absolute directory path of data-store.
3) save_format: video save format
4) video_codec: codec supported by opencv
5) camera_mac: MAC address of the camera that you are trying to link. This can be found in tapo application under camera settings.
6) max_storage_gb: Max storage space that this application can use.
7) clip_duration_minutes: Time duration of each clip from camera.
8) resolution_wh: Resolution of frames to be saved. keep it [-1, -1] for default from camera stream.
9) fps: FPS supported by camera. It will be auto-adjusted by application during runtime.
