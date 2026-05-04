import json
from app.parser import parse_replay_log

with open("./samples/sample.json", "r", encoding="utf-8") as f:
    replay_data = json.load(f)

log_text = replay_data["log"]

from app.parser import parse_replay_log
from app.context import group_events_by_turn, link_damage_and_faint_context

events = parse_replay_log(log_text)

turns = group_events_by_turn(events)
print("Turns parsed:", list(turns.keys()))

linked = link_damage_and_faint_context(events)

for item in linked[:20]:
    print(item)