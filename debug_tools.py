"""Diagnostic: one agent run, printing the full error if there is one. Press Run."""
import json
import agent
items = json.load(open("items.json"))
row = agent.run(items[0], "A0", "W0", 0)
print(json.dumps(row, indent=1))