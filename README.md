# edge-video

Containerized Raspberry Pi camera service for the AI Legal Edge platform.

## Design goals

- Local-first evidence capture.
- Raspberry Pi CSI camera through `rpicam`/libcamera, not raw `/dev/video0` assumptions.
- Hardware H.264 encoding.
- One-minute segmented MKV evidence files.
- SHA-256 hash calculated after each segment is closed and flushed.
- JSON evidence manifest beside every segment.
- System-clock timestamps are explicitly marked `unsynchronized` until GPS/PPS is available.
- Controller registration follows the current generic node/service API used by edge-audio and edge-gps.
- Optional network streaming is separate from the evidence path.

## Current tested hardware

The initial target is the Raspberry Pi 4 with an OV5647 CSI camera. The current tested camera reports as camera index `0` and is exposed by the Unicam subsystem. `rpicam-hello --list-cameras` is the authoritative camera discovery mechanism.

## Evidence flow

```text
CSI camera
    |
    v
rpicam-vid / libcamera
    |
    +--> H.264
    |
    v
1-minute MKV segments
    |
    +--> fsync
    +--> SHA-256
    +--> immutable JSON manifest
    |
    v
local evidence spool
```

The original segment is not modified after finalization. AI analysis is expected to consume a read-only copy/replica in later phases.

## Time model

Version 0.1.0 does not claim GPS-authoritative time. Each manifest records:

- UTC system time
- a monotonic clock field
- `clock_source: system`
- `time_quality: unsynchronized`
- `gps_authority: false`

When edge-gps/PPS is ready, the common evidence timestamp envelope can be extended without changing the video payload.

## Controller integration

The service uses the current generic API:

- `POST /api/v1/nodes`
- `POST /api/v1/nodes/{node_id}/services`
- `GET /api/v1/nodes/{node_id}/services/{service_id}/configuration`
- `PUT /api/v1/nodes/{node_id}/services/{service_id}/status`

This preserves the multi-service-per-node architecture.

## Raspberry Pi test without Docker

```bash
rpicam-hello --list-cameras
rpicam-vid -t 10s --width 1920 --height 1080 --codec libav --libav-format mkv -o test.mkv
```

For a live VLC-compatible MPEG-TS test, Raspberry Pi documents the `libav` MPEG-TS network path. See the official camera documentation.

## Docker

Create `.env` from `.envSAMPLE`, then:

```bash
docker compose build
docker compose up -d
```

Health:

```bash
curl http://127.0.0.1:8090/health
```

Evidence is stored under the host path configured by `EDGE_VIDEO_HOST_EVIDENCE_PATH`.

## Important MVP limitation

The current implementation intentionally keeps the live-stream path optional and separate. It is not yet the final production media gateway. The evidence recorder remains local-first. A later phase should add a server-side media gateway (MediaMTX or equivalent), server-side evidence ingestion/verification, upload acknowledgements, retention policy, event markers, GPS/PPS time authority, and AI analysis workers.
