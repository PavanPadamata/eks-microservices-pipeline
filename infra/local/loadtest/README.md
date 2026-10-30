# Load test and HPA measurements (kind)

Everything marked `TODO(measure)` below is intentionally empty. Fill it in from your own runs; do not
copy numbers from anywhere else. Record the conditions next to the numbers, because they change the result.

## Conditions to record

| Item | How to get it | Value |
|---|---|---|
| Date | `date -I` | TODO(measure) |
| Git commit deployed | `git rev-parse --short HEAD` | TODO(measure) |
| Machine (CPU cores / RAM) | `nproc; free -h` | TODO(measure) |
| What else was running (Jenkins, monitoring stack?) | note it | TODO(measure) |
| Replica bounds (`values-local.yaml`) | min 1, max 5 per service; CPU target 70% of request | known from the chart |

## Run

Start from a deployed, idle cluster (`make local-up && make deploy`). Both targets wait until each HPA is back
at its minimum replicas, so every run starts from the same state.

```bash
make load-baseline   # 60 s at 2 req/s: latency before load
make load-test       # 240 s at 40 req/s, then 180 s of recording to see scale-down
make load-test LOAD_RATE=60 LOAD_DURATION_S=300   # override the knobs
```

Each run writes `infra/local/loadtest/results/<label>/` (gitignored): `k6-summary.json`, `k6-stdout.txt` and
`hpa-timeline.csv` (HPA replicas and CPU % every ~5 s), then prints a summary. Watch the Grafana dashboard
(`make grafana`) at the same time and take your screenshots from that run.

How the load works: the api calls the worker for every request, and the worker burns `WORK_MS` (20 ms) of CPU
per request. So about 40 req/s needs about 0.8 CPU cores of worker capacity, while one worker pod requests only
0.1 core, which is why the HPA scales out.

## What to read from the output

| Metric | Where | Value |
|---|---|---|
| p95 latency before load (2 req/s) | `make load-baseline` -> `p(95)` | TODO(measure) |
| p95 latency during load (40 req/s) | `make load-test` -> `p(95)` | TODO(measure) |
| p99 latency during load | `make load-test` -> `p(99)` | TODO(measure) |
| Request failure rate during load | `make load-test` -> `failed` | TODO(measure) |
| api: time until HPA first wants more replicas | summary: `first desired > start` | TODO(measure) |
| api: time until a new replica exists | summary: `first current > start` | TODO(measure) |
| api: peak replicas / peak CPU % | summary: `peak`, `peak_cpu` | TODO(measure) |
| worker: time until HPA first wants more replicas | summary: `first desired > start` | TODO(measure) |
| worker: time until a new replica exists | summary: `first current > start` | TODO(measure) |
| worker: peak replicas / peak CPU % | summary: `peak`, `peak_cpu` | TODO(measure) |
| Time until scale-down starts after load ends | summary: `first scale-down` minus the load duration | TODO(measure) |

Notes on reading it:

- All times are seconds since the recorder started, which is within about 2 s of the load starting. The recorder
  samples every ~5 s, so treat each time as accurate to about +/-5 s.
- Latency is measured by k6 on your machine through the ingress, so it includes Traefik.
- `peak_cpu` is the HPA's own utilisation figure (percent of the CPU *request*), so it can exceed 100%. It is
  capped by the CPU limit: a worker pod with a 500m limit and a 100m request tops out at 500%.
- If a service reaches its `maxReplicas` (5) while still above the CPU target, the HPA cannot scale further. Say so
  when you write up the result instead of presenting that run as a clean scale-out.
- Run each scenario more than once and report the spread, not one lucky run.

## Pipeline and deploy timings (also `TODO(measure)`)

| Metric | Command | Value |
|---|---|---|
| Jenkins build duration, warm Docker cache | `curl -gs -u admin:<password> 'localhost:8081/job/eks-microservices-pipeline/lastBuild/api/json?tree=duration,result'` (milliseconds) | TODO(measure) |
| Per-stage durations | Jenkins UI Stage View, or `curl -s -u admin:<password> localhost:8081/job/eks-microservices-pipeline/lastBuild/wfapi/describe` | TODO(measure) |
| Rollout time of a real change | `time helm --kube-context kind-eks-ms upgrade --install microservices charts/microservices -n microservices -f charts/microservices/values-local.yaml --set services.api.image.tag=local --set services.worker.image.tag=local --set services.worker.env.WORK_MS=21 --wait --timeout 3m` | TODO(measure) |
| `make local-up` from nothing | `make local-down; time make local-up` | TODO(measure) |

The `WORK_MS=21` override changes the ConfigMap checksum so pods really roll; a no-change `helm upgrade` finishes
instantly and measures nothing. The admin password is in your local `.env` (`JENKINS_ADMIN_PASSWORD`).
