import io
import logging
from helpers.load_config import load_config

# Configure logging
config = load_config()
logging.basicConfig(level=logging.getLevelName(config.LOGGING_LEVEL), format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Set pika logging level to WARNING (otherwise it will log a lot of info messages)
logging.getLogger("pika").setLevel(logging.WARNING)

# todo: do we need this?
class TqdmToLogger(io.StringIO):
    """
        Output stream for TQDM which will output to logger module instead of
        the StdOut.
    """
    logger = None
    level = None
    buf = ''
    def __init__(self,logger,level=None):
        super(TqdmToLogger, self).__init__()
        self.logger = logger
        self.level = level or logging.INFO
    def write(self,buf):
        self.buf = buf.strip('\r\n\t ')
    def flush(self):
        self.logger.log(self.level, self.buf)