import logging
from pathlib import Path
from typing import Any, Dict, Mapping

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier, XGBRegressor

try:
    import sklearn.compose._column_transformer as ct
    if not hasattr(ct, "_RemainderColsList"):
        class _RemainderColsList(list):
            pass
        ct._RemainderColsList = _RemainderColsList
except Exception:
    pass

logger = logging.getLogger("roadsense")


class AccidentRiskService:
    REQUIRED_FILES = {
        "classifier": "accident_risk_classifier.json",
        "regressor": "accident_risk_regressor.json",
        "preprocessor": "accident_preprocessor.pkl",
        "label_encoder": "accident_label_encoder.pkl",
    }

    def __init__(self, model_dir: str | Path | None = None):
        base_dir = Path(model_dir) if model_dir is not None else Path(__file__).resolve().parents[1] / "ml" / "models"
        self.model_dir = base_dir
        self.classifier = None
        self.regressor = None
        self.preprocessor = None
        self.label_encoder = None
        self._load_models()

    def _load_models(self) -> None:
        missing = [
            name for name, file_name in self.REQUIRED_FILES.items() if not (self.model_dir / file_name).exists()
        ]
        if missing:
            missing_list = ", ".join(missing)
            raise RuntimeError(f"Missing accident-risk model artifact(s): {missing_list}")

        try:
            self.classifier = XGBClassifier()
            self.classifier.load_model(str(self.model_dir / self.REQUIRED_FILES["classifier"]))

            self.regressor = XGBRegressor()
            self.regressor.load_model(str(self.model_dir / self.REQUIRED_FILES["regressor"]))

            self.preprocessor = joblib.load(str(self.model_dir / self.REQUIRED_FILES["preprocessor"]))
            self.label_encoder = joblib.load(str(self.model_dir / self.REQUIRED_FILES["label_encoder"]))

            logger.info("Loaded accident-risk model artifacts from %s", self.model_dir)
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            logger.exception("Failed to load accident-risk model artifacts")
            raise RuntimeError("Failed to load accident-risk model artifacts.") from exc

    def _coerce_payload(self, payload: Mapping[str, Any]) -> pd.DataFrame:
        if not isinstance(payload, Mapping):
            raise ValueError("Prediction payload must be a dictionary-like object.")

        required_fields = [
            "start_location",
            "end_location",
            "start_latitude",
            "start_longitude",
            "end_latitude",
            "end_longitude",
            "road_type",
            "hour",
            "day_of_week",
            "holiday",
            "vehicle_count",
            "average_speed",
            "traffic_density",
            "road_capacity",
            "previous_traffic",
            "weather",
            "rainfall",
            "temperature",
            "visibility",
            "road_condition",
            "historical_accidents",
            "congestion_level",
        ]

        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValueError(f"Missing required prediction fields: {', '.join(missing)}")

        row = pd.DataFrame([dict(payload)])
        return row

    def predict(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        if self.classifier is None or self.regressor is None or self.preprocessor is None or self.label_encoder is None:
            raise RuntimeError("Accident-risk model is not loaded.")

        try:
            df = self._coerce_payload(payload)
            processed = self.preprocessor.transform(df)

            level_prediction = self.classifier.predict(processed)
            risk_level = self.label_encoder.inverse_transform(level_prediction.astype(int))[0]

            probs = self.classifier.predict_proba(processed)[0]
            confidence = float(np.max(probs) * 100)

            risk_prediction = self.regressor.predict(processed)[0]
            accident_risk = float(np.clip(float(risk_prediction), 0.0, 100.0))

            result = {
                "success": True,
                "accident_risk": round(accident_risk, 2),
                "accident_risk_level": str(risk_level).upper(),
                "confidence_score": round(confidence, 1),
                "probabilities": {cls: round(float(p), 4) for cls, p in zip(self.label_encoder.classes_, probs)}
            }
            logger.info("Accident risk prediction produced %s for level %s (confidence: %s%%)", result["accident_risk"], result["accident_risk_level"], result["confidence_score"])
            return result
        except Exception as exc:
            logger.exception("Accident risk prediction failed")
            raise RuntimeError("Accident-risk prediction failed during inference.") from exc


accident_risk_service = AccidentRiskService()
