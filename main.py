import json
import os
import logging.config
from logging.handlers import RotatingFileHandler
from utils.find_devices import DeviceFinder
from camera_handler import CameraHandler
import time
import sys

file_handler = RotatingFileHandler(filename='debug_logs.log', mode='a', maxBytes=5 * 1024 * 1024, backupCount=2, encoding=None, delay=0)
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger('LOGGER_NAME')

def main():
    # Reading Config
    configPath = os.path.join(os.path.dirname(__file__), 'utils/config.json')
    with open(configPath, "r") as fp:
        config = json.load(fp)
        fp.close()
    if config is None:
        logger.error("Failed to read config.json")
        return -1

    while True:
        logger.info("Starting Application")
        # Finding ip of camera to prepare its stream string
        deviceHandler = DeviceFinder()
        ip = deviceHandler.getIPofDevice(config['camera_mac'])
        if ip is None:
            logger.error(f"Unable to find ip of device with mac {config['camera_mac']}")
            logging.info('Waiting for 10 seconds to restart')
            time.sleep(10)
            continue
        stream = config['rstp_string'].format(ip=ip)
        logger.info(f"Setting camera stream {stream}")

        # Launching camera handler
        camHandle = CameraHandler(stream, config)
        camHandle.begin()
        logger.error("Camera application crashed. Restarting")


if __name__ == "__main__":
    main()