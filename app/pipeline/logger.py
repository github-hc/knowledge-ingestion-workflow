import logging
import os

LOG_FILE = "/Users/harshitchoudhary/Tech2go/PdfRAG/knowledge-process-workflow/knowledge-ingestion-workflow/pipeline.log"

def get_pipeline_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(LOG_FILE, mode="a")
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger
