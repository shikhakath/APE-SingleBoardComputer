"""Run the MCP's check_placement over the whole board in batches and summarise it.

One call with all parts runs for many minutes and locks Altium past the bridge's
timeout, so this sends 40 parts at a time (about a second per part) and retries a
batch once. Each part is measured against every other part on its side, so a pair
can appear twice; the summary counts it once. Take the Altium lock first (see
docs/pcb-placement.md).

    python hardware/gen/placement_check.py [clearance_mils]

Writes out/check_placement.json.
"""
import json
import sys
import time

import mcp_client
import placement as P


def main(argv):
    clearance = float(argv[0]) if argv else 6.0
    parts, _ = P.load_parts()
    designators = sorted(parts, key=P._natural)
    pairs = {}
    missing = []
    errors = []
    t0 = time.time()
    for i in range(0, len(designators), 40):
        chunk = designators[i:i + 40]
        for attempt in (1, 2):
            raw = mcp_client.call("check_placement", {"cmp_designators": chunk, "clearance_mils": clearance}, timeout=280)
            try:
                data = json.loads(raw)
            except ValueError:
                data = {"error": raw[:200]}
            if "error" not in data:
                break
            time.sleep(90)                     # Altium may still be finishing the timed-out batch
        if "error" in data:
            errors.append(f"{chunk[0]}..{chunk[-1]}: {data['error']}")
            continue
        missing += data.get("missing_designators", []) or []
        for v in data.get("violations", []):
            pairs.setdefault(tuple(sorted((v["a"], v["b"]))), v)
        print(f"{i + len(chunk)}/{len(designators)} parts, {len(pairs)} pairs, {time.time() - t0:.0f} s", flush=True)
    kinds = {}
    for v in pairs.values():
        kinds[v["type"]] = kinds.get(v["type"], 0) + 1
    out = {"clearance_mils": clearance, "parts": len(designators), "pairs": len(pairs), "by_type": kinds,
           "missing": missing, "errors": errors,
           "violations": [{"a": a, "b": b, **{k: v[k] for k in v if k not in ("a", "b")}} for (a, b), v in pairs.items()]}
    (P.OUT / "check_placement.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ("parts", "pairs", "by_type", "missing", "errors")}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
