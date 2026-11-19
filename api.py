import os
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from model.network import AKByteModel
from model.config import BLOCK_SIZE

app = FastAPI(title="Ankit Kryptex AI API", version="0.1.0")
DEVICE = torch.device("cpu")
MODEL = None
WEIGHTS_PATH = os.getenv("AK_WEIGHTS", "model/weights.pt")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    max_new_tokens: int = Field(default=100, ge=1, le=180)

class ChatResponse(BaseModel):
    reply: str
    model: str = "AK-Byte-1"
    trained: bool

def load_model():
    global MODEL
    if MODEL is not None:
        return MODEL
    if not os.path.exists(WEIGHTS_PATH):
        return None
    try:
        checkpoint = torch.load(WEIGHTS_PATH, map_location=DEVICE, weights_only=True)
        model = AKByteModel()
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        MODEL = model
        return MODEL
    except (RuntimeError, KeyError, OSError, ValueError) as error:
        # Old checkpoints may use a different architecture; wait for the new training run.
        print(f"AK-Byte-1 weights are not compatible with this architecture yet: {error}", flush=True)
        return None

@app.get("/health")
def health():
    return {"ok": True, "model": "AK-Byte-1", "trained_weights_available": load_model() is not None}

@app.get("/api/status")
def status():
    return {"name": "Ankit Kryptex AI", "model": "AK-Byte-1", "trained": load_model() is not None,
            "uses_external_model_api": False, "pretrained_weights": False}

@app.post("/api/chat", response_model=ChatResponse)
def chat(body: ChatRequest):
    model = load_model()
    if model is None:
        raise HTTPException(status_code=503, detail="Model abhi train nahi hua. GitHub Actions mein 'Train AK-Byte-1 from scratch' workflow run karo.")
    prompt = ("User: " + body.message.strip() + "\nAnkit Kryptex: ").encode("utf-8")
    tokens = torch.tensor(list(prompt), dtype=torch.long, device=DEVICE)[None, :]
    with torch.no_grad():
        output = model.generate(tokens, max_new_tokens=body.max_new_tokens)
    generated = bytes(output[0, tokens.shape[1]:].tolist()).decode("utf-8", errors="replace")
    reply = generated.split("\nUser:", 1)[0].split("\n\n", 1)[0].strip()
    return ChatResponse(reply=reply or "Mujhe abhi iska jawab generate karna nahi aaya.", trained=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def home():
    return FileResponse("static/index.html")
