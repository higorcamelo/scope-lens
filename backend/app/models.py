from dataclasses import dataclass, field
from typing import Optional, Any

# Representa um evento individual extraído do log do replay.
# Ex.: um move, um switch, um faint, um status, etc.
@dataclass
class BattleEvent:
    turn: int                      # turno em que o evento aconteceu
    kind: str                      # tipo do evento ("move", "-status", "faint"...)
    actor: Optional[str] = None    # quem executou ou quem foi afetado, dependendo do evento
    target: Optional[str] = None   # alvo do evento, quando existir
    move: Optional[str] = None     # nome do golpe usado, se for um move
    value: Optional[Any] = None    # valor auxiliar, como item, status, stat boost, HP, etc.
    tags: list[str] = field(default_factory=list)  # rótulos úteis para filtragem
    raw: str = ""                  # linha original do log, para debug e rastreio

# Agrupa os eventos de um turno.
# Útil para análises por turno, turn summaries e turning points.
@dataclass
class BattleTurn:
    turn: int
    events: list[BattleEvent] = field(default_factory=list)

# Guarda a "nota" de cada Pokémon na partida.
# Usado para decidir MVP, ameaças e relevância.
@dataclass
class PokemonImpact:
    name: str
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)

# Estrutura final que a API devolve.
# É o resumo do replay.
@dataclass
class BattleAnalysis:
    winner: Optional[str]
    format_id: Optional[str]
    mvp: Optional[str]
    turning_points: list[int]
    main_threats: list[str]
    win_condition: Optional[str]
    summary: str