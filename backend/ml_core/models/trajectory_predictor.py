import torch
import torch.nn as nn

from ml_core.base import LoadableModel


class TrajectoryLSTM(nn.Module):
    # Must match notebooks/train_m3.ipynb's architecture exactly — this
    # wrapper loads a state_dict, not a pickled module, so the class
    # definition has to be reconstructed here bit-for-bit.
    def __init__(self, input_size=1, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :]).squeeze(-1)


class TrajectoryPredictor(LoadableModel):
    always_resident = True

    def __init__(self, weights_path: str):
        super().__init__()
        self.weights_path = weights_path
        self.model: TrajectoryLSTM | None = None

    def load(self) -> None:
        if self._loaded:
            return
        self.model = TrajectoryLSTM()
        self.model.load_state_dict(torch.load(self.weights_path, map_location="cpu", weights_only=False))
        self.model.eval()
        self._loaded = True

    def infer(self, recent_scores: list[float]) -> dict:
        # recent_scores: last SEQ_LEN=5 session scores, oldest first
        x = torch.tensor(recent_scores, dtype=torch.float32).view(1, -1, 1)
        with torch.no_grad():
            predicted_next = self.model(x).item()
        trend = (
            "declining" if predicted_next < recent_scores[-1] - 3
            else "improving" if predicted_next > recent_scores[-1] + 3
            else "stable"
        )
        return {"predicted_next_score": round(predicted_next, 1), "trend": trend}

    def unload(self) -> None:
        pass  # never actually called for an always_resident model — see model_manager.py
