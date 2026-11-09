import ctypes
import gc
import logging
import platform

import psutil

logger = logging.getLogger("memory_watchdog")


def log_memory_snapshot(label: str):
    mem = psutil.virtual_memory()
    logger.info(f"[{label}] RAM used: {mem.percent}% ({mem.used / 1e9:.2f}GB / {mem.total / 1e9:.2f}GB)")


def release_freed_memory():
    """
    Found via Phase 8's RAM measurement: after model.unload() drops the last
    Python reference to a model's tensors, process RSS barely moves even
    with gc.collect() (measured: 921MB loaded -> 718MB after unload+gc.collect()
    for M1 alone, nowhere near the ~287MB pre-load baseline). That gap isn't
    a GC-timing issue — it's glibc's malloc holding onto freed arenas rather
    than returning them to the OS. Calling malloc_trim(0) after gc.collect()
    recovers most of the rest (measured: 718MB -> 452MB for the same case) —
    this is the actual mechanism the idle-unload design needs to deliver on
    its "RAM drops back near idle" premise, not just gc.collect() alone.
    Linux-only (glibc); a no-op elsewhere.
    """
    gc.collect()
    if platform.system() == "Linux":
        try:
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except OSError:
            pass
