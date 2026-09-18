# edge-video — Service Status

**Purpose:** Current development phase and maturity of the video evidence service.  
**Status:** Operational MVP / next integration target  
**Last reviewed:** September 2026

## Current Phase

**Phase 1 — Evidence Capture MVP: OPERATIONAL**

The Raspberry Pi CSI-camera evidence pipeline is operational as an MVP. The next development increment is evidence-facing temporal integration with local `edge-time`.

## Verified MVP Capabilities

- Raspberry Pi CSI/OV5647 discovery and capture
- Hardware H.264 capture through `rpicam-vid`
- 1920x1080 configured 30 FPS capture
- 12 Mbps configured bitrate
- Local raw H.264 evidence segmentation
- 60-second evidence segments
- SHA-256 hashing and atomic JSON manifests
- System/monotonic timing metadata
- Generic controller registration/configuration/status
- Optional HLS live streaming
- Health endpoint and restart behavior

The authoritative evidence path is separate from the disposable live HLS path.

## Evidence Position

Completed segments are finalized with filesystem synchronization, SHA-256 hashing, and an accompanying manifest. Finalized source evidence is not modified by later processing.

The raw H.264 path has known timestamp warnings because the elementary stream does not carry container timestamps.

## Current Temporal Position

The service does not claim GPS/PPS-authoritative timestamps. The next integration is to associate local edge-time Capture Time Context with video evidence while preserving the distinction between context acquisition time and physical camera exposure timing.

## Current Limitations

- One selected camera per process
- Raspberry Pi CSI/libcamera backend only
- USB/V4L2 cameras not implemented
- Multiple simultaneous cameras not implemented
- Server-side evidence ingestion not implemented
- AI video analysis not implemented
- Raw-H.264 timestamp handling remains open
- HLS latency optimization remains deferred

## Future Direction

Multiple camera backends and independent per-camera evidence lifecycles remain future work and are not part of the current MVP.
