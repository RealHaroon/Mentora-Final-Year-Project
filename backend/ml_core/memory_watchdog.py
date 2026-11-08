import logging

import psutil

logger = logging.getLogger("memory_watchdog")


def log_memory_snapshot(label: str):
    mem = psutil.virtual_memory()
    logger.info(f"[{label}] RAM used: {mem.percent}% ({mem.used / 1e9:.2f}GB / {mem.total / 1e9:.2f}GB)")
