"""Turn candidate events into a small, explicit provisional session summary."""


def build_session(analysis):
    """Never count an unknown result as a miss or silently drop it from FG%."""
    events = []
    mapping = {"possible_make": "made", "possible_miss": "missed", "unknown": "unknown"}
    for candidate in analysis["candidates"]:
        timestamp = (candidate["crossing_frame"]/analysis["fps"]
                     if "crossing_frame" in candidate else candidate["start_seconds"])
        events.append({"candidate_id": candidate["candidate_id"], "timestamp": round(timestamp, 4),
                       "result": mapping[candidate["outcome"]], "provisional": True,
                       "reason": candidate["reason"]})
    made = sum(item["result"] == "made" for item in events)
    missed = sum(item["result"] == "missed" for item in events)
    unknown = len(events)-made-missed
    return {"status": "provisional", "attempt_candidates": len(events), "makes": made,
            "misses": missed, "unknown": unknown,
            "fg_percent": round(100*made/len(events), 1) if events and not unknown else None,
            "note": "Counts are automatic estimates. Null FG means no candidates or unresolved outcomes; review footage for missed attempts.",
            "events": events}
