# RPI_NAS
RSTP based NAS for Raspberry Pi

This application is to be used to store videos from IP cameras making RPI as DVR.

Hardware Requirements:
1) Tapo-C110
2) RPI3 b+ (or any future variant)

How to setup:
1) Setup tapo camera and setup its camera account with username and password
2) Setup RPI with raspbian and connect to same network as camera.
3) copy all the codes to a directory in RPI and configure config.txt
4) Add this application to run at startup by adding run.sh to rc.local file.
5) create a folder for storing videos and add it to the config file.
6) restart RPI and then monitor debug_logs.txt for output.

