# edge-video — Development Handoff

## Purpose

This document is the authoritative continuation point for future development of the `edge-video` service in the AI Legal Edge platform.

The immediate goal is **not** to redesign the working MVP. The current implementation is sufficiently functional to commit to ADO `master` and synchronize the current working state to the public GitHub repository.

Future work must preserve the evidence-first architecture already established.


---

# GitHub access
If there are issues using the API to pull from the public code base, always try to access any files via direct access/links for reference. 
GitHub public repos will ALWAYS be up to date on builds/commits. 

---

# 1. Current Project State

## Repository

Public repository:

```text
https://github.com/troy-cichosz/edge-video
```

Current development branch:

```text
public
```

ADO is the primary development/source workflow. After the current working state is committed to ADO `master`, GitHub will be updated from that source.

### Important

The runtime state described below includes the recent working changes made during this development session.

In particular, the Docker deployment now uses:

```yaml
uts: host
```

This change is required so that `socket.gethostname()` inside the container resolves to the physical Raspberry Pi hostname rather than the Docker container ID.

The repository must be synchronized with this working state before future development assumes it is present.

---

# 2. Hardware Currently Verified

Tested Raspberry Pi nodes:

```text
pi4SSD
pi4nVME
```

Current camera hardware:

```text
Raspberry Pi CSI camera
Sensor: OV5647
```

Observed camera identity:

```text
/base/soc/i2c0mux/i2c@1/ov5647@36
```

Current discovered camera:

```text
camera index: 0
sensor: ov5647
native: 2592x1944 10-bit GBRG
```

The Raspberry Pi camera is discovered through the `rpicam`/libcamera stack.

`edge-video` does **not** currently assume `/dev/video0` alone is the camera abstraction. The authoritative discovery mechanism is `rpicam-vid --list-cameras`.

---

# 3. Current Container Architecture

Current deployment is Docker-based.

Relevant Compose structure:

```yaml
services:
  edge-video:
    build:
      context: .
    image: $(edge-video_TAG)
    container_name: edge-video
    restart: unless-stopped
    uts: host
    env_file:
      - .env
    privileged: true
    volumes:
      - ../recordings/videos:/recordings
      - /run/udev:/run/udev:ro
      - /dev:/dev
    ports:
      - "${EDGE_VIDEO_HEALTH_PORT:-8090}:8090"
```

The following are intentional:

* `privileged: true`
* `/dev:/dev`
* `/run/udev:/run/udev:ro`
* host UTS namespace
* container restart policy
* host-backed recording storage

Do not remove `uts: host` without replacing it with another consistent physical-node identity mechanism.

---

# 4. Physical Node Identity

The controller architecture is:

```text
Physical Node
├── edge-audio
├── edge-gps
└── edge-video
```

Services must register beneath the physical node.

Example:

```text
pi4nVME
├── edge-audio
├── edge-gps
└── edge-video
```

NOT:

```text
fa845db26f12
└── edge-video
```

The previous incorrect node was caused by Docker hostname behavior.

`edge-video` configuration currently supports:

```python
node_id=env_or_default(
    "EDGE_NODE_ID",
    socket.gethostname(),
)
```

The normal deployment does not need a unique hard-coded node ID when the container shares the host UTS namespace.

With:

```yaml
uts: host
```

the fallback becomes:

```text
socket.gethostname()
        ↓
pi4nVME
```

rather than:

```text
fa845db26f12
```

This is consistent with the existing edge-service architecture.

---

# 5. Controller Integration — WORKING

Controller:

```text
http://spoo-lin.spoocannon.com:8080
```

Current edge-video registration has been verified successfully.

Example verified runtime:

```text
node_id=pi4nVME
service_id=edge-video
service_version=0.1.0
```

The following requests have been verified as successful:

```text
GET  /api/v1/nodes/pi4nVME
GET  /api/v1/nodes/pi4nVME/services
PUT  /api/v1/nodes/pi4nVME/services/edge-video/status
GET  /api/v1/nodes/pi4nVME/services/edge-video/configuration
```

