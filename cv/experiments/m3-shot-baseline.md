# M3 baseline: shot candidates from saved tracks

Date: September 28, 2026. Rule implementation is working; real-footage shot
recognition is not yet demonstrated. No confidence thresholds or weights changed.

## Runs

| Clip | Frames analyzed | Track segments | Possible make | Possible miss | Unknown |
| --- | --- | --- | --- | --- | --- |
| 20secplay | 1,408 | 22 | 0 | 0 | 0 |
| threemade | 159 | 4 | 0 | 0 | 0 |
| threemiss | 178 | 10 | 0 | 0 | 0 |

All three commands completed, producing one state record per input frame and a
completed `shots.json` and `review.md`. Zero events means the starting rules were
not met; it does not establish that these videos contain no shots. Clip names
were not used as ground-truth labels or as inputs to the outcome logic.

## Diagnostic finding

The short clips have zero selected ball observations inside the candidate's
above-hoop starting region. The longer clip has 12 such observations (frames
1330-1334, 1337-1338, 1341-1345), but none start a candidate under the complete
continuity/motion rules. The earlier M2 review also marked frame 1333's basketball
prediction as uncertain, so these positions cannot be assumed to be the real ball.

This limits what the shot layer can infer from the current tracks. Broadening
thresholds just to get an event would not establish better recognition.

## Verification

The total suite has 33 passing tests: 16 prior evaluation/tracking tests, 12 shot
rule tests, and 5 full-command tests using synthetic logs. The latter includes a
complete possible-make event and checks that malformed alignment is rejected.
Python type checking passes. These checks verify code behavior, not shot accuracy.

## Outputs and next step

Local results live in `cv/output/<clip>-shots/` and tracking videos in
`cv/output/<clip>-tracking/`. Generated outputs remain ignored by Git.

Follow [the shot lesson](../SHOTS.md) for the precise rules and their limitations.
Review a known shot's visibility, rim location, and track gaps against the original
footage. Use the planned representative clip to validate detections and the
tracking/shot assumptions. M2 validation is still deferred; M3 is not complete.

Follow-up: [reviewed attempts and crop experiment](m3-reviewed-attempts.md) now
compares the baseline with two provisional visual labels and locates the missing
ball observations upstream of the shot rules.
