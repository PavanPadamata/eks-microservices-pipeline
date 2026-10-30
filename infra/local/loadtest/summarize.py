"""Print latency and HPA scaling timings for one run directory (see run.sh)."""
import csv
import json
import sys

out, load_s = sys.argv[1], int(sys.argv[2])

metrics = json.load(open(f"{out}/k6-summary.json"))["metrics"]
val = lambda name: metrics[name].get("values", metrics[name])  # handles both summary-export formats
dur, reqs, failed = val("http_req_duration"), val("http_reqs"), val("http_req_failed")
print("\n== latency (client side, through the ingress)")
print(f"requests: {reqs['count']:.0f}  rate: {reqs['rate']:.1f}/s  failed: {100 * failed.get('rate', failed.get('value', 0)):.2f}%")
print("  ".join(f"{k}={dur[k]:.1f}ms" for k in ("avg", "med", "p(90)", "p(95)", "p(99)", "max")))

rows = [{k: (int(v) if v else None) for k, v in r.items()} for r in csv.DictReader(open(f"{out}/hpa-timeline.csv"))]
print("\n== HPA timeline (sampled every ~5 s; t=0 is when recording started, within ~2 s of load start)")
for svc in ("api", "worker"):
    cur = [(r["t_s"], r[f"{svc}_current"]) for r in rows if r[f"{svc}_current"] is not None]
    des = [(r["t_s"], r[f"{svc}_desired"]) for r in rows if r[f"{svc}_desired"] is not None]
    cpu = [r[f"{svc}_cpu_pct"] for r in rows if r[f"{svc}_cpu_pct"] is not None]
    start = cur[0][1]
    peak = max(c for _, c in cur)
    first = lambda pairs, cond: next((t for t, v in pairs if cond(v)), None)
    after = [(t, c) for t, c in cur if t > load_s]
    fmt = lambda t: "not observed" if t is None else f"t={t}s"
    print(f"{svc}: start={start} peak={peak} peak_cpu={max(cpu) if cpu else 'n/a'}%")
    print(f"  first desired > start : {fmt(first(des, lambda v: v > start))}")
    print(f"  first current > start : {fmt(first(cur, lambda v: v > start))}")
    print(f"  reached peak          : {fmt(first(cur, lambda v: v == peak))}")
    print(f"  first scale-down      : {fmt(first(after, lambda v: v < peak))}  (load ended at t={load_s}s)")
    print(f"  back to start         : {fmt(first(after, lambda v: v <= start))}")
