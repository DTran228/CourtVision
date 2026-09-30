"""Conservative shot-candidate rules, using observed ball positions only.

The hoop box's top edge is a rough rim proxy. Outcomes are PROVISIONAL 2D
patterns, not confirmed baskets. Gaps beyond the configured allowance remain unknown.
"""

import math


class ShotAnalyzer:
    """Remember one near-hoop event, then pause briefly to avoid duplicates."""

    def __init__(self, fps, max_gap_seconds=0):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("FPS must be positive and finite.")
        if not math.isfinite(max_gap_seconds) or max_gap_seconds < 0:
            raise ValueError("Gap allowance must be nonnegative and finite.")
        self.max_gap = math.floor(max_gap_seconds*fps)
        self.fps = fps
        self.lowest_y = -float("inf")
        self.upward_steps = 0
        self.previous = None
        self.active = None
        self.crossing = None
        self.cooldown_until = -1
        self.next_id = 1

    def finish(self, reason, frame, outcome="unknown"):
        """Close an active candidate; also used when the input video ends."""
        if self.active is None:
            return None
        event = {**self.active, "end_frame": frame,
                 "end_seconds": round(frame / self.fps, 4),
                 "outcome": outcome, "provisional": True, "reason": reason}
        self.active = None
        self.crossing = None
        self.lowest_y = -float("inf")
        self.upward_steps = 0
        self.previous = None
        self.cooldown_until = frame + math.ceil(self.fps)
        return event

    def update(self, frame, track, detections):
        """Return (state, completed_event_or_None), once per sequential frame, including missing observations."""
        if frame <= self.cooldown_until:
            return "cooldown", None

        hoops = [item for item in detections if item["class"] == "hoop"]
        if track["status"] != "observed" or not hoops:
            if self.previous is not None and frame-self.previous["frame"] <= self.max_gap:
                return ("candidate" if self.active else "waiting"), None
            event = self.finish("Ball or hoop observation missing beyond gap allowance.", frame)
            self.previous = None
            return ("cooldown" if event else "waiting"), event

        hoop = max(hoops, key=lambda item: item["confidence"])
        left, top, right, bottom = hoop["bbox"]
        width = right - left
        if width <= 0 or bottom <= top:
            raise ValueError("Hoop box must have positive width and height.")
        x, y = track["center"]
        # Normalize by hoop width: x=0 is its middle; y=0 is its top edge.
        point = {"frame": frame, "timestamp_seconds": round(frame / self.fps, 4),
                 "track_id": track["track_id"], "ball_center": [x, y],
                 "hoop_bbox": hoop["bbox"], "source": track.get("source", "model"), "x": (x - (left + right) / 2) / width,
                 "y": (y - top) / width}
        previous = self.previous
        self.previous = point
        if previous is None:
            return "waiting", None

        old_left, old_top, old_right, _ = previous["hoop_bbox"]
        old_width = old_right - old_left
        hoop_moved = math.hypot((left + right - old_left - old_right) / 2,
                               top - old_top) > old_width * 0.5
        scale_changed = not 0.67 <= width / old_width <= 1.5
        elapsed = frame-previous["frame"]
        if (elapsed > self.max_gap+1 or elapsed <= 0 or point["track_id"] != previous["track_id"]
                or hoop_moved or scale_changed):
            event = self.finish("Track changed or hoop reference jumped.", frame)
            return ("cooldown" if event else "waiting"), event

        # Start from two observed above-hoop points, allowing only bounded gaps.
        # Image y increases DOWN, so a positive delta means descending.
        vertical_step = (point["y"]-previous["y"])/elapsed
        descending = vertical_step > 0.02
        above = -3 <= previous["y"] <= -0.15 and abs(previous["x"]) <= 2
        near = abs(point["x"]) <= 2 and -3 <= point["y"] <= 1
        if self.active is None and descending and above and near:
            self.active = {"candidate_id": self.next_id, "track_id": point["track_id"],
                           "start_frame": previous["frame"],
                           "start_seconds": previous["timestamp_seconds"],
                           "evidence": [previous, point]}
            self.next_id += 1
        if self.active is None:
            return "waiting", None

        if frame - self.active["start_frame"] > 2 * self.fps:
            return "cooldown", self.finish("Candidate timed out without clear evidence.", frame)

        self.lowest_y = max(self.lowest_y, point["y"])
        self.upward_steps = self.upward_steps+1 if vertical_step < -0.02 else 0
        if (self.crossing is not None and self.upward_steps >= 2
                and -0.05 <= self.lowest_y <= 0.5 and self.lowest_y-point["y"] >= 0.3
                and point["y"] < 0 and abs(point["x"]) <= 2):
            self.active["evidence"].append(point)
            return "cooldown", self.finish(
                "Observed upward rebound after approaching the rim proxy.", frame, "possible_miss")

        if self.crossing is None and previous["y"] < 0 <= point["y"] and descending:
            # Linear interpolation estimates where the observed segment crosses y=0.
            fraction = -previous["y"] / (point["y"] - previous["y"])
            self.crossing = previous["x"] + fraction * (point["x"] - previous["x"])
            self.active["crossing_x_in_hoop_widths"] = self.crossing
            self.active["crossing_frame"] = frame
            self.active["crossing_gap_frames"] = elapsed-1
            self.active["evidence"].extend([previous, point])
            return "candidate", None  # Require a later below-hoop observation too.

        if self.crossing is not None and point["y"] >= 0.5 and descending:
            self.active["evidence"].append(point)
            if abs(self.crossing) <= 0.5 and abs(point["x"]) <= 0.75:
                return "cooldown", self.finish(
                    "Observed descent crosses the hoop proxy and continues below it.",
                    frame, "possible_make")
            if abs(self.crossing) >= 0.75 and abs(point["x"]) >= 0.75:
                return "cooldown", self.finish(
                    "Observed descent passes outside the hoop proxy and continues below it.",
                    frame, "possible_miss")
            return "cooldown", self.finish("Crossing is ambiguous near the hoop edge.", frame)
        return "candidate", None
