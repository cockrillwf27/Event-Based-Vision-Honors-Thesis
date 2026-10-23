"""Analog clock reader for the RGB baseline.

Looks for a round face, then dark hands that pass near the center.
Angle zero is 12 o'clock, increasing clockwise. With two hands the longer
one is the minute hand. With three, longest is seconds, middle is minutes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ClockReading:
    hours: int
    minutes: int
    seconds: int
    hour_deg: float
    minute_deg: float
    second_deg: float | None
    confidence: float
    face_center: tuple[int, int]
    face_radius: int
    ok: bool
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "kind": "clock",
            "hours": self.hours,
            "minutes": self.minutes,
            "seconds": self.seconds,
            "text": f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}",
            "hour_deg": round(self.hour_deg, 2),
            "minute_deg": round(self.minute_deg, 2),
            "second_deg": None if self.second_deg is None else round(self.second_deg, 2),
            "face_center": list(self.face_center),
            "face_radius": self.face_radius,
        }

    def as_seconds(self) -> float:
        return self.hours * 3600 + self.minutes * 60 + self.seconds


def _angle_from_12(cx: float, cy: float, x: float, y: float) -> float:
    dx = x - cx
    dy = y - cy
    deg = math.degrees(math.atan2(dx, -dy))
    return deg % 360.0


def _line_near_center(x1, y1, x2, y2, cx, cy, tol: float) -> tuple[float, float, float] | None:
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 8:
        return None
    # Distance from center to the infinite line, then require the segment
    # to actually reach near the hub.
    num = abs((y2 - y1) * cx - (x2 - x1) * cy + x2 * y1 - y2 * x1)
    dist = num / length
    if dist > tol:
        return None
    d1 = math.hypot(x1 - cx, y1 - cy)
    d2 = math.hypot(x2 - cx, y2 - cy)
    if min(d1, d2) > tol * 1.6:
        return None
    tip_x, tip_y = (x1, y1) if d1 > d2 else (x2, y2)
    return length, _angle_from_12(cx, cy, tip_x, tip_y), max(d1, d2)


def read_clock(frame: np.ndarray, hands: int = 2) -> tuple[ClockReading, np.ndarray]:
    vis = frame.copy()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 1.4)
    h, w = gray.shape
    min_r = int(min(h, w) * 0.12)
    max_r = int(min(h, w) * 0.48)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(h, w) // 2,
        param1=120,
        param2=40,
        minRadius=min_r,
        maxRadius=max_r,
    )
    if circles is None:
        reading = ClockReading(0, 0, 0, 0, 0, None, 0.0, (w // 2, h // 2), 0, False, "no face")
        return reading, vis

    circles = np.round(circles[0]).astype(int)
    cx, cy, radius = max(circles, key=lambda c: c[2])
    cv2.circle(vis, (cx, cy), radius, (0, 220, 0), 2)
    cv2.circle(vis, (cx, cy), 3, (0, 220, 0), -1)

    mask = np.zeros_like(gray)
    cv2.circle(mask, (cx, cy), int(radius * 0.92), 255, -1)
    edges = cv2.Canny(gray, 50, 140)
    edges = cv2.bitwise_and(edges, mask)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=int(radius * 0.25),
        maxLineGap=12,
    )
    hands_found: list[tuple[float, float]] = []
    if lines is not None:
        tol = max(8.0, radius * 0.08)
        for x1, y1, x2, y2 in lines[:, 0]:
            hit = _line_near_center(x1, y1, x2, y2, cx, cy, tol)
            if hit is None:
                continue
            length, ang, reach = hit
            if reach < radius * 0.28:
                continue
            hands_found.append((length, ang))
            cv2.line(vis, (x1, y1), (x2, y2), (0, 140, 255), 1)

    if len(hands_found) < 2:
        reading = ClockReading(0, 0, 0, 0, 0, None, 0.15, (cx, cy), radius, False, "hands not found")
        cv2.putText(vis, reading.note, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return reading, vis

    # Collapse lines that are the same hand (within 8 degrees), keep the longest.
    hands_found.sort(key=lambda item: item[0], reverse=True)
    unique: list[tuple[float, float]] = []
    for length, ang in hands_found:
        if any(min(abs(ang - a) % 360, 360 - abs(ang - a) % 360) < 8 for _, a in unique):
            continue
        unique.append((length, ang))
        if len(unique) == max(2, hands):
            break

    if len(unique) < 2:
        reading = ClockReading(0, 0, 0, 0, 0, None, 0.2, (cx, cy), radius, False, "only one hand")
        return reading, vis

    unique.sort(key=lambda item: item[0], reverse=True)
    second_deg = None
    if hands >= 3 and len(unique) >= 3:
        second_deg = unique[0][1]
        minute_deg = unique[1][1]
        hour_deg = unique[2][1]
    else:
        minute_deg = unique[0][1]
        hour_deg = unique[1][1]

    minutes = int(round(minute_deg / 6.0)) % 60
    seconds = 0 if second_deg is None else int(round(second_deg / 6.0)) % 60
    hour_float = (hour_deg / 30.0) % 12
    # Minute hand pulls the hour hand; undo that so 1:30 is not read as 2.
    hours = int(round(hour_float - minutes / 60.0)) % 12
    if hours == 0:
        hours = 12

    confidence = 0.55 + 0.15 * min(len(unique), 3)
    reading = ClockReading(
        hours, minutes, seconds, hour_deg, minute_deg, second_deg, confidence, (cx, cy), int(radius), True
    )
    cv2.putText(
        vis,
        reading.as_dict()["text"],
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 220, 0),
        2,
    )
    return reading, vis


def seconds_error(reading: ClockReading, truth_h: int, truth_m: int, truth_s: int) -> float | None:
    if not reading.ok:
        return None
    truth = truth_h % 12 * 3600 + truth_m * 60 + truth_s
    got = (reading.hours % 12) * 3600 + reading.minutes * 60 + reading.seconds
    diff = abs(got - truth)
    return float(min(diff, 12 * 3600 - diff))
