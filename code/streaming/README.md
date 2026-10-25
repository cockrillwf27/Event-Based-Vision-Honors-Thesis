## Triton2 EVS Capture Path (25 Oct 2026)

Verified end-to-end streaming from the Lucid Triton2 EVS (TRT009S-E, S/N 264101664) on the Jetson Orin Nano to a laptop for reconstruction and visualization.

### What works
- Camera is reachable on the Jetson via Link-Local (169.254.0.0/16) on `enP8p1s0`.
- Arena SDK ARM64 can enumerate and acquire from the camera (`Cpp_Enumeration`, `Cpp_SimpleAcquisition`).
- Custom C++ sender (`jetson_evs_sender.cpp`) streams raw EVT 3.0 packets over TCP.
- Python receiver (`laptop_evs_receiver.py`) decodes the stream and displays a live event image.
- Output files (raw packets and screenshots) are written to `evs_output/`.

### Current limitations
- ARM64 Arena SDK does not expose all Triton2 EVS feature nodes (e.g. `EVSOutputFrame`).  
  The camera currently sends raw EVT 3.0 rather than pre-rendered CD Frames.
- Metavision HAL plugin for the Triton2 is not yet available; the path uses Arena only.
- Network path requires both machines on the same subnet (or a direct Ethernet link). Campus Wi-Fi client isolation can block connectivity.

### Files
- `streaming/jetson_evs_sender.cpp` — Jetson capture and TCP sender
- `streaming/laptop_evs_receiver.py` — Laptop EVT 3.0 decoder and viewer

### Next steps
- Add timestamps for latency measurement.
- Enumerate available nodes and set Accumulation Time / ERC when possible.
- Integrate with the existing benchmark package for RGB-vs-event comparison.
