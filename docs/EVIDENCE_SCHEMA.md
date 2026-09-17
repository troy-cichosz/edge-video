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

The manifest is a sidecar and does not replace timestamps contained in the media container.
