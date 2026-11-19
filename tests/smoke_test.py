import os
import torch

def main():
    weights = os.getenv("AK_WEIGHTS", "model/weights.pt")
    assert os.path.isfile(weights), f"Missing trained weights: {weights}"

    import api
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
    print("AK-Byte-1 smoke test passed")
    print(f"Generated sample: {result.reply!r}")

if __name__ == "__main__":
    main()
