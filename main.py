import json
import os
import logging.config
from utils.find_devices import DeviceFinder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(filename)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    # Reading Config
    configPath = os.path.join(os.path.dirname(__file__), 'utils/config.json')
    with open(configPath, "r") as fp:
        config = json.load(fp)
        fp.close()
    if config is None:
        logger.error("Failed to read config.json")
        return -1

    deviceHandler = DeviceFinder()
    ip = deviceHandler.getIPofDevice(config['camera_mac'])
    if ip is None:
        logger.error(f"Unable to find ip of device with mac {config['camera_mac']}")
        return -1

    stream = config['rstp_string'].format(ip=ip)
    logger.info(f"Setting camera stream {stream}")

if __name__ == "__main__":
    main()