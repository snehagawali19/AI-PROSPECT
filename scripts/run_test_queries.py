"""Runs the 5 mandatory queries + 1 unseen query against a running API → samples/ + samples/RESULTS.md.

Usage:  python -m scripts.run_test_queries [base_url]        (default http://localhost:4000)
Only needs `httpx` on the host. Output folder can be changed with SAMPLES_DIR.
"""
import json, os, pathlib, sys
import httpx

QUERIES = ["Football lovers in Washington DC in USA", "Digital marketing agency owners in New York USA",
           "Startup founders in London UK", "Cricket lovers in Ahmedabad India", "Restaurant owners in Dubai UAE",
           "Yoga instructors in Bangalore India"]          # 6th, unseen: proves nothing is hard-coded

def main(base: str) -> int:
    out = pathlib.Path(os.environ.get("SAMPLES_DIR", "samples"))
    out.mkdir(exist_ok=True)
    rows = ["| # | Query | Prospects | Platforms (links) | With email/phone/WhatsApp | SERP calls | Latency (s) |",
            "|---|---|---|---|---|---|---|"]
    for n, q in enumerate(QUERIES, 1):
        try:
            r = httpx.post(f"{base}/prospect-discovery", params={"include_evidence": "true"},
                           json={"query": q}, timeout=120)
        except httpx.HTTPError as e:
            print(f"Could not reach {base}: {type(e).__name__}. Is the API running?")
            return 1
        body = r.json()
        (out / f"q{n}_evidence.json").write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
        plain = {k: body.get(k) for k in ("success", "query", "total_prospects")}
        plain["prospects"] = [{k: v for k, v in p.items() if k != "evidence"} for p in body.get("prospects", [])]
        (out / f"q{n}.json").write_text(json.dumps(plain, indent=2, ensure_ascii=False), encoding="utf-8")
        counts: dict[str, int] = {}
        for p in body.get("prospects", []):
            for link in p["social_link"]:
                counts[link["platform"]] = counts.get(link["platform"], 0) + 1
        contact = sum(1 for p in body.get("prospects", [])
                      if any(l["platform"] in ("Email", "Phone", "WhatsApp") for l in p["social_link"]))
        meta = body.get("meta", {})
        total = body.get("total_prospects", f"ERR {r.status_code}")
        rows.append(f"| {n} | {q} | {total} | {', '.join(f'{k} {v}' for k, v in sorted(counts.items()))} | "
                    f"{contact} | {meta.get('serp_calls', '-')} | {meta.get('latency_ms', 0) / 1000:.1f} |")
    (out / "RESULTS.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("\n".join(rows))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4000"))
