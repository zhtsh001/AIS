import logging
import os

def get_logger(name):
    """
    Standardized logger for AIS Engine.
    Errors go to logs/error.log, Info and above go to console.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Ensure logs directory exists
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # File Handler (Errors only)
        fh = logging.FileHandler(os.path.join(log_dir, 'error.log'), encoding='utf-8')
        fh.setLevel(logging.ERROR)
        
        # Console Handler (Info and above)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatting
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    return logger
