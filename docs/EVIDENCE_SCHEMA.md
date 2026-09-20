# Evidence manifest v1

The manifest schema identifier is `ai-legal.evidence.video.v1`.

Required concepts:

- `evidence_id`: unique identifier for the evidence object.
- `service`, `service_version`: producing software identity.
- `node_id`: producing edge node.
- `capture`: capture interval and clock provenance.
- `camera`: sensor and selected camera identity.
- `video`: payload name, format, dimensions, encoder, byte count and SHA-256.
- `integrity`: hash algorithm and immutability declaration.
- `gps`: reserved for the GPS/PPS-authoritative phase.
- `temporal_provenance`: Capture Time Context acquisition and associated edge-time timing provenance when available.

## Temporal provenance

When local `edge-time` is available at the evidence boundary, the manifest records the Capture Time Context associated with the evidence segment. The context preserves its `context_id`, UTC/monotonic position, selected source and source observation, uncertainty, freshness, synchronization state, authority provenance, consistency state, holdover state, and attestation reference.

Capture Time Context acquisition time is not the exact physical camera exposure time unless a separately defined sensor/frame timing mechanism establishes that relationship. The manifest must not imply that it does.

If `edge-time` is unavailable, the evidence segment remains authoritative and the manifest records temporal-context unavailability while retaining local system/monotonic timing information.

The manifest is a sidecar and does not replace timestamps contained in the media container. It also does not retroactively rewrite the original raw H.264 payload when stronger time authority becomes available.
