from fastapi import APIRouter
from pydantic import BaseModel
from app.analyzer import analyze_replay

# Router da API.
router = APIRouter()

# Estrutura de entrada do endpoint.
class ReplayRequest(BaseModel):
    log_text: str
    format_id: str | None = None
    winner: str | None = None

# Endpoint principal
@router.post("/analyze")
def analyze(req: ReplayRequest):
    # Chama o motor de análise.
    result = analyze_replay(
        log_text=req.log_text,
        format_id=req.format_id,
        winner=req.winner
    )

    # Como BattleAnalysis é dataclass, __dict__ já funciona para serializar.
    return result.__dict__