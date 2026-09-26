# edge-video

Containerized Raspberry Pi video capture and evidence service for the AI Legal Edge platform.

`edge-video` provides local-first video capture, authoritative raw H.264 evidence segmentation, SHA-256 evidence manifests, optional HLS live streaming, and registration/status integration with the generic Edge Controller.

The current implementation is an **MVP focused on reliable local evidence capture from a Raspberry Pi CSI camera**. Multi-camera support, additional camera backends, GPS/PPS-authoritative time, server-side evidence ingestion, and AI video analysis are future development work.

---

## Current Status

**Version:** `0.1.0`

**Current tested hardware:**

* Raspberry Pi 4
* Raspberry Pi CSI camera
* OV5647 sensor
* Raspberry Pi `rpicam` / libcamera stack
* Docker deployment

**Current tested capture configuration:**

```text
1920x1080
30 FPS
H.264
12 Mbps
inline H.264 headers
```

**Current capabilities:**

* Raspberry Pi CSI camera discovery
* OV5647 capture
* Hardware H.264 capture through `rpicam-vid`
* Local raw H.264 evidence segmentation
* 60-second evidence segments
* SHA-256 hashing
* Atomic JSON evidence manifests
* System/monotonic timing metadata
* Local edge-time Capture Time Context acquisition
* Temporal provenance in evidence manifests
* Graceful temporal fallback when edge-time is unavailable
* Controller node/service registration
* Controller configuration retrieval
* Controller runtime status updates
* Optional HLS live streaming
* Docker deployment
* Automatic container restart
* HTTP health endpoint

**Current limitations:**

* One camera per `edge-video` process
* Raspberry Pi CSI/libcamera cameras only
* Generic USB/V4L2 cameras are not yet supported
* Multiple simultaneous cameras are not yet supported
* GPS/PPS authoritative timestamps are not yet integrated
* Raw H.264 timestamp warnings remain
* HLS latency has not yet been optimized
* Server-side evidence ingestion is not implemented
* AI video analysis is not implemented

---

# Architecture

The current media architecture is:

```text
                    Raspberry Pi CSI Camera
                              |
                              v
                         rpicam-vid
                              |
                              | H.264 stdout
                              |
                              v
                       MediaPipeline
                              |
                 +------------+------------+
                 |                         |
                 v                         v
          Evidence FFmpeg             Live FFmpeg
                 |                         |
                 v                         v
        Raw H.264 segments                HLS
                 |                         |
                 v                         v
          Evidence finalizer          /stream
                 |
                 +--> fsync
                 |
                 +--> SHA-256
                 |
                 +--> JSON manifest
```

The evidence path is the authoritative path.

Live streaming is optional and is not intended to become the authoritative evidence source.

AI analysis in future phases must consume a read-only copy/replica of authoritative evidence rather than modifying the original evidence.

---

# Camera Capture

The current implementation uses:

```text
rpicam-vid
libcamera
```

for Raspberry Pi CSI camera capture.

Camera discovery is performed through the Raspberry Pi camera stack.

A typical camera reports information such as:

```text
index: 0
sensor: ov5647
native: 2592x1944 10-bit GBRG
path: /base/soc/i2c0mux/i2c@1/ov5647@36
```

The selected camera is currently configured with:

```text
EDGE_VIDEO_CAMERA_INDEX=0
```

The media pipeline opens the selected camera once and captures its H.264 output.

Current capture command is conceptually:

```bash
rpicam-vid \
  --camera 0 \
  --timeout 0 \
  --nopreview \
  --width 1920 \
  --height 1080 \
  --framerate 30 \
  --bitrate 12000000 \
  --codec h264 \
  --inline \
  -o -
```

The camera's encoded H.264 stream is written to stdout and consumed by the media pipeline.

---

# Evidence Capture

Evidence capture is local-first.

Current evidence pipeline:

```text
rpicam-vid
    |
    | H.264 stdout
    v
FFmpeg
    |
    | stream copy
    v
60-second raw H.264 segments
```

The current evidence command is equivalent to:

```bash
ffmpeg \
  -hide_banner \
  -loglevel warning \
  -f h264 \
  -framerate 30 \
  -i pipe:0 \
  -an \
  -c:v copy \
  -f segment \
  -segment_time 60 \
  -segment_format h264 \
  /recordings/segment%06d.h264
```

The video is **not re-encoded** by FFmpeg.

The current evidence format is:

```text
H.264 elementary stream
```

