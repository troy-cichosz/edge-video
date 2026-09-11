# edge-video architecture

## Boundaries

`edge-video` owns camera acquisition, recording lifecycle, local evidence integrity, and camera metadata. `edge-controller` owns node/service registration and operational configuration. The eventual AI/legal server owns replicated evidence, indexing, analysis, and user-facing playback.

## Evidence is primary

The network stream is never the authoritative evidence source. A network outage must not stop local capture.

## Clock hierarchy

1. Monotonic clock: ordering and interval measurement.
2. System UTC: current timestamp when GPS is unavailable.
3. GPS/PPS-disciplined UTC: authoritative time once edge-gps supports it.

A later clock authority must not rewrite existing payloads or manifests. Instead, it creates a verifiable relationship between monotonic time and authoritative UTC.

## Segment lifecycle

```text
OPEN
  -> CLOSED
  -> FLUSHED
  -> HASHED
  -> MANIFESTED
  -> READY_FOR_REPLICATION
  -> VERIFIED_CENTRALLY (future)
```

Only completed segments receive manifests. The current open segment is never hashed as final evidence.

## Future replication

A future uploader should:

1. enumerate finalized manifests;
2. upload the exact video payload;
3. upload the manifest;
4. verify server-side SHA-256;
5. receive a durable acknowledgement;
6. retain the local copy according to policy.

## Future analysis

AI analysis must operate on a read-only evidence replica and create derived artifacts/events. It must never modify the original video payload.
