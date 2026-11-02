# CourtVision progress

## C0 — audit and preserve

- Read the supplied guideline, chat AGENTS.md and current source before edits.
- Preserved the four pre-existing user changes and saved experiment artifacts.
- Existing CV tests: 58 passed (outside sandbox; sandbox temp permissions failed).
- Mobile baseline: `cd mobile; npm run typecheck` passed.
- Added current-state comparison and architecture decisions.
- Next: inventory real timestamps/hashes, then C1 evaluation before tuning.

Acceptance gates involving real labels, phone use, paid cloud or participants
remain open until explicitly verified. See later entries for exact commands.

## C1 — evaluation contract

- Added versioned JSONL validation, recording-session split isolation, fixed
  0.15-second matching tolerance, one-to-one matching, confusion, unknown rate,
  count error, timestamp error and reviewed-negative FP/min.
- `python -m tools.inventory`: recorded 4 local inputs, model/source hashes,
  package versions and real PTS. Original files were read only.
- `python -m unittest cv.tests.test_dataset -v`: **5 passed**.
- Human footage provenance and held-out labels are missing. No accuracy claim.
- Understand: splits must group original recordings; unknowns stay in denominators.
- Next: experimental association on saved detections, baseline stays default.

## C2 — experimental association; quality gate open

- Added bounded candidate tracks, one-to-one motion/size matching, conservative
  identity resets and observed/predicted separation. Kept baseline default.
- `python -m unittest cv.tests.test_candidate_tracker cv.tests.test_dataset -v`:
  **11 passed**.
- Initial ablation command used an inspection folder without summary.json and
  failed. Corrected input to `cv/output/m3-threepointshootout25/model-detections`.
- `python -m tools.ablate --detections cv/output/m3-threepointshootout25/model-detections --output docs/evidence/association-development.json`: passed.
  Baseline 1/2/5 vs candidate 2/1/15 possible make/miss/unknown. Not an accuracy
  gain; candidate remains experimental. See ASSOCIATION.md for limitations.
- PTS inventory found threemade/threemiss are VFR; 20secplay/shootout are CFR.
  Product rejects the VFR originals; historical CLI remains available.
- Next: complete local durable jobs, review and mobile integration.

## C3 — local product implementation

- Added bounded streamed uploads with full decode/PTS checks, durable SQLite job
  acceptance and atomic claims, explicit worker OS lock, attempt isolation,
  interrupted recovery, bounded transient retries and idempotency conflicts.
- Added immutable automatic results, review revision snapshots, manual add/edit/
  remove, completeness-aware summaries, history and HTTP range media seeking.
- Expo now uploads, polls with backoff, resumes recent jobs, plays/seeks candidates,
  edits/persists reviews and compares completed session percentages.
- Added PyAV 16.1.0 and SDK-compatible expo-video ~57.0.5. Install sandbox DNS
  failures were rerun with approval. No state-management/multipart/queue dependency.
- First `python -m unittest tests.test_product -v`: 8 pass, 1 failure, 1 error.
  Fixed Windows lock conflict handling and a test relying on sorted review order.
- Rerun: **10 passed** in 2.934 s, including real synthetic-video upload/decode,
  worker, range request, interrupted stream, restart/retry, revision conflicts,
  source tampering, and review add/delete/unknown counts. No real model in tests.
- `cd mobile; npm run typecheck`: initial SDK fullscreen prop mismatch fixed
  against installed types; rerun passed.
- Starlette warns that its httpx TestClient adapter is deprecated; it currently
  works. npm install reported dependency advisories; see final audit entry.
- Phone walk-through remains unverified; local real-model smoke is next.

## C4 — optional Modal adapter; live gate open

- Installed optional SDK 1.6.3 and inspected actual API signatures; checked official
  invocation/lifecycle/Volume docs. Added pinned image/deployment definition,
  scale-to-zero with one container, warm model reuse and unique attempt paths.
- Dispatch intent/call ID are durable. Known calls resume; ambiguous dispatch cannot
  auto-retry. Downloads are confined and verified against completion manifests.
- `python -m unittest tests.test_cloud -v`: **4 passed**, all with fake transport.
- `python -c "import cloud.modal_app"`: passed locally, no deployment invoked.
- User confirmed local/tooling first, without cloud inputs/budget or human labels.
  Live CPU/Modal parity, cost, container lifecycle and SDK network behavior remain
  unverified. No frame batching/half precision/skipping before parity.
- Understand: a saved call ID resumes work; a mock is not evidence of GPU speed.

## C5 — evidence tooling; controlled benchmark and study gates open

- Added frozen manifests, bounded explicit-paid benchmark CLI, raw append-only
  request/job/run/result JSON, failure retention, summary JSON/CSV, parity checker,
  sample-aware statistics and formative user-study protocol. No invented impact.