It is **not MKV**.

Each completed segment is finalized by the evidence recorder.

---

# Evidence Finalization

The recorder monitors completed H.264 segments.

A segment must be stable before it is finalized.

Finalization performs:

```text
segment
   |
   v
fsync
   |
   v
SHA-256
   |
   v
JSON manifest
```

The manifest is written atomically.

Example runtime result:

```text
Evidence finalized: segment000000.h264
sha256=b63db94a9dbffbb77e077670e3f61363aa07b6c4077b7e06f7d319e941432e21
```

The original evidence segment is not modified after finalization.

---

# Evidence Manifests

Each evidence segment receives a corresponding JSON manifest.

Current manifest metadata includes information describing:

* Capture timing
* Camera information
* Video properties
* SHA-256 hash
* Service start timing
* Media pipeline
* Evidence transport
* Live transport
* Timestamp limitations
* Temporal provenance and Capture Time Context when available

When Capture Time Context is available, the manifest records the context acquisition and temporal provenance associated with the evidence segment. This provenance does not replace timestamps in the raw H.264 payload and does not assert exact physical camera exposure timing.

If edge-time is unavailable during finalization, the evidence segment is still finalized and the manifest records that temporal context was unavailable.

The current media pipeline metadata identifies:

```json
{
  "camera_owner": "rpicam-vid",
  "encoded_format": "h264",
  "evidence_transport": "stdout->ffmpeg",
  "live_transport": "stdout->ffmpeg->hls"
}
```

when live streaming is enabled.

This metadata is intentionally explicit so future evidence processing can distinguish the authoritative evidence path from derived/live media.

---

# Time Model

Version `0.1.0` does **not** claim GPS/PPS-authoritative video timestamps.

The current temporal model combines:

```text
system UTC
monotonic clock
local edge-time Capture Time Context
GPS/PPS authority (future)
physical camera exposure timing (not currently measured)
container/media timestamps
```

At the evidence boundary, `edge-video` requests Capture Time Context from the local `edge-time` instance and associates the returned context with the evidence segment manifest. The context includes the selected source, source observation, UTC and monotonic position, uncertainty, freshness, synchronization state, authority provenance, consistency state, holdover state, and attestation reference.

Capture Time Context acquisition time is **not** the exact physical camera exposure time unless a separately defined sensor/frame timing mechanism establishes that relationship. The current implementation does not make that claim.

If local `edge-time` is unavailable, video capture and evidence finalization continue using the local system/monotonic timing model. The manifest records the unavailable temporal context rather than stopping authoritative capture.

Future integration with `edge-gps` must extend temporal authority without modifying the original video payload or retroactively rewriting its provenance.

The temporal model must continue to distinguish:

```text
system clock
monotonic clock
edge-time Capture Time Context
GPS-derived time
PPS synchronization
physical capture/exposure timing
container/media timestamps
```

---

# Live HLS Streaming

Live streaming is optional.

Current configuration:

```env
EDGE_VIDEO_ENABLE_STREAM=true
EDGE_VIDEO_HLS_SEGMENT_SECONDS=1
EDGE_VIDEO_HLS_SEGMENT_COUNT=3
```

The live pipeline uses FFmpeg to convert the captured H.264 stream into HLS:

```text
H.264
   |
   v
FFmpeg
   |
   v
HLS
   |
   +--> index.m3u8
   +--> segment*.ts
```

The live playlist is served through:

```text
/stream
```

with the playlist:

```text
/stream/index.m3u8
```

HLS latency optimization is deferred.

---

# Live Stream vs Evidence

The architectural priority is:

```text
AUTHORITATIVE EVIDENCE
        >
LIVE STREAM
        >
FUTURE AI ANALYSIS
```

The live stream is disposable.

A live client disconnect is not an evidence failure.

Current HTTP clients may produce a connection-reset message when they disconnect from the stream. This is not currently treated as a media capture failure.

The live pipeline must not become the authoritative source of evidence.

---

# Controller Integration

`edge-video` uses the generic Edge Controller node/service architecture.

The controller URL is deployment configuration and must use the host-addressed controller endpoint. Docker service/container names must not be used.

The service registers beneath the physical hosting node. The service does not create a separate controller node for each Docker container.

Current controller operations include:

```text
GET  /api/v1/nodes/{node_id}
GET  /api/v1/nodes/{node_id}/services
POST /api/v1/nodes/{node_id}/services
GET  /api/v1/nodes/{node_id}/services/{service_id}/configuration
PUT  /api/v1/nodes/{node_id}/services/{service_id}/status
```

