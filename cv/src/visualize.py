"""Draw predictions on a copy of a frame, leaving the original unchanged."""

import cv2

# OpenCV uses blue, green, red (BGR), rather than RGB.
COLORS = {"basketball": (0, 165, 255), "hoop": (0, 220, 0)}


def draw_detections(frame, detections):
    """Orange boxes mark basketball predictions; green boxes mark hoop predictions."""
    annotated = frame.copy()
    for detection in detections:
        left, top, right, bottom = [round(value) for value in detection["bbox"]]
        label = detection["class"]
        color = COLORS[label]
        text = f"{label} motion" if detection["confidence"] is None else f"{label} {detection['confidence']:.2f}"
        cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)
        cv2.putText(annotated, text, (left, max(top - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return annotated


def draw_track(annotated, track, trail):
    """Add a cyan observed trail in place; never connect across missing frames."""
    color = (255, 255, 0)
    points = list(trail)
    for (previous_frame, previous), (current_frame, current) in zip(points, points[1:]):
        if current_frame == previous_frame + 1:
            cv2.line(annotated, tuple(round(v) for v in previous),
                     tuple(round(v) for v in current), color, 2)
    if track["center"] is not None:
        center = tuple(round(v) for v in track["center"])
        cv2.circle(annotated, center, 7, color, 2)
    label = f"Track {track['track_id']}: {track['status']}" if track["track_id"] else track["status"]
    cv2.putText(annotated, label, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
