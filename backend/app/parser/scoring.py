from collections import defaultdict
from app.models import BattleEvent, PokemonImpact
from app.parser.causality import link_damage_and_faint_context

# Pesos do MVP.
# A ideia agora é:
# - scorear por impacto causado
# - não só por "quem usou setup"
# - aproveitar a camada causal que você já construiu
WEIGHTS = {
    "ko": 8,
    "assist_ko": 3,
    "major_damage": 3,
    "chip_damage": 1,

    "setup_trick_room": 8,
    "setup_tailwind": 7,
    "setup_belly_drum": 8,
    "setup_swords_dance": 5,

    "weakness_policy": 6,

    "weather_control": 4,

    "status_inflicted": 2,
    "speed_control": 2,

    "item_removed": 3,

    "hazard_damage": 1,
    "residual_damage": 1,

    "fainted": -3,
}

HIGH_IMPACT_ITEMS = {
    "focus sash",
    "weakness policy",
    "choice scarf",
    "choice specs",
    "choice band",
    "eviolite",
    "assault vest",
}

SETUP_MOVES = {
    "swords dance",
    "nasty plot",
    "dragon dance",
    "quiver dance",
    "calm mind",
    "bulk up",
    "shell smash",
}

def normalize_name(raw: str | None) -> str | None:
    if not raw:
        return None
    return raw.split(":")[-1].strip()

def add_score(
    impacts: dict[str, PokemonImpact],
    pokemon: str,
    amount: int,
    reason: str,
):
    if pokemon not in impacts:
        impacts[pokemon] = PokemonImpact(name=pokemon)

    impacts[pokemon].score += amount
    impacts[pokemon].reasons.append(reason)

def score_events(events: list[BattleEvent]) -> dict[str, PokemonImpact]:
    impacts = defaultdict(lambda: PokemonImpact(name=""))

    # 1. SCORE NORMAL DOS EVENTOS
    for ev in events:
        pokemon = normalize_name(ev.actor)

        if not pokemon:
            continue

        if pokemon not in impacts:
            impacts[pokemon] = PokemonImpact(name=pokemon)

        # FAINT
        if ev.kind == "faint":
            add_score(
                impacts,
                pokemon,
                WEIGHTS["fainted"],
                "Fainted",
            )
            continue

        # STATUS
        elif ev.kind == "-status":
            status = str(ev.value)

            add_score(
                impacts,
                pokemon,
                WEIGHTS["status_inflicted"],
                f"Inflicted status: {status}",
            )

            if status == "par":
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["speed_control"],
                    "Applied paralysis speed control",
                )

        # BOOSTS
        elif ev.kind == "-boost" and isinstance(ev.value, dict):
            stat = ev.value.get("stat")
            amount = int(ev.value.get("amount") or 1)

            base = amount

            if stat in {"atk", "spa", "spe"}:
                base += 2

            add_score(
                impacts,
                pokemon,
                base,
                f"Boosted {stat} +{amount}",
            )

        # ITEM REMOVAL
        elif ev.kind == "-enditem":
            item = str(ev.value).lower()

            points = WEIGHTS["item_removed"]

            if item in HIGH_IMPACT_ITEMS:
                points += 2

            add_score(
                impacts,
                pokemon,
                points,
                f"Lost important item: {ev.value}",
            )

            # Weakness Policy ativando é relevante
            if item == "weakness policy":
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["weakness_policy"],
                    "Weakness Policy activated",
                )

        # FIELD
        elif ev.kind == "-fieldstart":
            effect = str(ev.value).lower()

            if "trick room" in effect:
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["setup_trick_room"],
                    "Set Trick Room",
                )

            elif "tailwind" in effect:
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["setup_tailwind"],
                    "Set Tailwind",
                )

        # WEATHER
        elif ev.kind == "-weather":
            add_score(
                impacts,
                pokemon,
                WEIGHTS["weather_control"],
                f"Weather control: {ev.value}",
            )
            
        # MOVE
        elif ev.kind == "move":
            move = (ev.move or "").lower()

            if move == "trick room":
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["setup_trick_room"],
                    "Used Trick Room",
                )

            elif move == "tailwind":
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["setup_tailwind"],
                    "Used Tailwind",
                )

            elif move == "belly drum":
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["setup_belly_drum"],
                    "Used Belly Drum",
                )

            elif move in SETUP_MOVES:
                add_score(
                    impacts,
                    pokemon,
                    WEIGHTS["setup_swords_dance"],
                    f"Used setup move: {ev.move}",
                )

    # 2. SCORE CAUSAL (DANO / KO)

    linked_events = link_damage_and_faint_context(events)

    for linked in linked_events:
        source = linked.likely_source

        if not source:
            continue

        # DAMAGE
        if linked.kind == "-damage":

            # Dano residual e hazards contam menos.
            if linked.source_kind in {"hazard", "residual"}:
                add_score(
                    impacts,
                    source,
                    WEIGHTS["hazard_damage"],
                    f"Applied passive damage to {linked.victim}",
                )
                continue

            # Dano normal ofensivo.
            add_score(
                impacts,
                source,
                WEIGHTS["chip_damage"],
                f"Damaged {linked.victim}",
            )

            # KO embutido no dano.
            if "0 fnt" in linked.raw:
                add_score(
                    impacts,
                    source,
                    WEIGHTS["major_damage"],
                    f"Delivered lethal damage to {linked.victim}",
                )

        # FAINT
        elif linked.kind == "faint":

            add_score(
                impacts,
                source,
                WEIGHTS["ko"],
                f"KO'd {linked.victim}",
            )

    return impacts

def get_mvp(impacts: dict[str, PokemonImpact]) -> PokemonImpact | None:
    if not impacts:
        return None

    return max(
        impacts.values(),
        key=lambda x: x.score,
    )