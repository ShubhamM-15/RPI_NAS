#!/bin/sh
while true
do
echo "Starting python script main.py"
# paste absolute path of python file main.py
sudo python3 /home/pi/RPI_NAS/main.py
echo "Entire process crashed. Restarting through shell"
sleep 2
done
