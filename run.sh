#!/bin/sh
# paste absolute path of python file main.py
retry=0
while true
do
	echo "Starting python script main.py"
	sudo python3 /home/pi/RPI_NAS/main.py
	echo "Entire process crashed. Restarting through shell. Retry Count: $retry"
	sleep 10
	retry=$((retry+1))
	if [ "$retry" -eq "10" ];
	then
		echo "Max retries surpassed. Restarting in 60 seconds"
		sleep 60
		sudo reboot
	fi
done