All returned:

```text
HTTP 200
```

The controller correctly recognized that both the physical node and `edge-video` service already existed.

The controller GUI now shows the service beneath the correct physical node.

This is considered **working and complete for the current MVP**.

---

# 6. Controller Status Reporting — WORKING

`edge-video` reports runtime state to the controller.

Example online status:

```json
{
  "status": "ok",
  "camera": {
    "index": 0,
    "sensor": "ov5647",
    "native": "2592x1944 10-bit GBRG",
    "path": "/base/soc/i2c0mux/i2c@1/ov5647@36",
    "modes": [...]
  },
  "recording": true,
  "stream": {
    "enabled": true,
    "alive": true,
    "protocol": "hls",
    "endpoint": "/stream",
    "playlist": "/stream/index.m3u8",
    "error": null
  }
}
```

On shutdown it reports:

```text
status = offline
```

with:

```text
recording = false
stream.alive = false
```

This behavior is verified.

---

# 7. Camera Capture — WORKING

Current capture command:

```text
rpicam-vid
  --camera 0
  --timeout 0
  --nopreview
  --width 1920
  --height 1080
  --framerate 30
  --bitrate 12000000
  --codec h264
  --inline
  -o -
```

Current tested configuration:

```text
1920x1080
30 FPS
12 Mbps
H.264
inline headers
```

The OV5647 successfully selected:

```text
1920x1080-SGBRG10_CSI2P
```

with the corresponding YUV420 output stream.

The camera process remains owned by the media pipeline.

The camera is opened once and its encoded H.264 stdout is distributed to downstream consumers.

---

# 8. Evidence Pipeline — WORKING

The evidence path is authoritative.

Current architecture:

```text
OV5647
   |
   v
rpicam-vid
   |
   | H.264 stdout
   v
MediaPipeline
   |
   v
FFmpeg evidence process
   |
   v
60-second raw H.264 segments
```

Current evidence command:

```text
ffmpeg
  -hide_banner
  -loglevel warning
  -f h264
  -framerate 30
  -i pipe:0
  -an
  -c:v copy
  -f segment
  -segment_time 60
  -segment_format h264
  /recordings/segment%06d.h264
```

The encoded video is copied rather than re-encoded.

Evidence segments are therefore generated locally from the original H.264 stream.

---

# 9. Evidence Finalization — WORKING

The recorder watches for completed:

```text
segment*.h264
```

files.

A segment is considered stable before finalization.

Finalization performs:

```text
fsync
   ↓
SHA-256
   ↓
manifest generation
   ↓
atomic JSON write
```

Runtime verification has produced entries such as:

```text
Evidence finalized: segment000000.h264
sha256=b63db94a9dbffbb77e077670e3f61363aa07b6c4077b7e06f7d319e941432e21
```

and:

```text
Evidence finalized: segment000001.h264
sha256=363f1c9093e8f5342fe00fdf3f0628f449b26f5d1d47d97e1794240ed0ad8d59
```

The evidence segment itself is not modified after finalization.

---

# 10. Evidence Metadata / Time Model

Current evidence timestamp model is intentionally conservative.

Current system:

```text
UTC system time
monotonic clock
clock_source = system
time_quality = unsynchronized
gps_authority = false
```

The current system does **not** claim GPS-authoritative time.

This is intentional.

Future GPS/PPS integration must augment the evidence timestamp envelope without modifying the authoritative video payload.

---

# 11. Live HLS Stream — WORKING

Live streaming is enabled in the current deployment.

Current configuration:

```text
EDGE_VIDEO_ENABLE_STREAM=true
EDGE_VIDEO_HLS_SEGMENT_SECONDS=1
EDGE_VIDEO_HLS_SEGMENT_COUNT=3
```

Current live architecture:

```text
rpicam-vid
   |
   | H.264
   v
MediaPipeline
   |
   +--------------------+
   |                    |
   v                    v
Evidence FFmpeg       bounded live queue
                           |
                           v
                       Live FFmpeg
                           |
                           v
                         HLS
                           |
                           v
                  /stream/index.m3u8
```

