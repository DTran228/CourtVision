# Repository audit — 2026-10-30

The attached brief was compared with the actual working tree before edits.
The user's AGENTS.md instructions were supplied in chat; no additional on-disk
AGENTS.md was found in this checkout or its parent directories.

| Milestone | Existing | Missing / adjustment |
| --- | --- | --- |
| C0 | CLI, model provenance, 58 unittest regressions, Expo picker | Executable audit, reliable presentation timestamps, current dependency inventory |
| C1 | Provisional window evaluator and AI-reviewed development examples | Versioned labels, recording-session split guard, complete metric denominators |
| C2 | Nearest-neighbor single-ball baseline, opt-in color recovery | Bounded multi-candidate motion association and same-input comparison |
| C3 | FastAPI health, independent Expo/CV | Upload, SQLite jobs, worker, review revisions, media, history |
| C4 | CPU-only YOLO wrapper | Device setting, optional Modal adapter, restart-safe dispatch, runbook |
| C5 | Historical development experiments | Append-only benchmark harness, raw timing, claim matrix, human study protocol |

Preserved user work at entry: modified README.md and cv/M3.md; untracked
cv/experiments/m3-threepointshootout25.md and threepointshootout25-review.json.
Existing experiments and saved detections are inputs only, never overwritten.
Historical resume targets are not measured results.

Initial checks: `python -m unittest discover -s cv/tests -v`: sandbox temporary
directory permission errors, then **58 passed** outside sandbox in 0.953 s.
`npm run typecheck` in mobile: passed. Python packages, input hashes and media
timing inspection are recorded in `docs/evidence/initial-inventory.json`.
Four local videos and E-BARD weights exist. No ffmpeg/ffprobe executable on PATH.

Current labels are provisional AI development reviews, not a held-out human
dataset. Phone interaction, participant study and paid GPU execution require
external verification. Local work can proceed independently.
