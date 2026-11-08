from fastapi import APIRouter, Request

from ml_core.model_manager import ModelManager

router = APIRouter(prefix="/debug", tags=["debug"])

# Only mounted when settings.debug is True (see main.py) — temporary, remove
# before the final demo per the Phase 6 doc.


@router.get("/model-status")
def model_status(request: Request):
    manager: ModelManager = request.app.state.model_manager
    return {
        name: {
            "loaded": model.is_loaded,
            "always_resident": model.always_resident,
            "last_used": manager.last_used.get(name),
        }
        for name, model in manager.models.items()
    }