The live branch is explicitly disposable.

A slow or failed live consumer must not block authoritative evidence capture.

The live stream has been successfully viewed during testing.

Observed latency is approximately:

```text
~8 seconds
```

Further HLS latency optimization is deferred.

---

# 12. Known FFmpeg Timestamp Warning

The current pipelines produce warnings similar to:

```text
Timestamps are unset in a packet for stream 0.
This is deprecated and will stop working in the future.
```

This occurs because the raw H.264 stream does not contain container timestamps.

This has been observed in both:

```text
evidence segment muxer
HLS muxer
```

This is a known issue and has intentionally been deferred.

It must eventually be addressed as part of the media/timestamp architecture, especially before treating the stream as production-grade evidentiary media.

Do not solve this by altering the authoritative evidence payload casually.

The future solution must preserve the evidence model and explicitly distinguish:

```text
capture timestamps
container timestamps
GPS/PPS authoritative timestamps
monotonic timing
```

---

# 13. Current Single-Camera Limitation

The current service is explicitly a **single-camera pipeline**.

`Camera.selected_camera()` discovers cameras using:

```text
rpicam-vid --list-cameras
```

but selects one camera based on:

```text
EDGE_VIDEO_CAMERA_INDEX
```

The current media pipeline owns:

```text
one rpicam-vid process
one evidence FFmpeg process
one live FFmpeg process
```

Therefore the current architecture is:

```text
edge-video
└── one selected CSI camera
    ├── authoritative evidence
    └── optional HLS stream
```

It is NOT yet:

```text
edge-video
├── camera 0
├── camera 1
└── camera 2
```

with independent capture/evidence/stream pipelines.

---

# 14. USB Camera Support — NOT IMPLEMENTED

Generic USB/V4L2 cameras are not currently supported.

The current capture implementation is based on:

```text
rpicam-vid
libcamera
```

and Raspberry Pi CSI camera discovery.

Do not assume that:

```text
/dev/video1
/dev/video2
```

can simply be selected by changing `EDGE_VIDEO_CAMERA_INDEX`.

The next implementation must introduce an explicit camera backend abstraction.

---

# 15. Required Future Camera Architecture

The next major edge-video development phase should support multiple physical camera types.

Target architecture:

```text
edge-video
│
├── Camera Manager
│
├── Camera 0
│   └── libcamera / Raspberry Pi CSI
│
├── Camera 1
│   └── V4L2 / USB
│
└── Camera 2
    └── V4L2 / USB
```

Camera identity should become a first-class object rather than simply an integer camera index.

Conceptually:

```text
camera_id
backend
device
sensor/model
capabilities
resolution
framerate
pixel format
configuration
status
```

Potential backends:

```text
libcamera
v4l2
```

The implementation should not hard-code:

```text
camera 0 = Pi camera
camera 1 = USB
```

Instead, cameras should be discovered and represented according to their actual capabilities.

---

# 16. Multi-Camera Evidence Architecture

Multiple cameras require independent evidence identities.

The future architecture should look approximately like:

```text
Physical Node
│
└── edge-video
    │
    ├── camera-0
    │   ├── capture
    │   ├── evidence
    │   ├── manifests
    │   └── live stream
    │
    ├── camera-1
    │   ├── capture
    │   ├── evidence
    │   ├── manifests
    │   └── live stream
    │
    └── camera-2
        ├── capture
        ├── evidence
        ├── manifests
        └── live stream
```

Evidence storage should eventually prevent collisions between cameras.

Example conceptual layout:

```text
/recordings/
├── camera-0/
│   ├── segment000000.h264
│   ├── segment000001.h264
│   └── manifests/
│
├── camera-1/
│   ├── segment000000.h264
│   ├── segment000001.h264
│   └── manifests/
│
└── camera-2/
    ├── segment000000.h264
    ├── segment000001.h264
    └── manifests/
```

The exact storage layout is not yet locked.

