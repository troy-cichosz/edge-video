# edge-video — Sprint Status

**Current sprint:** Evidence-facing temporal integration  
**Status:** COMPLETE / VERIFIED  
**Development phase:** Phase 1 evidence capture MVP → common evidence model

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

## Completed This Sprint

1. Acquire Capture Time Context at the appropriate evidence boundary.
2. Associate temporal context with evidence manifests/metadata.
3. Preserve monotonic timing and temporal uncertainty.
4. Distinguish context acquisition time from physical camera exposure timing.
5. Preserve local operation when edge-time is unavailable.
6. Verify runtime and applicable failure/recovery behavior.
7. Update documentation after verification.

## Verified Behavior

Normal operation acquires local Capture Time Context and associates it with the finalized evidence manifest. If edge-time is unavailable, video capture and evidence finalization continue and temporal-context unavailability is recorded rather than making the temporal service a capture dependency.

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

Temporal integration is complete and verified. The next platform increment is common evidence-model and manifest integration across edge-video and edge-audio, preserving evidence immutability, SHA-256 integrity, monotonic timing, temporal provenance, uncertainty, authority/source information, and the distinction between context acquisition and physical exposure.
