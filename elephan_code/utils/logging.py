from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional


import logging


class StructuredLogger:
    """简单的结构化 JSON logger，写入到文件（append JSON lines）。"""

    def __init__(self, path: Optional[str] = None):
        self.path = path
        if self.path:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # prepare an internal logger for fallback
        self._logger = logging.getLogger("elephan.structured")
        if not self._logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter('%(message)s'))
            self._logger.addHandler(h)

    def log(self, event: Dict[str, Any]):
        line = json.dumps(event, ensure_ascii=False)
        if self.path:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        else:
            # use structured internal logger to output
            self._logger.info(line)


def get_logger(name: str = __name__, level: int = logging.INFO, logfile: Optional[str] = None) -> logging.Logger:
    """Return a configured stdlib logger. If logfile is provided, add a FileHandler.

    Use `elephan_code.utils.logging.get_logger()` across the project to get consistent logging.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        fmt = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
        if logfile:
            fh = logging.FileHandler(logfile)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
    return logger