- `python -m benchmarks.manifest --videos cv/sample_videos/20secplay.mp4 cv/sample_videos/threepointshootout25.mkv --output data/benchmark-pilot.json`: passed (2 eligible inputs; fewer than 5).
- `python -m benchmarks.run --manifest data/benchmark-pilot.json --runner local --pilot --dry-run --output benchmarks/runs/pilot`: passed, 2 planned runs, no upload.
- Repeated saved-detection ablation separating association-only/time-aware settings
  gave the same candidate counts (2/1/15); baseline remains 1/2/5 and the default.
- Full benchmark needs >=5 varied clips and repeated cold/warm runs. No held-out
  human labels, GPU measurements, billing export or participants are available.

## Integration verification (2026-10-31)

- `python -m tools.demo --synthetic --output data/demo-synthetic`: plumbing passed;
  first evaluator invocation rejected the hardcoded floating-point interval end.
  Fixed fixture to use the measured duration and reran into demo-synthetic-v2.
- Evaluator CLI on demo-synthetic-v2: passed, 1 scripted attempt matched. This is
  synthetic behavior verification, **not basketball accuracy**.
- Initial real-demo attempt in sandbox stalled before database initialization and
  was stopped. Rerun outside sandbox succeeded; no result was claimed from the stall.
- Real pinned E-BARD CPU smoke through upload/job/worker/review:
  - 20secplay: 1,408 frames, 0 candidates; pipeline 99.083 s, local in-process
    upload-to-review-ready 107.216 s; review revision 1 saved, incomplete.
  - shootout: 3,772 frames, 8 candidates (1/2/5 made/missed/unknown estimates);
    pipeline 217.534 s, local in-process upload-to-review-ready 234.829 s;
    review revision 1 saved, incomplete.
  These are single uncontrolled smoke runs, not comparable GPU benchmarks or phone
  latency. See docs/evidence for copied summaries and local data directories for
  full logs/results. Historical experiments were not overwritten.
- `python -m tools.checks`: **87 passed** in 6.639 s before the final benchmark
  failure-denominator regression was added; final rerun recorded below.
- `python -m pip check`: passed. Python compileall and git diff --check passed.
- iOS export first failed writing Hermes bytecode to sandbox Temp (permission
  denied); rerun outside sandbox is recorded below. Typecheck passed.
- npm audit initially reported 18 advisories including one critical. Updated only
  shell-quote, node-forge and source-map-js within allowed ranges; now 15 remain
  (2 low, 11 moderate, 2 high), no critical. Remaining Expo-chain remediation
  proposes a major SDK upgrade, deferred to a separate compatibility change.

## Final verification and handoff

- `python -m tools.checks --report docs/evidence/final-checks.json`: **89 passed**,
  0 failures/errors/skips, unittest elapsed 8.726 s. Includes the original 58 tests,
  dataset matching/split guards, candidate association/time-aware 30/60 FPS,
  product persistence/failures and offline Modal/benchmark checks.
- Final `cd mobile; npm run typecheck`: passed.
- `npx expo export --platform ios --output-dir ../data/mobile-ios-export-final`:
  passed, 608 modules, Hermes bundle index-e6db650237b7d69f1541cb1b18af5fca.hbc.
  This is a JS/Hermes export, not a native iPhone installation/device test.
- `python -m tools.http_smoke --output data/http-smoke`: passed. Separate loopback
  API/worker processes, real model on tiny synthetic video, saved revision 1 and
  verified the review survived a real API restart. Child processes were stopped.
- `python -m benchmarks.summarize data/http-smoke/runs --output data/http-smoke-summary`:
  passed, 1 raw run/1 group, p95 suppressed. This is plumbing evidence, not a
  controlled basketball performance experiment.
- `python -m tools.collect_evidence`: copied real smoke summaries/results/manifests,
  loopback JSON/CSV and machine/package metadata without copying private videos.
- Hash comparison against C0 inventory: cv/M3.md and all 10 original experiment
  files unchanged, including both user-provided untracked experiment files.
- `npm audit --json` raw report saved to docs/evidence/npm-audit.json; expected
  exit 1 because 15 advisories remain. It is not counted as a passing security scan.

| Milestone | Delivered | Acceptance still requiring external evidence |
| --- | --- | --- |
| C0 | Repository comparison, source/input/dependency inventory, existing regressions preserved | None for local audit |
| C1 | Dataset contract/evaluator, synthetic regression reproduction | Human labels, provenance-confirmed session-held-out dataset |
| C2 | Experimental candidate association, saved-input ablations, regression checks | Measured accuracy/coverage improvement; baseline remains shipped default |
| C3 | Local upload/job/worker/results/review/history, real-model and process smoke | Two-clip phone walk-through and native playback/upload validation |
| C4 | Optional adapter/deployment definition, offline integration checks and runbook | Approved footage/budget/credentials, deployed GPU parity/lifecycle/cost |
| C5 | Frozen-manifest runner, raw evidence, summary/parity tooling, study/claim docs | Five varied eligible clips, repeated cold/warm CPU/GPU runs, actual participants |

Start with RUNBOOK.md for commands and the review workflow. DATASET.md,
ASSOCIATION.md, MODAL.md, BENCHMARKS.md and RESUME_CLAIMS.md explain the open gates.
Do not describe these external gates as passed or turn old targets into results.