---

# 17. Controller Integration for Multiple Cameras

The controller currently models:

```text
Node
└── Service
```

and `edge-video` is one service.

Do NOT turn each camera into a separate controller service.

The desired model is:

```text
Node
└── edge-video
    ├── camera-0
    ├── camera-1
    └── camera-2
```

The controller service configuration should eventually contain camera-specific configuration and status.

Example conceptual configuration:

```json
{
  "cameras": [
    {
      "id": "camera-0",
      "backend": "libcamera",
      "enabled": true,
      "width": 1920,
      "height": 1080,
      "framerate": 30,
      "bitrate": 12000000
    },
    {
      "id": "camera-1",
      "backend": "v4l2",
      "enabled": true,
      "device": "/dev/video1"
    }
  ]
}
```

This is a design target, not an implementation currently present.

---

# 18. GUI Requirements

The eventual controller GUI must remain generic.

It must not assume:

```text
edge-audio
```

is the only service.

Likewise, the edge-video GUI/configuration must not assume:

```text
one camera
```

forever.

The intended hierarchy is:

```text
Node
  |
  +-- Services
        |
        +-- edge-audio
        +-- edge-gps
        +-- edge-video
              |
              +-- Cameras
```

Camera-specific configuration should eventually be dynamically discovered/configured.

---

# 19. Controller Stale Nodes

The following incorrect/stale node IDs were identified:

```text
30e85ff915dd
9be1d95791e8
c770291ec0f6
test-node-01
```

There is also the previously created Docker-container node:

```text
fa845db26f12
```

if it still exists in the database.

The correct physical nodes are:

```text
pi4SSD
pi4nVME
```

The stale nodes should eventually be removed.

---

# 20. Controller Node Deletion — Future Work

The current `edge-controller` API has node creation, retrieval, service registration, configuration, status, and calibration operations.

It currently does not expose a proper:

```text
DELETE /api/v1/nodes/{node_id}
```

operation.

Do not manually delete database records as the long-term solution.

Future controller work should add:

```text
DELETE /api/v1/nodes/{node_id}
```

and an explicit administrative GUI action.

Node deletion should cascade to the node's services and associated records according to the existing SQLAlchemy relationships.

Do NOT automatically delete nodes merely because they are offline.

This is primarily an `edge-controller` task, not an edge-video task.

---

# 21. Current Configuration

Current tested values:

```text
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

Controller:

```text
EDGE_CONTROLLER_URL=http://spoo-lin.spoocannon.com:8080
```

The service identity is:

```text
EDGE_SERVICE_ID=edge-video
EDGE_SERVICE_NAME=edge-video
EDGE_SERVICE_VERSION=0.1.0
```

Physical node identity is obtained through the host UTS namespace in the normal deployment.

---

# 22. Health Endpoint

Current health port:

```text
8090
```

Expected local endpoint:

```text
http://127.0.0.1:8090/health
```

The health service reports runtime state from the video pipeline.

---

# 23. Current Known Issues

These are known and intentionally not blockers for the current commit:

### 23.1 FFmpeg raw-H.264 timestamp warnings

```text
Timestamps are unset in a packet for stream 0
```

Deferred.

### 23.2 HLS latency

Current observed latency:

```text
~8 seconds
```

Deferred.

### 23.3 Client disconnect logging

A browser/VLC/client disconnect can produce:

```text
ConnectionResetError: [Errno 104] Connection reset by peer
```

This is not currently considered a media pipeline failure.

It can later be handled more cleanly in the HTTP streaming layer.

### 23.4 Single-camera architecture

Current limitation.

Must be redesigned for multi-camera support.

### 23.5 USB/V4L2 cameras

Not supported yet.

Requires camera backend abstraction.

### 23.6 GPS/PPS authoritative timestamps

Not implemented yet.

Current timestamps remain explicitly unsynchronized.

### 23.7 Server-side evidence ingestion

Not implemented.

### 23.8 Server-side media gateway

Not implemented.

### 23.9 AI video analysis

Not implemented.

---

# 24. Evidence Architecture That Must Not Be Broken

Future development must preserve this priority:

```text
AUTHORITATIVE EVIDENCE
        |
        v
