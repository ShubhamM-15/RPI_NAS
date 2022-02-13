import numpy as np

from storage_handler import StorageHandler
import cv2
import logging
import time
logger = logging.getLogger(__name__)

class CameraHandler:
    def __init__(self, captureStream, config, debug=False):
        self.stream = captureStream
        self.config = config
        self.resolution = config['resolution_wh']
        self.fps = config['fps']
        self.captureWait = 1/self.fps
        self.debug = debug

        self.maxMisses = 20
        self.bufferSize = self.fps * 1

        self.storage = StorageHandler(config)

    def __setupCam(self, cam):
        # TODO populate this for efficiency
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 3)

    def begin(self):
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
        ttime = 0
        while True:
            try:
                if cam.isOpened():
                    stime = time.time()
                    ret = cam.read(image=workFrame)
                    if ret:
                        errorCount = 0
                        np.copyto(framebuffer[bufIndex], workFrame)
                        bufIndex += 1
                        ttime += time.time()-stime
                        if bufIndex >= self.bufferSize:
                            logger.info("framebuffer overflow, dumping video now")
                            logger.info(f"Effective fps: {self.bufferSize/ttime}")
                            bufIndex = 0
                            ttime = 0
                            # TODO Signal storage to dump video here by dispatcher

                        if self.debug:
                            cv2.imshow("Frames", workFrame)
                            cv2.waitKey(1)
                        time.sleep(max(0.001, self.captureWait - (time.time()-stime)))
                    else:
                        errorCount += 1
                        logger.error("Camera closed while application was running")
                else:
                    errorCount += 1
                    logger.error("Camera closed while application was running")
            except Exception as e:
                errorCount += 1
                logger.error(f"Capturing failed: {e}")
            if errorCount > self.maxMisses:
                logger.fatal("Max Misses surpassed. exiting application")
                cv2.destroyAllWindows()
                # TODO dump video if bufIndex != 0 in case of camera fatality
                return -1