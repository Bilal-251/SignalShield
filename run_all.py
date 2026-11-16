"""One-click runner (no terminal needed): open this file in any editor/IDE (VS Code, PyCharm) or Colab and press Run.
Steps: make items -> pilot -> main run -> analysis. Safe to re-run: finished work is cached and skipped.
Set PILOT_ONLY = False first, check the cost and results, then set it to False."""
import subprocess
import sys

PILOT_ONLY = False
N_ITEMS = 80
REPS = 2

py = sys.executable
def sh(*a):
    print(">>", *a, flush=True)
    subprocess.run([py, *a], check=True)

sh("gen_items.py", "--n", str(N_ITEMS), "--out", "items.json", "--workers", "6")
if PILOT_ONLY:
    sh("run.py", "--n-items", "20", "--arms", "A0,A1", "--reps", "1", "--out", "pilot.jsonl")
    print("Pilot done. Check the spend printed above, then set PILOT_ONLY = False and run again.")
else:
    sh("run.py", "--n-items", str(N_ITEMS), "--arms", "A0,A1,A3,A4,A6,A7", "--reps", str(REPS))
    sh("analyze.py")