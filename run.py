"""Run arms over items. Resumable and budget-guarded.

    python run.py --n-items 20 --arms A0,A1 --reps 1 --out pilot.jsonl      # pilot
    python run.py --n-items 100 --arms A0,A1,A3,A4,A6,A7 --reps 2           # main
"""
import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import agent
import config as C
import llm

ap = argparse.ArgumentParser()
ap.add_argument("--items", default="items.json")
ap.add_argument("--n-items", type=int, default=100)
ap.add_argument("--offset", type=int, default=0)
ap.add_argument("--arms", default=",".join(C.ARMS_CORE))
ap.add_argument("--reps", type=int, default=2)
ap.add_argument("--wording", default="W0")
ap.add_argument("--out", default="runs.jsonl")
ap.add_argument("--workers", type=int, default=8)
a = ap.parse_args()

items = json.load(open(a.items))[a.offset:a.offset + a.n_items]
out = Path(a.out)
done = set()
if out.exists():
    for line in out.read_text().splitlines():
        r = json.loads(line)
        done.add((r["item_id"], r["arm"], r["wording"], r["rep"]))

jobs = [(it, arm, rep) for it in items for arm in a.arms.split(",") for rep in range(a.reps)
        if (it["item_id"], arm, a.wording, rep) not in done]
print(f"{len(jobs)} jobs to run ({len(done)} already done). spend so far ${llm.spent():.3f}")

lock = threading.Lock()
stop = threading.Event()
count = [0]


def work(job):
    if stop.is_set():
        return
    it, arm, rep = job
    try:
        row = agent.run(it, arm, a.wording, rep)
    except llm.BudgetExceeded as e:
        stop.set()
        print("BUDGET STOP:", e)
        return
    with lock:
        with out.open("a") as f:
            f.write(json.dumps(row) + "\n")
        count[0] += 1
        if count[0] % 50 == 0:
            print(f"{count[0]} done, spend ${llm.spent():.3f}", flush=True)


with ThreadPoolExecutor(a.workers) as ex:
    list(ex.map(work, jobs))
print(f"finished {count[0]} runs. total spend ${llm.spent():.3f}")