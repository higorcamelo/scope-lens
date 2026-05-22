import re
from app.models import BattleEvent

# Detecta mudanças de turno no log.
TURN_RE = re.compile(r"^\|turn\|(\d+)$")

def parse_replay_log(log_text: str) -> list[BattleEvent]:
    # Lista final de eventos estruturados.
    events: list[BattleEvent] = []

    # Turno atual enquanto percorremos o log.
    current_turn = 0

    # Percorre o replay linha por linha.
    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Se a linha indicar mudança de turno, atualiza o estado.
        turn_match = TURN_RE.match(line)
        if turn_match:
            current_turn = int(turn_match.group(1))
            continue

        # Separa os campos do log usando "|".
        parts = line.split("|")

        # Ex.: ["", "move", "p1a: Solgaleo", "Knock Off", "p2b: Rotom"]
        if len(parts) < 2:
            continue

        kind = parts[1]

        # Golpe usado.
        if kind == "move" and len(parts) >= 5:
            events.append(BattleEvent(
                turn=current_turn,
                kind="move",
                actor=parts[2],   # quem usou o golpe
                move=parts[3],    # qual golpe
                target=parts[4],  # alvo
                raw=line,
                tags=["action"]
            ))

        # Weather ou mudança de clima.
        elif kind == "-weather" and len(parts) >= 4:
            events.append(BattleEvent(
                turn=current_turn,
                kind="-weather",
                actor=parts[3].replace("[of] ", "").strip(),  # responsável pelo weather
                value=parts[2],  # SunnyDay, RainDance etc.
                raw=line,
                tags=["weather"]
            ))

        # Troca de Pokémon.
        elif kind == "switch" and len(parts) >= 4:
            events.append(BattleEvent(
                turn=current_turn,
                kind="switch",
                actor=parts[2],  # quem entrou
                value=parts[3],  # forma completa do Pokémon
                raw=line,
                tags=["position_change"]
            ))

        # Faint.
        elif kind == "faint" and len(parts) >= 3:
            events.append(BattleEvent(
                turn=current_turn,
                kind="faint",
                actor=parts[2],  # Pokémon que caiu
                raw=line,
                tags=["ko"]
            ))

        # Status.
        elif kind == "-status" and len(parts) >= 4:
            events.append(BattleEvent(
                turn=current_turn,
                kind="-status",
                actor=parts[2],  # Pokémon afetado
                value=parts[3],  # par / brn / slp / etc.
                raw=line,
                tags=["status"]
            ))

        # Boost de stats.
        elif kind == "-boost" and len(parts) >= 5:
            events.append(BattleEvent(
                turn=current_turn,
                kind="-boost",
                actor=parts[2],  # Pokémon afetado
                value={"stat": parts[3], "amount": parts[4]},
                raw=line,
                tags=["boost"]
            ))

        # Campo iniciado.
        elif kind == "-fieldstart" and len(parts) >= 4:
            events.append(BattleEvent(
                turn=current_turn,
                kind="-fieldstart",
                actor=parts[3].replace("[of] ", "").strip(),  # quem colocou o efeito
                value=parts[2],  # move: Trick Room, move: Tailwind etc.
                raw=line,
                tags=["field_effect"]
            ))

        # Item removido.
        elif kind == "-enditem" and len(parts) >= 4:
            events.append(BattleEvent(
                turn=current_turn,
                kind="-enditem",
                actor=parts[2],  # Pokémon que perdeu o item
                value=parts[3],  # item removido
                raw=line,
                tags=["item_change"]
            ))

        # Dano.
        elif kind == "-damage" and len(parts) >= 4:
            events.append(BattleEvent(
                turn=current_turn,
                kind="-damage",
                actor=parts[2],   # Pokémon que sofreu dano
                value=parts[3],   # HP restante
                raw=line,
                tags=["damage"]
            ))

        # Qualquer outro evento "-" que ainda não tratamos.
        elif kind.startswith("-"):
            events.append(BattleEvent(
                turn=current_turn,
                kind=kind,
                raw=line
            ))

    return events