The current implementation has been verified against the Edge Controller with HTTP 200 responses for:

```text
node lookup
service lookup
status update
configuration retrieval
```

The controller architecture supports multiple services per physical node.

---

# Physical Node Identity

The controller node identity represents the physical hosting node, not an individual Docker container.

The deployment normally uses the host's runtime identity so multiple services on the same physical node register beneath the same Node. An explicit `EDGE_NODE_ID` override remains available when required.

This service follows the project rule that nodes may host multiple services; `edge-video` is a Service, not a special controller Node.

# Configuration

Current important configuration:

```env
EDGE_CONTROLLER_URL=<host-addressed-controller-url>

EDGE_SERVICE_ID=edge-video
EDGE_SERVICE_NAME=edge-video
EDGE_SERVICE_VERSION=0.1.0

EDGE_VIDEO_CAMERA_INDEX=0
EDGE_VIDEO_WIDTH=1920
EDGE_VIDEO_HEIGHT=1080
EDGE_VIDEO_FRAMERATE=30
EDGE_VIDEO_BITRATE=12000000
EDGE_VIDEO_SEGMENT_SECONDS=60
EDGE_VIDEO_INLINE_HEADERS=true

EDGE_VIDEO_ENABLE_STREAM=true
EDGE_VIDEO_HLS_SEGMENT_SECONDS=1
EDGE_VIDEO_HLS_SEGMENT_COUNT=3

EDGE_VIDEO_HEALTH_PORT=8090
```

Additional configuration exists for:

```text
rpicam binary
FFmpeg binary
health host
health port
evidence root
live root
controller timeout
```

See `.envSAMPLE` for the complete configuration list.

---

# Health Endpoint

The service exposes HTTP health information on port:

```text
8090
```

Default local endpoint:

```text
http://127.0.0.1:8090/health
```

Docker publishes the configured health port to the host.

---

# Raspberry Pi Camera Test

Before deploying the service, camera discovery can be tested directly on the Raspberry Pi:

```bash
rpicam-hello --list-cameras
```

A basic H.264 capture test can be performed with:

```bash
rpicam-vid \
  -t 10s \
  --width 1920 \
  --height 1080 \
  --codec h264 \
  -o test.h264
```

The exact camera modes available depend on the connected sensor and Raspberry Pi camera stack.

---

# Docker Deployment

Create the deployment environment from `.envSAMPLE`:

```bash
cp .envSAMPLE .env
```

Configure the environment as required.

Then:

```bash
docker compose build
docker compose up -d
```

Check the container:

```bash
docker ps
```

Check logs:

```bash
docker logs -f edge-video
```

Check health:

```bash
curl http://127.0.0.1:8090/health
```

---

# Known FFmpeg Timestamp Warning

The current implementation produces warnings similar to:

```text
Timestamps are unset in a packet for stream 0.
This is deprecated and will stop working in the future.
```

This occurs because the authoritative evidence stream is raw H.264 and does not contain container timestamps.

This is currently a known limitation.

It must eventually be addressed as part of the evidence/timestamp architecture.

The solution must not compromise the raw evidence model or incorrectly imply GPS-authoritative timestamps.

---

# Known Limitations

## Single camera

The current implementation supports one selected camera per `edge-video` process.

Current selection is based on:

```env
EDGE_VIDEO_CAMERA_INDEX=0
```

The media pipeline currently owns:

```text
one rpicam-vid process
one evidence FFmpeg process
one optional HLS FFmpeg process
```

Multiple simultaneous cameras are not implemented.

---

## USB/V4L2 cameras

Generic USB cameras are not currently supported.

The current camera backend is:

```text
rpicam-vid / libcamera
```

A future implementation must add a V4L2 backend rather than assuming that changing the camera index will make `/dev/videoN` USB cameras work.

---

## Multiple cameras

Future versions need to support combinations such as:

```text
Pi CSI camera
+
USB camera
```

and:

```text
USB camera
+
USB camera
```

and potentially:

```text
multiple CSI cameras
```

where supported by the Raspberry Pi hardware.

The target architecture is:

```text
edge-video
+-- camera-0
|   +-- evidence
|   +-- live
+-- camera-1
|   +-- evidence
|   +-- live
+-- camera-N
    +-- evidence
    +-- live
```

Each camera must have an independent capture/evidence lifecycle.

---

