# Performance evidence and experiment protocol

No CPU-to-Modal speedup, held-out accuracy gain or user-impact percentage is
established. Historical 290.85 seconds includes a model-stage script's overhead;
it is not a comparable kernel-only baseline. Real local smoke evidence is separate
from synthetic tests and from a controlled benchmark.

Use a frozen manifest of >=5 varied CFR clips (15–120 s) with hashes, resolution,
FPS and identical settings. Four videos currently exist, two are VFR; the full
benchmark dataset is not ready. `--pilot` explicitly permits fewer clips. Changing
resolution, confidence, weights, tracking, frame skipping or precision creates a
different quality experiment. No result cache is used by the runner.

From root, prepare a manifest without uploading:
```powershell
.\.venv\Scripts\python.exe -m benchmarks.manifest --videos cv/sample_videos/20secplay.mp4 cv/sample_videos/threepointshootout25.mkv --output data/benchmark-pilot.json
.\.venv\Scripts\python.exe -m benchmarks.run --manifest data/benchmark-pilot.json --runner local --pilot --dry-run --output benchmarks/runs/pilot
```

With API and worker already running, an actual CPU pilot:
```powershell
.\.venv\Scripts\python.exe -m benchmarks.run --manifest data/benchmark-pilot.json --runner local --pilot --repeats 1 --output benchmarks/runs/cpu-pilot-01
```

**Paid cloud command, only after the owner supplies approved footage and cap:**
```powershell
.\.venv\Scripts\python.exe -m benchmarks.run --manifest data/benchmark-frozen.json --runner modal --paid --budget-usd 5 --repeats 3 --temperature cold --output benchmarks/runs/gpu-cold-01
```
The example $5 must be replaced by the actual approved cap. The argument records
that cap; it cannot enforce provider billing. Set provider budget alerts, observe
cost after each small pilot, and stop when the cap would be exceeded. No command
above was executed against paid Modal during this implementation.

Run initial >=3 cold and >=5 warm repeats per clip after parity. Cold requires
actual fresh container observations, not a command-line label or arbitrary sleep.
Cloud runtime logs container ID and first-request flag; summaries group observed
temperature separately. CPU requested temperature remains unclassified unless a
separate process-restart protocol is documented. Failed cold/warm runs remain in
raw files; failures without observed temperature form an unclassified group.

The runner measures client upload **plus server validation**, job queue wait,
pipeline decode/inference/tracking, cloud transfer/retrieval and client total.
CUDA inference synchronizes before/after timing. Cloud cold initialization is
reported separately. Queue vs startup isolation requires provider telemetry and is
left null rather than guessed. No annotated video is encoded in the product;
encode time is null/not applicable. Client totals include polling delay. A desktop
HTTP client is not the phone; instrument the phone separately for mobile latency.

Raw request/job/run/result JSON is append-only. Interrupted polling preserves the
job ID; resume it rather than submitting new GPU work. `plan.json` pins manifest
hash and configuration. `*-run.json` retains failed runs and error details.

```powershell
.\.venv\Scripts\python.exe -m benchmarks.summarize benchmarks/runs/cpu-pilot-01 benchmarks/runs/gpu-cold-01 --output data/benchmark-summary-01
.\.venv\Scripts\python.exe -m benchmarks.parity data/cpu/result.json data/gpu/result.json --tolerance 0.05 --output data/parity-01.json
```

Summaries preserve per-video/config/model/code/hardware/temperature groups, sample
counts, median, min/max and error rate. P95 is suppressed below 100 successful
runs/group; larger groups include an exploratory bootstrap interval and assumptions.
No automatic speedup claim is printed: first check held-out quality and compare
matching strata, then compute CPU/GPU medians for both compute and user wait.
Use actual billing exports for cost (or label rate×time clearly as an estimate).
Raw stages keep missing measurements null; no zero-filled cloud metrics.
