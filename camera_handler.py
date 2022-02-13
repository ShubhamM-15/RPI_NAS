import numpy as np

from storage_handler import StorageHandler
import cv2
import logging
import time
logger = logging.getLogger(__name__)

class CameraHandler:
    def __init__(self, captureStream, config):
        self.stream = captureStream
        self.config = config
        self.resolution = config['resolution_wh']
        self.fps = config['fps']
        self.captureWait = 1/self.fps

        self.maxMisses = 20
        self.bufferSize = self.fps * 1

        self.storage = StorageHandler(config)

    def __setupCam(self, cam):
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        cam.set(cv2.CAP_PROP_XI_TIMEOUT, 1)

    def begin(self, debug=False):
        # This is major camera loop that captures and saves
        logger.info("Initiating camera open")
        cam = cv2.VideoCapture(self.stream)
        if cam is None or not cam.isOpened():
            logger.fatal(f"Unable to open camera at {self.stream}")
            return -1
        logger.info(f"Camera opened at {self.stream} running application")
        self.__setupCam(cam)

        # Prepare framebuffer
        ret, workFrame = cam.read()
        if ret:
            framebuffer = []
            for i in range(0, self.bufferSize):
                framebuffer.append(np.zeros(workFrame.shape, dtype=np.uint8))
        else:
            logger.error("Unable to capture frame from camera. exiting")
            return -1

        logger.info("Running loop for grab retrieve and dump...")
        errorCount = 0
        bufIndex = 0
        while True:
            atime = time.time()
            if errorCount > self.maxMisses:
                logger.fatal("Max Misses surpassed. exiting application")
                cv2.destroyAllWindows()
                return -1
            try:
                if cam.isOpened():
                    stime = time.time()
                    ret = cam.read(image=workFrame)
                    if ret:
                        errorCount = 0
                        np.copyto(framebuffer[bufIndex], workFrame)
                        bufIndex += 1
                        if bufIndex >= self.bufferSize:
                            logger.info("framebuffer overflow, dumping video now")
                            bufIndex = 0
                            # Signal storage to dump video here

                        if debug:
                            cv2.imshow("frames", workFrame)
                        cv2.waitKey(max(1, self.captureWait - (time.time()-stime)))
                    else:
                        errorCount += 1
                        logger.error("Camera closed while application was running")
                else:
                    errorCount += 1
                    logger.error("Camera closed while application was running")
            except Exception as e:
                errorCount += 1
                logger.error(f"Capturing failed: {e}")
            print(f"Time for one loop: {time.time()-atime}")