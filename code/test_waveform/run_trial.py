#!/usr/bin/env python3
"""
run_trial.py — Create a self-contained trial folder for Simpson 260 / event-camera experiments.

Implements:
  1. Folder layout (one folder per run, never overwrite)
  2. run_meta.json with full metadata
  4. tegrastats logging

Camera capture and reference-voltage logging are stubbed for the next session.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Defaults (edit or override via CLI)
# ---------------------------------------------------------------------------
DEFAULT_WAVEFORM = Path("meter_trial.csv")          # path to the CSV you generated
DEFAULT_RUNS_DIR = Path("runs")
WAVEFORM_SAMPLE_RATE = 100                          # Sa/s used when generating the CSV
EXPECTED_DURATION_S = 430                           # approx total length of the 42-segment table (~7 min)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def nvpmodel() -> str:
    try:
        return subprocess.check_output(["nvpmodel", "-q"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def create_run_folder(runs_dir: Path, camera: str, lighting: str, repeat: int) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    # Find next available Rxxx for today
    existing = list(runs_dir.glob(f"{today}_R*_{camera}_*"))
    next_id = 1
    if existing:
        ids = []
        for p in existing:
            try:
                ids.append(int(p.name.split("_")[1][1:]))
            except Exception:
                pass
        if ids:
            next_id = max(ids) + 1
    run_id = f"R{next_id:03d}"
    folder_name = f"{today}_{run_id}_{camera}_light{lighting}_rep{repeat}"
    folder = runs_dir / folder_name
    folder.mkdir(parents=True, exist_ok=False)  # never overwrite
    (folder / "camera_raw").mkdir()
    return folder, run_id


def write_metadata(folder: Path, run_id: str, args, waveform_path: Path):
    meta = {
        "run_id": run_id,
        "date_time": datetime.now().isoformat(timespec="seconds"),
        "camera": args.camera,
        "lighting": args.lighting,
        "repeat": args.repeat,
        "waveform_file": waveform_path.name,
        "waveform_sha256": sha256_file(waveform_path),
        "waveform_sample_rate_hz": WAVEFORM_SAMPLE_RATE,
        "meter_range": "10 V DC",
        "awg_model": "Keysight 33500B",
        "awg_sample_rate_hz": WAVEFORM_SAMPLE_RATE,
        "awg_load": "High Z",
        "jetson_power_mode": nvpmodel(),
        "git_commit": git_commit(),
        "camera_settings": {
            "notes": "fill in bias / exposure / gain / fps / lens / focus"
        },
        "status": "in_progress",
        "notes": ""
    }
    with (folder / "run_meta.json").open("w") as f:
        json.dump(meta, f, indent=2)
    return meta


def start_tegrastats(logfile: Path) -> subprocess.Popen:
    return subprocess.Popen(
        ["tegrastats", "--interval", "100", "--logfile", str(logfile)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop_process(proc: subprocess.Popen):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def sanity_check(folder: Path) -> list[str]:
    issues = []
    for name in ["run_meta.json", "waveform.csv", "tegrastats.log"]:
        p = folder / name
        if not p.exists() or p.stat().st_size == 0:
            issues.append(f"{name} missing or empty")
    # angles.csv and reference_v.csv are optional tonight
    return issues


def main():
    parser = argparse.ArgumentParser(description="Start a self-contained Simpson 260 trial run.")
    parser.add_argument("--camera", required=True, choices=["event", "rgb"], help="Camera type")
    parser.add_argument("--lighting", required=True, help="Lighting level label (e.g. A, B)")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat number (1-based)")
    parser.add_argument("--waveform", type=Path, default=DEFAULT_WAVEFORM, help="Path to meter_trial.csv")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR, help="Root runs directory")
    parser.add_argument("--duration", type=float, default=EXPECTED_DURATION_S + 30,
                        help="How long to wait (seconds) before stopping logs")
    parser.add_argument("--manual-trigger", action="store_true",
                        help="Prompt the user to start the 33500B instead of SCPI")
    args = parser.parse_args()

    if not args.waveform.exists():
        sys.exit(f"Waveform file not found: {args.waveform}")

    args.runs_dir.mkdir(parents=True, exist_ok=True)
    folder, run_id = create_run_folder(args.runs_dir, args.camera, args.lighting, args.repeat)
    print(f"Created run folder: {folder}")

    # Copy waveform
    shutil.copy(args.waveform, folder / "waveform.csv")

    # Metadata
    write_metadata(folder, run_id, args, args.waveform)
    print(f"Wrote {folder / 'run_meta.json'}")

    # Notes file
    (folder / "notes.txt").write_text("# Add any anomalies here (bumped table, light flicker, etc.)\n")

    # Start tegrastats
    tegrastats_log = folder / "tegrastats.log"
    tegrastats_proc = start_tegrastats(tegrastats_log)
    print("Started tegrastats")

    # --- Placeholders for next session ---
    # TODO: start reference voltage logger (DAQ / scope / DMM)
    # TODO: start camera capture into folder / "camera_raw"
    # TODO: trigger 33500B (SCPI or manual)

    if args.manual_trigger:
        input("Press Enter when you have started the 33500B waveform...")
    else:
        print("TODO: trigger 33500B via SCPI (pyvisa) here")

    print(f"Waiting {args.duration:.0f} s for the trial to finish...")
    try:
        time.sleep(args.duration)
    except KeyboardInterrupt:
        print("Interrupted — stopping early")

    # Stop in reverse order
    stop_process(tegrastats_proc)
    print("Stopped tegrastats")
    # TODO: stop camera and reference logger

    # Sanity check
    issues = sanity_check(folder)
    if issues:
        print("Sanity check issues:")
        for i in issues:
            print("  -", i)
        # mark bad in metadata
        meta_path = folder / "run_meta.json"
        with meta_path.open() as f:
            meta = json.load(f)
        meta["status"] = "bad"
        meta["notes"] = "Sanity check failed: " + "; ".join(issues)
        with meta_path.open("w") as f:
            json.dump(meta, f, indent=2)
    else:
        print("Sanity check passed")
        meta_path = folder / "run_meta.json"
        with meta_path.open() as f:
            meta = json.load(f)
        meta["status"] = "complete"
        with meta_path.open("w") as f:
            json.dump(meta, f, indent=2)

    print(f"Run finished. Folder: {folder}")


if __name__ == "__main__":
    main()
