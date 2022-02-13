import logging
logger = logging.getLogger(__name__)


class StorageHandler:
    def __init__(self, config):
        self.config = config
