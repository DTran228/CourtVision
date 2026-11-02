# Optional Modal experiment (not live validated)

User decision on 2026-10-30: no labeled dataset or approved cloud inputs/budget yet;
finish local code and tooling first. No deployment or paid call was performed.

SDK interfaces were inspected locally with Modal **1.6.3** and checked against
official [invocation](https://modal.com/docs/guide/function-invocation-methods),
[lifecycle](https://modal.com/docs/guide/lifecycle-functions) and
[Volume](https://modal.com/docs/guide/volumes) documentation. SDK is optional and
server-side. The pinned GPU image, driver compatibility and lifecycle persistence
still require a real pilot. Defining/importing the app is not a deployment test.

After the owner approves specific footage and a spending cap:

1. Install optional tools: `.\.venv\Scripts\python.exe -m pip install -r cloud/requirements.txt`.
2. Configure Modal authentication on the server (`python -m modal setup`). Never
   put its tokens in Expo or EXPO_PUBLIC variables.
3. Verify the pinned model from cv/models/README.md. Set `COURTVISION_GPU=T4` for
   an initial small pilot; this is a candidate accelerator, not a proven optimum.
4. Set a workspace budget/alerts in Modal. `max_containers=1`, `min_containers=0`,
   no SDK compute retries, 900-second timeout bound concurrency and duration;
   they are **not a monetary spending cap**. Idle time until scaledown can cost money.
5. From repository root deploy explicitly:
   `.\.venv\Scripts\python.exe -m modal deploy cloud/modal_app.py`.
6. Set `$env:COURTVISION_ENABLE_MODAL='1'` in the API and worker shells. Start
   both as in RUNBOOK.md. POST /jobs with `runner: "modal"`. Mobile defaults local.
7. Validate the same CFR clip on CPU and cloud; use `python -m benchmarks.parity`
   to compare provenance/events with declared timestamp tolerance. Inspect outcome
   changes, do not require bit-identical tensors. Record actual hardware/software.

Inputs go to `/jobs/<UUID>/attempt-<N>/input.mp4` in the Volume. The model is
baked into the image; one detector loads per warm container. The same pipeline
and config hashes must match the local submission. Files close before reload or
commit. SQLite remains local. Completed output is published by directory rename
and a committed manifest; retrieval verifies every file hash.

Dispatch intent commits before spawn and the returned call ID commits immediately
after. On restart a known call resumes polling without new GPU work. A crash in
between is `dispatch_ambiguous`: inspect the Modal dashboard and attempt Volume
artifacts, cancel/wait for existing work, then make an explicit new request only
after resolving cost/duplication. Automatic retry is disabled once dispatch intent
exists. A remote error is visible as a typed job failure; no blind cloud respawn.
Function results can expire; keep Volume evidence and download completed results
promptly. Expired call recovery requires manual inspection, not silent resubmission.

Batching, half precision, frame skipping and resolution changes are deferred until
live parity passes; they are separate quality experiments. No cloud speedup, cost
improvement or lifecycle reliability has been measured by mocks.
