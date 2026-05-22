from collections import defaultdict

from app.models import BattleAnalysis
from app.parser.causality import link_damage_and_faint_context
from app.parser.parser import parse_replay_log
from app.parser.scoring import get_mvp, score_events

# Palavras-chave que sinalizam eventos decisivos.
# Hoje está definido, mas ainda não está sendo usado diretamente.
# Pode ser útil no futuro para expandir a detecção de turning points. Precisamos de uma base mais sólida
TURNING_KEYWORDS = {
    "trick room",
    "tailwind",
    "belly drum",
    "dynamax",
    "weakness policy",
    "faint",
    "knock off",
}

def detect_turning_points(events):
    # Guarda uma pontuação por turno.
    turn_scores = defaultdict(int)

    # Guarda as razões pelas quais cada turno foi importante.
    turn_reasons = defaultdict(list)

    linked_events = link_damage_and_faint_context(events)

    for ev in events:
        # Texto auxiliar para facilitar detecção.
        text = f"{ev.kind} {ev.move or ''} {ev.raw}".lower()

        # KO tende a mudar muito o turno.
        if ev.kind == "faint":
            turn_scores[ev.turn] += 5
            turn_reasons[ev.turn].append("KO occurred")

        # Trick Room costuma mudar muito o ritmo da batalha.
        if "trick room" in text:
            turn_scores[ev.turn] += 6
            turn_reasons[ev.turn].append("Trick Room changed tempo")

        # Tailwind também muda muito o fluxo.
        if "tailwind" in text:
            turn_scores[ev.turn] += 6
            turn_reasons[ev.turn].append("Tailwind changed tempo")

        # Belly Drum costuma gerar ameaça imediata (Saudades do meu Azumarill).
        if "belly drum" in text:
            turn_scores[ev.turn] += 5
            turn_reasons[ev.turn].append("Belly Drum threat activated")

        # Weakness Policy geralmente sinaliza explosão de pressão.
        if "weakness policy" in text:
            turn_scores[ev.turn] += 4
            turn_reasons[ev.turn].append("Weakness Policy activated")

        # Knock Off costuma ter valor estratégico alto.
        if "knock off" in text:
            turn_scores[ev.turn] += 2
            turn_reasons[ev.turn].append("Item removed")

    # Eventos causais pesam MUITO.
    for linked in linked_events:

        # KO real detectado pela camada causal.
        if linked.kind == "faint" and linked.likely_source:
            turn_scores[linked.turn] += int(6 * linked.confidence)

            turn_reasons[linked.turn].append(
                f"{linked.likely_source} secured a KO"
            )

        # Hazards começando a gerar pressão.
        elif linked.source_kind == "hazard":
            turn_scores[linked.turn] += int(2 * linked.confidence)

            turn_reasons[linked.turn].append(
                "Entry hazards generated pressure"
            )

        # Dano residual importante.
        elif linked.source_kind == "residual":
            turn_scores[linked.turn] += int(1 * linked.confidence)

            turn_reasons[linked.turn].append(
                "Residual damage accumulated"
            )

    if not turn_scores:
        return []

    # Mantém os turnos que ficaram perto do turno mais importante.
    threshold = max(turn_scores.values()) * 0.75

    return sorted([
        turn
        for turn, score in turn_scores.items()
        if score >= threshold
    ])

def analyze_replay(
    log_text: str,
    format_id: str | None = None,
    winner: str | None = None,
) -> BattleAnalysis:

    # 1) transforma o log em eventos
    events = parse_replay_log(log_text)

    # 2) pontua os eventos
    impacts = score_events(events)

    # 3) escolhe o MVP
    mvp = get_mvp(impacts)

    # 4) detecta turnos mais decisivos
    turning_points = detect_turning_points(events)

    # 5) extrai ameaças principais
    threats = sorted(
        [
            p
            for p in impacts.values()
            if p.score >= 4
        ],
        key=lambda x: x.score,
        reverse=True,
    )[:3]

    # Resumo simples
    summary = (
        "Replay analisado com foco em eventos decisivos, "
        "pressão estratégica e controle de ritmo."
    )

    # Monta o objeto final da análise.
    return BattleAnalysis(
        winner=winner,
        format_id=format_id,
        mvp=mvp.name if mvp else None,
        turning_points=turning_points,
        main_threats=[t.name for t in threats],
        win_condition=None,  # TODO: ainda não implementado
        summary=summary,
    )