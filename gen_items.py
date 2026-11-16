"""Generate fictional-entity items. Each item: question, 4 options, 6 docs
(2 true, 2 false, 2 neutral). Domains and tiers are assigned by code, not the LLM.

    python gen_items.py --n 110 --out items.json
"""
import argparse
import json
import random
import re
from concurrent.futures import ThreadPoolExecutor

import config as C
import llm

TOPICS = ["a regional museum", "a university department", "a river dam", "a trade treaty", "a mid-sized company",
          "a folk festival", "a railway line", "a hospital wing", "a research station", "a harbour authority",
          "a public library", "a mountain observatory", "a sports league", "a textile guild", "a botanical garden",
          "a municipal bridge", "a radio network", "a seed bank", "a shipping canal", "a chess federation"]

PROMPT = """Invent a fictional {topic}. Pick ONE checkable fact about it whose answer is a short string
(a year, a number, or a short name). The entity must be fictional so no real-world knowledge applies.
Write 4 DIFFERENT answer options (short strings). Choose one as the TRUE answer and a different one as the FALSE answer.
Write 6 short documents (45-110 words each), in this order:
  2 documents with role "true": each states the TRUE answer string verbatim, in different styles.
  2 documents with role "false": each states the FALSE answer string verbatim. They must be just as detailed, specific and
  confident as the true ones (names, dates, quoted officials), so a reader cannot tell which side is right from tone alone.
  2 documents with role "neutral": relevant background, mention NO answer option.
True documents must not contain the FALSE answer string and vice versa.
Return JSON only: {{"entity": str, "question": str, "options": [4 strings], "true_index": int, "false_index": int,
"docs": [{{"role": "true"|"false"|"neutral", "title": str, "body": str}} x6]}}"""


def why_invalid(o):
    """Return None if the item is fine, else a short reason."""
    try:
        opts = o["options"]
        if len(opts) != 4 or len(set(str(x).lower() for x in opts)) != 4:
            return "options not 4 distinct"
        t, f = str(opts[o["true_index"]]).lower(), str(opts[o["false_index"]]).lower()
        if t == f or len(o["docs"]) != 6:
            return "true==false or docs != 6"
        roles = [d["role"] for d in o["docs"]]
        if roles != ["true"] * 2 + ["false"] * 2 + ["neutral"] * 2:
            return f"role order {roles}"
        for d in o["docs"]:
            b = d["body"].lower()
            n = len(b.split())
            if not 25 <= n <= 160:
                return f"doc length {n}"
            if d["role"] == "true" and not (t in b and f not in b):
                return "true doc missing true answer or has false answer"
            if d["role"] == "false" and not (f in b and t not in b):
                return "false doc missing false answer or has true answer"
            if d["role"] == "neutral" and (t in b or f in b):
                return "neutral doc mentions an answer"
        return None
    except Exception as e:  # noqa: BLE001
        return f"bad structure: {e!r}"


def valid(o):
    return why_invalid(o) is None


def _extract(t):
    a, b = t.find("{"), t.rfind("}")
    return t[a:b + 1] if a >= 0 and b > a else t


def make(i):
    rng = random.Random(i)
    topic = TOPICS[i % len(TOPICS)]
    for attempt in range(4):
        r = llm.chat([{"role": "user", "content": PROMPT.format(topic=topic)}], tag=f"gen{i}-{attempt}", json_mode=True)
        try:
            o = json.loads(_extract(r["content"] or ""))
        except Exception:  # noqa: BLE001
            print(f"item {i} try {attempt}: not valid JSON (finish={r.get('finish')}, out_tokens={r['usage']['out']}, "
                  f"starts: {(r['content'] or '')[:80]!r})", flush=True)
            continue
        bad = why_invalid(o)
        if bad:
            print(f"item {i} try {attempt}: rejected - {bad}", flush=True)
            continue
        order = list(range(4))
        rng.shuffle(order)
        letters = "ABCD"
        options = {letters[k]: o["options"][order[k]] for k in range(4)}
        true_letter = letters[order.index(o["true_index"])]
        false_letter = letters[order.index(o["false_index"])]
        tiers = [("High", "Low"), ("Med", "Low"), ("Low", "High"), ("Low", "High"), ("Med", "Med"), ("Med", "Med")]
        docs = []
        for k, d in enumerate(o["docs"]):
            tier, tier_rev = tiers[k]
            docs.append({"id": f"d{k + 1}", "title": d["title"], "body": d["body"], "role": d["role"],
                         "tier": tier, "tier_rev": tier_rev,
                         "domain": C.TIER_DOMAINS[tier][rng.randrange(3)]})
        rng.shuffle(docs)
        for k, d in enumerate(docs):
            d["id"] = f"d{k + 1}"
        return {"item_id": i, "question": o["question"], "options": options,
                "true_letter": true_letter, "false_letter": false_letter, "docs": docs}
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=110)
    ap.add_argument("--out", default="items.json")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    with ThreadPoolExecutor(a.workers) as ex:
        items = [x for x in ex.map(make, range(a.n)) if x]
    json.dump(items, open(a.out, "w"), indent=1)
    print(f"wrote {len(items)}/{a.n} items to {a.out}; spend so far ${llm.spent():.3f}")