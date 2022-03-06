import logging
import cv2
import os
import numpy as np
import time
from datetime import datetime
import shutil
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import gc

logger = logging.getLogger(__name__)

class StorageHandler:
    def __init__(self, config, frame: np.ndarray):
        logger.info("Initializing Storage Handler")
        self.storePath = config['save_dir']
        self.maxStorage = float(config['max_storage_gb']) * 1024
        self.videoFormat = config['save_format']
        self.exportDuration = int(config['clip_duration_minutes']) * 60
        self.fps = config['fps']
        self.videoCodec = config['video_codec']
        self.storeMetaData = Queue(maxsize=-1)
        self.frameCounter = 0
        self.maxMisses = 10
        self.filePurgeBatch = 10
        self.clipStartTime = time.time()
        self.frameShape = frame.shape[:2][::-1]
        self.frameCH = frame.shape[2]
        self.frameSize = frame.nbytes / (1024*1024)
        self.forceExport = False
        self.cvExport = None
        self.videoPath = ""

        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='export_handler')
        self.q = Queue(maxsize=2)

        os.makedirs(self.storePath, exist_ok=True)
        self.isReady = self.__checkStorage()
        self.isReady = self.isReady and self.__prepareStoreMetaData()
        if self.isReady:
            self.executor.submit(self.__exportHandler)
            logger.info("Storage Handler launched and ready")
        else:
            logger.error("Storage Handler failed to initialize")

    def __exportHandler(self):
        # This is a never ending Daemon worker
        logger.info("export_handler: executor thread export_handler launched")
        self.executor.submit(self.__handleStorage)
        if self.cvExport is None:
            self.frameCounter = 0
            self.clipStartTime = time.time()
            dname, fname = self.__getFileName()
            os.makedirs(os.path.join(self.storePath, dname), exist_ok=True)
            self.videoPath = os.path.join(self.storePath, dname, fname)
            self.cvExport = cv2.VideoWriter(self.videoPath, cv2.VideoWriter_fourcc(*self.videoCodec),
                                            self.fps, self.frameShape)
            # Update meta data
            self.storeMetaData.put(self.videoPath)

        logger.info("Storage handler loop running...")
        errorCount = 0
        while True:
            try:
                frame = self.q.get(block=True, timeout=1)
            except:
                errorCount += 1
                logger.info("export_handler: dequeue frame timed out")
                frame = None
            if self.forceExport:
                logger.info("export_handler: export_handler forced to dump")
                if frame is not None:
                    self.cvExport.write(frame)
                self.cvExport.release()
                logger.info(f"export_handler: video: {self.videoPath} saved successfully")
                logger.info("export_handler: forced-dump done, terminating thread.")
                return True
            elif frame is not None:
                errorCount = 0
                cspan = time.time() - self.clipStartTime
                if cspan >= self.exportDuration:
                    self.executor.submit(self.__handleStorage)
                    logger.info(f"export_handler: Executing save video with {self.frameCounter} frames at {self.fps} fps")
                    self.fps = self.frameCounter / cspan
                    self.cvExport.write(frame)
                    self.cvExport.release()
                    logger.info(f"export_handler: video: {self.videoPath} saved successfully")
                    self.frameCounter = 0
                    self.clipStartTime = time.time()
                    dname, fname = self.__getFileName()
                    self.videoPath = os.path.join(self.storePath, dname, fname)
                    self.cvExport = cv2.VideoWriter(self.videoPath, cv2.VideoWriter_fourcc(*self.videoCodec),
                                                    self.fps, self.frameShape)
                    # Update meta data
                    self.storeMetaData.put(self.videoPath)
                else:
                    self.cvExport.write(frame)
                    self.frameCounter += 1
                del frame
                gc.collect()
            if errorCount >= self.maxMisses:
                if not self.forceExport:
                    self.forceExport = True
                else:
                    logger.fatal("Max error count surpassed in storage handler. Exiting.")
                    return False

    def __checkStorage(self):
        # To check if program has write permissions
        t = np.zeros(self.frameShape, dtype=np.uint8)
        np.save(os.path.join(self.storePath, 'test.npy'), t)
        if os.path.isfile(os.path.join(self.storePath, 'test.npy')):
            os.remove(os.path.join(self.storePath, 'test.npy'))
            return True
        else:
            return False

    def __getFileName(self):
        fName = datetime.today().strftime('%H_%M_%S')
        dName = datetime.today().strftime('%d_%m_%y')
        fName = fName + self.videoFormat
        return dName, fName

    def __prepareStoreMetaData(self):
        try:
            # list date folders
            dates = []
            for it in os.scandir(self.storePath):
                if it.is_dir():
                    date = os.path.split(it.path)[-1]
                    if date != 'dump':
                        dates.append(date)
            dates.sort(key=lambda date: datetime.strptime(date, '%d_%m_%y'))

            # list time files
            for date in dates:
                files = []
                for it in os.scandir(os.path.join(self.storePath, date)):
                    if it.is_file():
                        files.append(os.path.split(it.path)[-1])
                files.sort(key=lambda file: datetime.strptime(file.split('.')[0], '%H_%M_%S'))

                # Adding to datamap queue
                for file in files:
                    self.storeMetaData.put(os.path.join(self.storePath, date, file))
            logger.info("Storage mapped successfully")
            return True
        except:
            logger.error("Error in mapping data storage. Please format.")
            return False

    def __findStoreSize(self):
        size = 0
        # get size
        for path, dirs, files in os.walk(self.storePath):
            for f in files:
                fp = os.path.join(path, f)
                size += os.path.getsize(fp)
        sizeMB = (size / 1024) / 1024
        logger.info(f"Total size of used storage: {sizeMB} MB")
        return sizeMB

    def __handleStorage(self):
        used = self.__findStoreSize()
        retries = 0
        while used >= self.maxStorage:
            # delete last 10 files
            for _ in range(self.filePurgeBatch):
                try:
                    path = self.storeMetaData.get(block=False)
                    os.remove(path)
                    logger.info(f"Deleted file: {path}")
                except:
                    pass
            used = self.__findStoreSize()
            retries += 1
            if retries >= self.filePurgeBatch:
                logger.fatal("Max retries surpassed for handling storage. Storage might overflow.")
                return False
        return True

    def updateFrame(self, frame: np.ndarray):
        try:
            self.q.put(frame, block=True, timeout=1)
        except:
            logger.error(f"Unable to enqueue frame for exporting, Queue Full: {self.q.full()}")
            return False
        return True

    def forceDump(self):
        logger.info("Force dump initiated")
        if not self.forceExport:
            self.forceExport = True
            self.frameCounter = 0
            self.clipStartTime = time.time()
            self.executor.shutdown(wait=True)
        logging.info("All standing exports done. Exiting storage handler.")