rpicam / camera backend
        |
        v
encoded capture
        |
        v
local evidence writer
        |
        v
fsync
        |
        v
SHA-256
        |
        v
immutable manifest
```

Live streaming is secondary:

```text
capture
   |
   +--> authoritative evidence
   |
   +--> disposable live stream
```

The live path must never be allowed to compromise evidence capture.

Likewise, future AI analysis must consume a read-only copy/replica of evidence rather than modifying the authoritative original.

---

# 25. Future AI Legal Integration

The eventual purpose of edge-video is not simply surveillance or streaming.

It is an evidence-producing edge service for the AI Legal platform.

Future pipeline:

```text
Camera
   |
   v
Authoritative local evidence
   |
   +--> hash/manifest
   |
   +--> timestamp authority
   |
   +--> server replication
   |
   +--> event markers
   |
   +--> AI analysis
   |
   +--> OCR
   |
   +--> object/person/vehicle detection
   |
   +--> incident correlation
```

The original evidence must remain immutable.

AI-generated interpretation must remain distinguishable from the original evidence.

---

# 26. Recommended Development Order

Future work should proceed in this order.

## Phase 0 — Commit current working state

Before further development:

1. Commit the currently working edge-video state to ADO `master`.
2. Ensure `uts: host` is included.
3. Ensure the current controller registration behavior is included.
4. Ensure current HLS/evidence behavior is included.
5. Push/synchronize the current state to GitHub.
6. Verify GitHub matches the committed ADO source.

Do not start the multi-camera redesign until this baseline is preserved.

---

## Phase 1 — Reconcile repository documentation/code metadata

Before functional redesign, reconcile any stale documentation or metadata with the actual runtime implementation.

In particular, verify:

```text
README evidence format
manifest media_pipeline fields
HLS/live transport description
recording storage description
configuration examples
```

The runtime currently uses:

```text
raw H.264 evidence segments
HLS live output
```

and this must be represented consistently throughout the repository.

---

## Phase 2 — Camera abstraction

Refactor the current single-camera `Camera` class into a camera management abstraction.

Goals:

```text
discover cameras
identify backend
identify device
report capabilities
select camera
validate configuration
```

The first backends should be:

```text
libcamera
v4l2
```

Do not break the currently working OV5647/libcamera implementation while adding V4L2.

---

## Phase 3 — USB camera support

Implement generic V4L2 discovery and capture.

Test with:

```text
one USB camera
```

then:

```text
one Pi CSI + one USB camera
```

then:

```text
two USB cameras
```

where hardware permits.

---

## Phase 4 — Multi-camera pipeline

Move from:

```text
one MediaPipeline
```

to:

```text
CameraPipeline[]
```

Each camera pipeline must independently manage:

```text
capture
evidence
manifest
live stream
status
shutdown
failure state
```

A failure of one camera must not unnecessarily stop the other cameras.

---

## Phase 5 — Multi-camera controller status/configuration

Extend edge-video's controller payloads to represent multiple cameras.

The controller should remain generic:

```text
Node
└── Service
    └── service-specific configuration/status
```

Do not create camera-specific controller services.

---

## Phase 6 — Controller GUI camera management

Add dynamic camera discovery/configuration to the controller GUI.

The GUI should eventually permit:

```text
enable/disable camera
resolution
framerate
bitrate
backend/device selection
stream enablement
evidence settings
camera naming
```

Configuration must remain constrained by actual discovered camera capabilities.

---

## Phase 7 — Evidence/timestamp architecture

After multi-camera operation is stable:

1. Resolve raw-H.264 timestamp handling.
2. Integrate edge-gps/PPS time authority.
3. Define common timestamp envelope.
4. Preserve monotonic timing.
5. Clearly identify synchronized vs unsynchronized evidence.
6. Ensure manifests remain cryptographically verifiable.

---

## Phase 8 — Server-side evidence pipeline

Later:

```text
Pi local evidence
       |
       v
