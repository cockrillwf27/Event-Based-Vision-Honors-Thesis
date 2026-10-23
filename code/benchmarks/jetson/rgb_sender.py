"""RGB benchmark sender for the Jetson.

Captures the UC-517 (IMX477) through nvarguscamerasrc, reads the analog
clock, and ships one UDP packet per frame to the PC logger.

Run on the Jetson, after the IMX477 overlay is active and /dev/video* exists
or Argus can open sensor-id 0:

    python3 rgb_sender.py --host 192.168.1.20 --port 5005 --trial rgb-1

Pipeline latency in the packet does not need clock sync. For network latency,
start chrony on both machines first.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

from clock_reader import read_clock, seconds_error
from protocol import SENSOR_RGB, make_packet, now_ns, pack


def capture_pipeline(sensor_id: int, width: int, height: int, fps: int) -> str:
    return (
        f"nvarguscamerasrc sensor-id={sensor_id} ! "
        f"video/x-raw(memory:NVMM),width={width},height={height},framerate={fps}/1 ! "
        "nvvidconv ! video/x-raw,format=BGRx ! "
        "videoconvert ! video/x-raw,format=BGR ! "
        "appsink drop=1 max-buffers=1 sync=false"
    )


def open_log(path: Path) -> tuple[csv.writer, object]:
    new = not path.exists()
    handle = path.open("a", newline="")
    writer = csv.writer(handle)
    if new:
        writer.writerow(
            [
                "trial_id",
                "seq",
                "t_capture_ns",
                "pipeline_ms",
                "read_ms",
                "ok",
                "reading",
                "error_s",
                "confidence",
                "sensor_bytes",
                "packet_bytes",
            ]
        )
    return writer, handle


def main() -> int:
    parser = argparse.ArgumentParser(description="IMX477 clock benchmark sender")
    parser.add_argument("--host", required=True, help="PC address running receiver_gui.py")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--trial", default=None, help="trial id, default rgb-YYYYMMDD-HHMMSS")
    parser.add_argument("--sensor-id", type=int, default=0)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--hands", type=int, choices=(2, 3), default=2)
    parser.add_argument("--log", default="rgb_trial.csv")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = until Ctrl-C or power loss")
    args = parser.parse_args()

    trial_id = args.trial or "rgb-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cap = cv2.VideoCapture(capture_pipeline(args.sensor_id, args.width, args.height, args.fps), cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Argus pipeline did not open. Check the IMX477 overlay and cable.", file=sys.stderr)
        return 1

    log_path = Path(args.log)
    writer, handle = open_log(log_path)
    sensor_bytes = int(args.width * args.height * 1.5)  # NV12 size leaving the sensor path
    seq = 0
    started = time.monotonic()
    print(f"trial {trial_id} -> {args.host}:{args.port}  log {log_path}")
    print("Ctrl-C to stop. For a battery trial, let the pack die; rows are flushed each frame.")

    try:
        while args.max_frames == 0 or seq < args.max_frames:
            t_capture = now_ns()
            ok_frame, frame = cap.read()
            if not ok_frame:
                print("capture read failed", file=sys.stderr)
                time.sleep(0.05)
                continue
            reading, vis = read_clock(frame, hands=args.hands)
            t_read = now_ns()
            now = datetime.now()
            err = seconds_error(reading, now.hour % 12 or 12, now.minute, now.second)
            packet = make_packet(
                sensor=SENSOR_RGB,
                trial_id=trial_id,
                seq=seq,
                t_capture_ns=t_capture,
                t_read_done_ns=t_read,
                reading=reading.as_dict(),
                confidence=reading.confidence,
                sensor_bytes=sensor_bytes,
                ok=reading.ok,
                note=reading.note,
            )
            if err is not None:
                packet["reading"]["error_s"] = round(err, 2)
            payload = pack(packet)
            packet["packet_bytes"] = len(payload)
            sock.sendto(payload, (args.host, args.port))
            writer.writerow(
                [
                    trial_id,
                    seq,
                    t_capture,
                    f"{packet['pipeline_ms']:.2f}",
                    f"{packet['read_ms']:.2f}",
                    int(reading.ok),
                    reading.as_dict()["text"] if reading.ok else "",
                    "" if err is None else f"{err:.2f}",
                    f"{reading.confidence:.2f}",
                    sensor_bytes,
                    len(payload),
                ]
            )
            handle.flush()
            if args.preview:
                cv2.imshow("rgb benchmark", vis)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            seq += 1
            if seq % args.fps == 0:
                elapsed = time.monotonic() - started
                print(
                    f"seq {seq}  pipeline {packet['pipeline_ms']:.1f} ms  "
                    f"read {packet['read_ms']:.1f} ms  "
                    f"sensor {sensor_bytes * seq / 1e6:.1f} MB  elapsed {elapsed:.0f}s"
                )
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        cap.release()
        handle.close()
        sock.close()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
