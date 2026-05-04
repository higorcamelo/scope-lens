from collections import defaultdict
from app.models import BattleEvent, PokemonImpact

# Pesos iniciais do MVP.
# Eles não precisam cobrir tudo no jogo.
# Servem só para os eventos mais fortes e mais fáceis de reconhecer.
WEIGHTS = {
    "ko": 6,
    "setup_trick_room": 8,
    "setup_tailwind": 7,
    "setup_belly_drum": 8,
    "setup_swords_dance": 5,
    "setup_dragon_dance": 5,
    "weakness_policy": 6,
    "weather_control": 4,
    "status_inflicted": 2,
    "item_removed": 3,
    "speed_control_lost": 5,
    "forced_switch": 2,
    "important_damage": 2,
    "faint_early": -4,
}

def normalize_name(raw: str | None) -> str | None:
    # Remove o prefixo p1a:, p2b:, etc.
    if not raw:
        return None
    return raw.split(":")[-1].strip()

def score_events(events: list[BattleEvent]) -> dict[str, PokemonImpact]:
    # Guarda a pontuação acumulada de cada Pokémon.
    impacts = defaultdict(lambda: PokemonImpact(name=""))

    for ev in events:
        pokemon = normalize_name(ev.actor)
        if not pokemon:
            continue

        if pokemon not in impacts:
            impacts[pokemon] = PokemonImpact(name=pokemon)

        # Faint reduz impacto.
        if ev.kind == "faint":
            impacts[pokemon].score -= 3
            impacts[pokemon].reasons.append("Fainted")
            continue

        # Status: relevante, principalmente paralisação.
        if ev.kind == "-status":
            status = str(ev.value)
            impacts[pokemon].score += WEIGHTS["status_inflicted"]
            impacts[pokemon].reasons.append(f"Inflicted status: {status}")

            if status == "par":
                impacts[pokemon].score += 1
                impacts[pokemon].reasons.append("Speed control affected by paralysis")

        # Boosts: alguns são bem mais importantes que outros.
        elif ev.kind == "-boost" and isinstance(ev.value, dict):
            stat = ev.value.get("stat")
            amount = ev.value.get("amount")
            impacts[pokemon].score += int(amount or 1)

            if stat in {"atk", "spa", "spe"}:
                impacts[pokemon].score += 2
                impacts[pokemon].reasons.append(f"Important boost: {stat} +{amount}")
            else:
                impacts[pokemon].reasons.append(f"Boosted {stat} +{amount}")

        # Remoção de item: muito relevante quando afeta item forte.
        elif ev.kind == "-enditem":
            item = str(ev.value).lower()
            impacts[pokemon].score += WEIGHTS["item_removed"]
            impacts[pokemon].reasons.append(f"Lost item: {ev.value}")

            if item in {"focus sash", "weakness policy", "choice scarf", "choice specs", "choice band"}:
                impacts[pokemon].score += 2
                impacts[pokemon].reasons.append(f"High-impact item removed: {ev.value}")

            if item == "weakness policy":
                impacts[pokemon].score += WEIGHTS["weakness_policy"]
                impacts[pokemon].reasons.append("Weakness Policy activated")

        # Campo: Trick Room e Tailwind são muito importantes.
        elif ev.kind == "-fieldstart":
            effect = str(ev.value).lower()
            if "trick room" in effect:
                impacts[pokemon].score += WEIGHTS["setup_trick_room"]
                impacts[pokemon].reasons.append("Set Trick Room")
            elif "tailwind" in effect:
                impacts[pokemon].score += WEIGHTS["setup_tailwind"]
                impacts[pokemon].reasons.append("Set Tailwind")
            else:
                impacts[pokemon].score += 2
                impacts[pokemon].reasons.append(f"Field effect: {ev.value}")

        # Weather também pode ser relevante.
        elif ev.kind == "-weather":
            impacts[pokemon].score += WEIGHTS["weather_control"]
            impacts[pokemon].reasons.append(f"Weather involved: {ev.value}")

        # Moves de setup aumentam muito a importância.
        elif ev.kind == "move":
            move = (ev.move or "").lower()

            if move == "trick room":
                impacts[pokemon].score += WEIGHTS["setup_trick_room"]
                impacts[pokemon].reasons.append("Used Trick Room")

            elif move == "tailwind":
                impacts[pokemon].score += WEIGHTS["setup_tailwind"]
                impacts[pokemon].reasons.append("Used Tailwind")

            elif move == "belly drum":
                impacts[pokemon].score += WEIGHTS["setup_belly_drum"]
                impacts[pokemon].reasons.append("Used Belly Drum")

            elif move in {"swords dance", "nasty plot", "dragon dance", "quiver dance"}:
                impacts[pokemon].score += WEIGHTS["setup_swords_dance"]
                impacts[pokemon].reasons.append(f"Used setup move: {ev.move}")

    return impacts

def get_mvp(impacts: dict[str, PokemonImpact]) -> PokemonImpact | None:
    # Retorna o Pokémon com maior pontuação.
    if not impacts:
        return None
    return max(impacts.values(), key=lambda x: x.score)