server ingestion
       |
       v
verification
       |
       v
immutable storage
```

Required future components include:

```text
upload acknowledgements
verification
retention policy
replication
failure/retry handling
event markers
```

---

## Phase 9 — Server-side media gateway

Later evaluate:

```text
MediaMTX
```

or equivalent.

The Pi should remain capable of local evidence capture even if the network or server media gateway is unavailable.

---

## Phase 10 — AI analysis

Only after the evidence architecture is stable:

```text
read-only evidence replica
        |
        v
AI workers
        |
        +--> object detection
        +--> OCR
        +--> scene analysis
        +--> event detection
        +--> incident correlation
```

AI results must never alter authoritative evidence.

---

# 27. Current Definition of Done

The current edge-video MVP is considered sufficiently functional when all of the following remain true:

```text
[PASS] Pi CSI camera discovered
[PASS] OV5647 capture works
[PASS] H.264 hardware capture works
[PASS] 1920x1080 @ 30 FPS works
[PASS] local evidence recording works
[PASS] 60-second segmentation works
[PASS] SHA-256 generation works
[PASS] JSON manifests work
[PASS] controller node registration works
[PASS] controller service registration works
[PASS] controller configuration retrieval works
[PASS] controller status updates work
[PASS] physical Pi hostname used as node identity
[PASS] HLS live stream works
[PASS] evidence remains independent of live stream
[PASS] container restarts automatically
[PASS] health endpoint exists
```

Current intentional limitations:

```text
[DEFERRED] USB/V4L2 camera support
[DEFERRED] multiple simultaneous cameras
[DEFERRED] GPS/PPS authoritative time
[DEFERRED] timestamp warning cleanup
[DEFERRED] HLS latency optimization
[DEFERRED] server-side evidence ingestion
[DEFERRED] server media gateway
[DEFERRED] AI video analysis
```

---

# 28. Immediate Next Session Starting Point

When continuing development in a new conversation:

1. Treat this document as the handoff baseline.
2. Treat the committed ADO/GitHub version as authoritative.
3. Verify the `uts: host` deployment change exists.
4. Do not revisit the already-resolved controller registration problem unless new evidence shows regression.
5. Do not introduce a new node-identity mechanism.
6. Do not replace the authoritative evidence path with the live-stream path.
7. Do not redesign the current working HLS implementation merely to support the next feature.
8. Begin with **camera abstraction**.
9. Add **V4L2/USB discovery** without breaking libcamera.
10. Then implement **multi-camera pipelines**.
11. Then integrate multi-camera configuration/status with the existing generic controller.
12. Keep edge-controller node deletion as a separate controller task.

---

# 29. Architectural Target

The eventual edge-video architecture should converge toward:

```text
                         Physical Raspberry Pi
                                  |
                                  v
                              edge-video
                                  |
                +-----------------+-----------------+
                |                 |                 |
             Camera 0          Camera 1          Camera N
             libcamera           V4L2             V4L2/...
                |                 |                 |
                v                 v                 v
          Capture Pipeline   Capture Pipeline   Capture Pipeline
                |                 |                 |
          +-----+-----+     +-----+-----+     +-----+-----+
          |           |     |           |     |           |
       Evidence     Live  Evidence    Live  Evidence    Live
          |           |     |           |     |           |
          v           v     v           v     v           v
       SHA-256      HLS   SHA-256      HLS  SHA-256      HLS
          |                 |                 |
          +-----------------+-----------------+
                            |
                            v
                    Controller status/config
                            |
                            v
                     Server-side systems
                            |
             +--------------+--------------+
             |              |              |
          Evidence         AI          Media Gateway
          ingestion      analysis
```

The non-negotiable architectural rule remains:

```text
AUTHORITATIVE EVIDENCE > LIVE STREAM > AI ANALYSIS
```

The live stream and AI subsystems are consumers of the camera data. They are never allowed to become the authoritative evidence source.
