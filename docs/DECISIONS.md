# Decisions

- Keep one FastAPI process, one explicit worker, sqlite3 and local files. A job
  transaction commits before HTTP 202; no inference runs in an HTTP handler.
- Keep old CLIs and baseline defaults. Candidate association is experimental
  until held-out evidence justifies promotion. No Kalman/FilterPy dependency.
- Use PyAV to decode real PTS (presentation timestamps). OpenCV's frame/FPS
  estimate cannot establish constant frame rate. Reject VFR, missing/nonmonotonic
  timestamps and nonzero video start for the initial product; retain the measured
  source timestamp map. No silent normalization or audio-time shift.
- Add expo-video for actual playback/seeking. No navigation/state-management
  framework is needed for three screens. Phone settings contain a LAN API URL;
  credentials for Modal stay on the server.
- Upload raw video bytes via PUT-like POST /videos, avoiding a multipart parser
  dependency. Stream to a temporary file and remove failed uploads. Inspect
  content after size/type checks. Limit duration, resolution, frame count, FPS.
- Store automatic results independently from each immutable review revision.
  Revision comparison prevents lost edits; review completeness is a user assertion,
  never benchmark ground truth. FG% stays null until complete and resolved.
- Use optional Modal SDK only for cloud mode. Persist dispatch intent before
  spawning. A saved call ID resumes polling. Ambiguous dispatch never respawns
  automatically. No cloud calls in ordinary tests.
- Timing, accuracy and user impact are different experiments. Missing measurements
  remain null/pending; no claimed speedup or participant outcomes without evidence.
