# edge-video — Sprint Status

**Current sprint:** Evidence-facing temporal integration  
**Status:** NEXT / READY FOR DEVELOPMENT  
**Development phase:** Phase 1 evidence capture MVP → temporal integration

## Sprint Objective

Integrate local edge-time Capture Time Context into the operational video evidence pipeline without changing the authoritative raw evidence model.

## Completed Before This Sprint

- Raspberry Pi CSI/OV5647 capture
- Hardware H.264 capture
- 1920x1080 / configured 30 FPS / 12 Mbps capture
- Local 60-second evidence segmentation and finalization
- SHA-256 manifests
- Optional HLS live stream
- Controller registration/configuration/status integration
- Health endpoint and restart behavior

## Current Work

1. Acquire Capture Time Context at the appropriate video-capture boundary.
2. Associate temporal context with evidence manifests/metadata.
3. Preserve monotonic timing and temporal uncertainty.
4. Distinguish context acquisition time from physical camera exposure timing.
5. Preserve local operation when edge-time is unavailable.
6. Verify runtime and applicable failure/recovery behavior.
7. Update documentation after verification.

## Constraints

The controller must not become the timestamp broker. The raw H.264 evidence path must remain authoritative and independent of HLS.

## Deferred

- Multi-camera architecture
- USB/V4L2 backend
- Server-side evidence ingestion
- HLS latency optimization
- AI video analysis
- Production-grade timestamp/container timing resolution

## Handoff

After video temporal integration is verified, move toward common evidence-model and manifest integration across edge-video and edge-audio.
