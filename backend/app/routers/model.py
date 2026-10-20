import json

from fastapi import APIRouter, Depends

from app.ml.train import METRICS_PATH
from app.models import User
from app.schemas import PredictIn, PredictionOut
from app.security import get_current_user
from app.services.predictor import get_predictor

router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/metrics")
def metrics(_: User = Depends(get_current_user)):
    return json.loads(METRICS_PATH.read_text())


@router.post("/predict", response_model=PredictionOut)
def what_if(body: PredictIn, _: User = Depends(get_current_user)):
    """Prediction only, nothing is stored."""
    return get_predictor().predict_one(body.model_dump(exclude={"term"}))
