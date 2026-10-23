"""Shared benchmark packet for the RGB and event-camera paths.

Both senders emit this dict as one UDP datagram. The PC stamps arrival time.
Pipeline latency does not need clock sync. Network and end-to-end latency do:
run chrony on the Jetson and the PC before a recorded trial.
"""

from __future__ import annotations

import json
import time
from typing import Any


SENSOR_RGB = "imx477"
SENSOR_EBV = "triton2"


def now_ns() -> int:
    return time.time_ns()


def pack(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def unpack(data: bytes) -> dict[str, Any]:
    return json.loads(data.decode("utf-8"))


def make_packet(
    *,
    sensor: str,
    trial_id: str,
    seq: int,
    t_capture_ns: int,
    t_read_done_ns: int,
    reading: dict[str, Any],
    confidence: float,
    sensor_bytes: int,
    ok: bool,
    note: str = "",
) -> dict[str, Any]:
    t_send_ns = now_ns()
    packet = {
        "v": 1,
        "sensor": sensor,
        "trial_id": trial_id,
        "seq": seq,
        "t_capture_ns": t_capture_ns,
        "t_read_done_ns": t_read_done_ns,
        "t_send_ns": t_send_ns,
        "pipeline_ms": (t_send_ns - t_capture_ns) / 1e6,
        "read_ms": (t_read_done_ns - t_capture_ns) / 1e6,
        "reading": reading,
        "confidence": round(float(confidence), 4),
        "sensor_bytes": int(sensor_bytes),
        "ok": bool(ok),
        "note": note,
    }
    raw = pack(packet)
    packet["packet_bytes"] = len(raw)
    return packet
