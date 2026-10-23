"""PC-side benchmark logger and GUI.

Listens for UDP packets from rgb_sender.py (and later the Triton2 sender).
Shows the latest reading, pipeline latency, network latency, end-to-end
latency, and bytes. Writes a CSV that survives if you close the window.

    python3 receiver_gui.py --port 5005

Network and end-to-end numbers are only meaningful if the Jetson and this
PC are synced (chrony). Pipeline latency is computed on the Jetson and does
not need that.
"""

from __future__ import annotations

import argparse
import csv
import socket
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

from protocol import now_ns, unpack


class App:
    def __init__(self, port: int, log_path: Path) -> None:
        self.port = port
        self.log_path = log_path
        self.samples: deque[dict] = deque(maxlen=300)
        self.lock = threading.Lock()
        self.running = True
        self.bytes_in = 0
        self.count = 0
        self.started = time.monotonic()

        new = not log_path.exists()
        self.log_handle = log_path.open("a", newline="")
        self.writer = csv.writer(self.log_handle)
        if new:
            self.writer.writerow(
                [
                    "recv_iso",
                    "sensor",
                    "trial_id",
                    "seq",
                    "reading",
                    "ok",
                    "pipeline_ms",
                    "network_ms",
                    "e2e_ms",
                    "error_s",
                    "sensor_bytes",
                    "packet_bytes",
                    "confidence",
                ]
            )

        self.root = tk.Tk()
        self.root.title("Gauge benchmark")
        self.root.geometry("720x460")
        self.labels = {}
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)
        rows = [
            ("sensor", "Sensor"),
            ("trial", "Trial"),
            ("reading", "Reading"),
            ("error", "Clock error"),
            ("pipeline", "Pipeline latency"),
            ("network", "Network latency"),
            ("e2e", "End-to-end latency"),
            ("volume", "Data volume"),
            ("rate", "Packet rate"),
            ("status", "Status"),
        ]
        for i, (key, title) in enumerate(rows):
            ttk.Label(frame, text=title, width=22).grid(row=i, column=0, sticky="w", pady=4)
            var = tk.StringVar(value="—")
            ttk.Label(frame, textvariable=var, font=("TkDefaultFont", 14)).grid(row=i, column=1, sticky="w")
            self.labels[key] = var
        ttk.Label(
            frame,
            text="Battery trials: leave this open. Duration is in the CSV recv times.\n"
            "Sync clocks before trusting network / end-to-end latency.",
        ).grid(row=len(rows), column=0, columnspan=2, sticky="w", pady=12)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", port))
        self.sock.settimeout(0.5)
        self.thread = threading.Thread(target=self._recv, daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(200, self._refresh)

    def _recv(self) -> None:
        while self.running:
            try:
                data, _addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            t_recv = now_ns()
            try:
                packet = unpack(data)
            except ValueError:
                continue
            packet["t_recv_ns"] = t_recv
            packet["packet_bytes"] = len(data)
            t_send = int(packet.get("t_send_ns") or 0)
            t_cap = int(packet.get("t_capture_ns") or 0)
            packet["network_ms"] = (t_recv - t_send) / 1e6 if t_send else None
            packet["e2e_ms"] = (t_recv - t_cap) / 1e6 if t_cap else None
            reading = packet.get("reading") or {}
            self.writer.writerow(
                [
                    datetime.now().isoformat(timespec="milliseconds"),
                    packet.get("sensor"),
                    packet.get("trial_id"),
                    packet.get("seq"),
                    reading.get("text", ""),
                    int(bool(packet.get("ok"))),
                    f"{packet.get('pipeline_ms', 0):.2f}",
                    "" if packet["network_ms"] is None else f"{packet['network_ms']:.2f}",
                    "" if packet["e2e_ms"] is None else f"{packet['e2e_ms']:.2f}",
                    reading.get("error_s", ""),
                    packet.get("sensor_bytes", 0),
                    len(data),
                    packet.get("confidence", ""),
                ]
            )
            self.log_handle.flush()
            with self.lock:
                self.samples.append(packet)
                self.bytes_in += len(data) + int(packet.get("sensor_bytes") or 0)
                self.count += 1

    def _mean(self, key: str) -> str:
        with self.lock:
            vals = [s[key] for s in self.samples if s.get(key) is not None]
        if not vals:
            return "—"
        return f"{sum(vals) / len(vals):.1f} ms   (n={len(vals)})"

    def _refresh(self) -> None:
        with self.lock:
            latest = self.samples[-1] if self.samples else None
            count = self.count
            sensor_bytes = sum(int(s.get("sensor_bytes") or 0) for s in self.samples)
            packet_bytes = sum(int(s.get("packet_bytes") or 0) for s in self.samples)
        elapsed = max(time.monotonic() - self.started, 0.1)
        if latest is None:
            self.labels["status"].set(f"listening on {self.port}")
        else:
            reading = latest.get("reading") or {}
            self.labels["sensor"].set(str(latest.get("sensor")))
            self.labels["trial"].set(str(latest.get("trial_id")))
            self.labels["reading"].set(reading.get("text") or latest.get("note") or "no read")
            err = reading.get("error_s")
            self.labels["error"].set("—" if err is None else f"{err:.1f} s")
            self.labels["pipeline"].set(self._mean("pipeline_ms"))
            self.labels["network"].set(self._mean("network_ms"))
            self.labels["e2e"].set(self._mean("e2e_ms"))
            self.labels["volume"].set(
                f"sensor {sensor_bytes / 1e6:.1f} MB in window   packets {packet_bytes / 1e3:.1f} kB"
            )
            self.labels["rate"].set(f"{count / elapsed:.1f} pkt/s   total {count}")
            self.labels["status"].set("receiving")
        if self.running:
            self.root.after(200, self._refresh)

    def close(self) -> None:
        self.running = False
        self.sock.close()
        self.log_handle.close()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark receiver GUI")
    parser.add_argument("--port", type=int, default=5005)
    parser.add_argument("--log", default="benchmark_recv.csv")
    args = parser.parse_args()
    App(args.port, Path(args.log)).run()


if __name__ == "__main__":
    main()
