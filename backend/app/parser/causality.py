import re
from collections import defaultdict
from typing import Optional

from app.models import BattleEvent, LinkedBattleEvent

# Captura qual lado o Pokémon pertence: p1 ou p2.
SIDE_RE = re.compile(r"^(p[12])")

def group_events_by_turn(events: list[BattleEvent]) -> dict[int, list[BattleEvent]]:
    # Agrupa todos os eventos por número de turno.
    grouped: dict[int, list[BattleEvent]] = defaultdict(list)
    for event in events:
        grouped[event.turn].append(event)

    # Ordena os turnos para ficar previsível.
    return dict(sorted(grouped.items(), key=lambda item: item[0]))

def get_side(ref: Optional[str]) -> Optional[str]:
    # Extrai o lado do Pokémon, ex.: "p1a: Dragapult" -> "p1"
    if not ref:
        return None
    match = SIDE_RE.match(ref.strip())
    return match.group(1) if match else None

def opposite_side(side: Optional[str]) -> Optional[str]:
    # Inverte o lado.
    if side == "p1":
        return "p2"
    if side == "p2":
        return "p1"
    return None

def normalize_name(raw: Optional[str]) -> Optional[str]:
    # Remove o prefixo p1a:, p2b:, etc.
    if not raw:
        return None
    return raw.split(":")[-1].strip()

def extract_explicit_cause(raw: str) -> tuple[Optional[str], Optional[str]]:
    # Tenta encontrar causas explícitas dentro da linha do log.
    lower = raw.lower()

    # Dano residual.
    if "[from] brn" in lower:
        return "residual", "burn"
    if "[from] psn" in lower:
        return "residual", "poison"
    if "[from] tox" in lower:
        return "residual", "toxic"
    if "[from] sandstorm" in lower:
        return "residual", "sandstorm"
    if "[from] hail" in lower:
        return "residual", "hail"

    # Hazard.
    if "[from] stealth rock" in lower:
        return "hazard", "Stealth Rock"
    if "[from] spikes" in lower:
        return "hazard", "Spikes"

    # Recoil.
    if "[from] recoil" in lower:
        return "recoil", "Recoil"

    # Dano vindo de move.
    move_match = re.search(
        r"\[from\]\s*move:\s*(.+?)(?:\|\[of\]\s*(.+))?$",
        raw,
        flags=re.IGNORECASE
    )
    if move_match:
        return "move", move_match.group(1).strip()

    # Dano vindo de ability.
    ability_match = re.search(
        r"\[from\]\s*ability:\s*(.+?)(?:\|\[of\]\s*(.+))?$",
        raw,
        flags=re.IGNORECASE
    )
    if ability_match:
        return "ability", ability_match.group(1).strip()

    # Dano vindo de item.
    item_match = re.search(
        r"\[from\]\s*item:\s*(.+?)(?:\|\[of\]\s*(.+))?$",
        raw,
        flags=re.IGNORECASE
    )
    if item_match:
        return "item", item_match.group(1).strip()

    return None, None

def _extract_of_target(raw: str) -> Optional[str]:
    # Extração auxiliar do trecho "[of] p1a: X"
    match = re.search(r"\|\[of\]\s*(.+)$", raw, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()

def link_damage_and_faint_context(events: list[BattleEvent]) -> list[LinkedBattleEvent]:
    # Agrupa os eventos por turno antes de processar contexto.
    grouped = group_events_by_turn(events)
    linked: list[LinkedBattleEvent] = []

    # Último move conhecido de cada lado.
    prev_last_move_by_side: dict[str, BattleEvent | None] = {
        "p1": None,
        "p2": None,
    }

    # Memória do último dano em cada vítima.
    last_damage_by_victim: dict[str, LinkedBattleEvent] = {}

    for turn, turn_events in grouped.items():
        # Copia do estado anterior para usar como memória do turno atual.
        last_move_by_side: dict[str, BattleEvent | None] = (
            prev_last_move_by_side.copy()
        )

        for ev in turn_events:
            side = get_side(ev.actor)

            # Se foi um move, atualiza a memória do lado.
            if ev.kind == "move" and side:
                last_move_by_side[side] = ev
                continue

            # Só tentamos linkar dano e faint.
            if ev.kind not in {"-damage", "faint"}:
                continue

            victim = normalize_name(ev.actor)

            # Primeiro tenta achar causa explícita no raw.
            explicit_kind, explicit_label = extract_explicit_cause(ev.raw)

            # Se a causa está explícita, usamos ela.
            if explicit_kind is not None:

                if explicit_kind == "residual":
                    linked_event = LinkedBattleEvent(
                        turn=turn,
                        kind=ev.kind,
                        victim=victim,
                        likely_source=None,
                        source_kind=explicit_kind,
                        confidence=1.0,
                        reason=f"Explicit residual damage: {explicit_label}",
                        raw=ev.raw,
                    )

                    linked.append(linked_event)

                    if victim:
                        last_damage_by_victim[victim] = linked_event

                    continue

                if explicit_kind == "recoil":
                    linked_event = LinkedBattleEvent(
                        turn=turn,
                        kind=ev.kind,
                        victim=victim,
                        likely_source=victim,
                        source_kind="recoil",
                        confidence=1.0,
                        reason="Self-inflicted recoil damage",
                        raw=ev.raw,
                    )

                    linked.append(linked_event)

                    if victim:
                        last_damage_by_victim[victim] = linked_event

                    continue

                likely_source = _extract_of_target(ev.raw)

                linked_event = LinkedBattleEvent(
                    turn=turn,
                    kind=ev.kind,
                    victim=victim,
                    likely_source=normalize_name(likely_source),
                    source_kind=explicit_kind,
                    confidence=0.95 if likely_source else 0.75,
                    reason=f"Explicit cause: {explicit_kind} -> {explicit_label}",
                    raw=ev.raw,
                )

                linked.append(linked_event)

                if victim:
                    last_damage_by_victim[victim] = linked_event

                continue

            # Para faint, tenta usar o último dano no mesmo alvo.
            if ev.kind == "faint" and victim in last_damage_by_victim:
                prev = last_damage_by_victim[victim]

                linked_event = LinkedBattleEvent(
                    turn=turn,
                    kind=ev.kind,
                    victim=victim,
                    likely_source=prev.likely_source,
                    source_kind=prev.source_kind,
                    confidence=min(0.98, prev.confidence + 0.05),
                    reason="Linked from the most recent damage on the same victim",
                    raw=ev.raw,
                )

                linked.append(linked_event)
                continue

            # Fallback: usa o último move do lado oposto.
            source_side = opposite_side(side)
            source_event = (
                last_move_by_side.get(source_side)
                if source_side else None
            )

            if source_event:
                linked_event = LinkedBattleEvent(
                    turn=turn,
                    kind=ev.kind,
                    victim=victim,
                    likely_source=normalize_name(source_event.actor),
                    source_kind="move",
                    confidence=0.85 if source_event.turn == turn else 0.60,
                    reason="Likely caused by the last opposing move",
                    raw=ev.raw,
                )

            else:
                linked_event = LinkedBattleEvent(
                    turn=turn,
                    kind=ev.kind,
                    victim=victim,
                    likely_source=None,
                    source_kind=None,
                    confidence=0.0,
                    reason="No obvious source found",
                    raw=ev.raw,
                )

            linked.append(linked_event)

            # Atualiza a memória do alvo.
            if victim:
                last_damage_by_victim[victim] = linked_event

        # Atualiza memória entre turnos.
        prev_last_move_by_side = last_move_by_side

    return linked