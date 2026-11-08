import asyncio
import logging
import time

from ml_core.base import LoadableModel
from ml_core.memory_watchdog import log_memory_snapshot

logger = logging.getLogger("model_manager")

IDLE_UNLOAD_SECONDS = 5 * 60
IDLE_CHECK_INTERVAL_SECONDS = 60


class ModelManager:
    _instance: "ModelManager | None" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, models: dict[str, LoadableModel] | None = None):
        if getattr(self, "_initialized", False):
            return  # __init__ runs every time ModelManager() is called — guard against re-init
        self.models: dict[str, LoadableModel] = models or {}
        self.last_used: dict[str, float] = {}
        self.heavy_lock = asyncio.Semaphore(1)
        self._initialized = True
        self._watchdog_task: asyncio.Task | None = None
        logger.info(f"ModelManager initialized with models: {list(self.models)}")

    async def startup(self):
        """Call once from FastAPI's lifespan startup event."""
        for name, model in self.models.items():
            if model.always_resident:
                logger.info(f"Loading always-resident model: {name}")
                await asyncio.to_thread(model.load)
        self._watchdog_task = asyncio.create_task(self._idle_watchdog())

    async def shutdown(self):
        if self._watchdog_task:
            self._watchdog_task.cancel()

    async def _idle_watchdog(self):
        while True:
            try:
                await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                now = time.time()
                for name, model in self.models.items():
                    if model.always_resident or not model.is_loaded:
                        continue
                    if now - self.last_used.get(name, now) > IDLE_UNLOAD_SECONDS:
                        logger.info(f"Unloading idle model: {name}")
                        await asyncio.to_thread(model.unload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Idle watchdog iteration failed — continuing")

    async def infer(self, model_name: str, *args, **kwargs):
        model = self.models.get(model_name)
        if model is None:
            raise ValueError(f"Unknown model: {model_name}")

        if model.always_resident:
            # No lock needed — cheap, always loaded, safe to run concurrently.
            return await asyncio.to_thread(model.infer, *args, **kwargs)

        async with self.heavy_lock:  # serializes M1/M2/M5 against each other
            log_memory_snapshot(f"before {model_name}")
            if not model.is_loaded:
                logger.info(f"Lazily loading model: {model_name}")
                await asyncio.to_thread(model.load)
            self.last_used[model_name] = time.time()
            result = await asyncio.to_thread(model.infer, *args, **kwargs)
            self.last_used[model_name] = time.time()  # refresh again — infer() can take a while
            log_memory_snapshot(f"after {model_name}")
            return result
