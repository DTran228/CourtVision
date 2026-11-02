# Claim → implementation → evidence

| Potential claim | Implementation | Evidence / current limit | Status |
| --- | --- | --- | --- |
| Built a React Native video review workflow with Python/OpenCV | Expo upload/status/playback/review/history; FastAPI/SQLite worker; callable pipeline | Typecheck, offline tests and real local smoke; phone walk-through pending | Implemented locally; device validation pending |
| Timestamped automatic shot estimates with preserved uncertainty | CFR/PTS gate; observed evidence; immutable automatic output; separate reviews | Result schema, old/new regression tests, demo artifacts | Supported as estimate workflow; no broad accuracy claim |
| Durable background analysis and corrections | SQLite queue/attempts, restart reconciliation, review revisions | Product integration tests including interruption, retry isolation, conflicts | Supported locally |
| Improved tracking accuracy / 25% fewer interruptions | Experimental candidate association | Same saved detections increase unknowns; no held-out labels | NOT supported; baseline retained |
| Trained a basketball model | Uses unchanged third-party E-BARD weights | cv/models/README.md provenance/hash | NOT supported; never claim trained |
| Used Kalman/FilterPy tracker | Constant-velocity greedy association; no Kalman added | tracker.py and candidate_tracker.py | NOT supported |
| Reduced turnaround from A to B with Modal | Optional GPU adapter and reproducible harness | Offline cloud mocks; no paid run, CPU/GPU pair or cost measurement | NOT supported yet |
| Improved FG/outcome accuracy | Evaluation tooling with explicit denominators | No session-held-out human dataset | NOT supported yet |
| Saved players/coaches X% review time | User study protocol only | No participants or timings | NOT supported yet |

Safe wording today: “Implemented a local basketball video review workflow with
React Native, FastAPI, SQLite and a pretrained detector, preserving automatic
estimates and user corrections separately.” Qualify device/cloud validation.
Only publish measured improvements after raw evidence reproduces the claim.
