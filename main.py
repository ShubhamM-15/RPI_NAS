import json
import os
import logging.config
from logging.handlers import RotatingFileHandler
from utils.find_devices import DeviceFinder
from camera_handler import CameraHandler
import time
import sys

logPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_logs.log")
file_handler = RotatingFileHandler(logPath, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2, encoding=None, delay=0)
stdout_handler = logging.StreamHandler(sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger('LOGGER_NAME')

def main():
    '''
    Its infinite loop should be handled by the shell script calling this python script
    :return: It only returns if application has crashed.
    '''
    # Reading Config
    configPath = os.path.join(os.path.dirname(__file__), 'utils/config.json')
    with open(configPath, "r") as fp:
        config = json.load(fp)
        fp.close()
    if config is None:
        logger.error("Failed to read config.json")
        return -1

    logger.info("Starting Application")
    # Finding ip of camera to prepare its stream string
    deviceHandler = DeviceFinder()
    ip = deviceHandler.getIPofDevice(config['camera_mac'])
    if ip is None:
        logger.fatal(f"Unable to find ip of device with mac {config['camera_mac']}")
        logger.fatal("Exiting Python Application")
        return -1
    stream = config['rstp_string'].format(ip=ip)
    logger.info(f"Setting camera stream {stream}")

    # Launching camera handler
    camHandle = CameraHandler(stream, config)
    camHandle.begin()
    logger.error("Camera application crashed. Restarting")
    return -1

if __name__ == "__main__":
    main()