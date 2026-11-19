import os
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from model.config import BLOCK_SIZE, D_MODEL, N_HEADS, N_LAYERS
    from model.network import AKByteModel

    assert D_MODEL % N_HEADS == 0
    model = AKByteModel()
    sample = torch.randint(0, 256, (1, min(16, BLOCK_SIZE)))
    logits, _ = model(sample)
    assert logits.shape == (1, sample.shape[1], 256)
    print(
        f"Architecture OK: {N_LAYERS} layers, {D_MODEL} dimensions, "
        f"{N_HEADS} heads ({D_MODEL // N_HEADS} per head)"
    )

    weights = os.getenv("AK_WEIGHTS", str(ROOT / "model" / "weights.pt"))
    import api

    if not os.path.isfile(weights):
        assert api.health()["ok"] is True
        assert api.status()["trained"] is False
        print("API import/health OK; no trained checkpoint exists yet (expected before training).")
        return

    health = api.health()
    assert health["ok"] is True
    assert health["trained_weights_available"] is True
    status = api.status()
    assert status["trained"] is True
    assert status["uses_external_model_api"] is False
    assert status["pretrained_weights"] is False

    torch.manual_seed(7)
    result = api.chat(api.ChatRequest(message="Namaste", max_new_tokens=12))
    assert result.trained is True
    assert result.model == "AK-Byte-1"
    assert isinstance(result.reply, str) and len(result.reply) > 0
    print("AK-Byte-1 trained API smoke test passed")
    print(f"Generated sample: {result.reply!r}")


if __name__ == "__main__":
    main()
