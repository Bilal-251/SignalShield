"""Diagnostic: makes ONE call and shows exactly what Cohere returns. Press Run on this file."""
import json
import config as C
import cohere, os

co = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"], timeout=120)
for label, extra in [("thinking disabled", dict(thinking={"type": "disabled"})), ("default", {})]:
    r = co.chat(model=C.MODEL, max_tokens=1500, messages=[{"role": "user", "content":
        "Return JSON only: {\"year\": 1987, \"name\": \"test\"}"}], response_format={"type": "json_object"}, **extra)
    print("====", label)
    print("finish:", r.finish_reason, "| tokens:", r.usage.tokens, "| billed:", r.usage.billed_units)
    for c in r.message.content or []:
        print(" block:", c.type, "|", (getattr(c, "text", None) or getattr(c, "thinking", None) or "")[:200].replace("\n", " "))