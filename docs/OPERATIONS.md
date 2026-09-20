# Operations

## Identify camera

```bash
rpicam-hello --list-cameras
```

## Test capture

```bash
rpicam-still -t 2000 -o /tmp/camera-test.jpg
```

## Inspect V4L2

```bash
v4l2-ctl --all -d /dev/video0
v4l2-ctl --list-formats-ext -d /dev/video0
```

Do not use `/dev/video0` as the camera identity. The sensor/camera index from rpicam is authoritative for camera selection; V4L2 is an underlying interface.

## Inspect service

```bash
docker logs -f edge-video
curl http://127.0.0.1:8090/status
```

## Inspect temporal integration

Capture Time Context is obtained from the local `edge-time` instance by `edge-video` at the evidence boundary. The controller is not involved in temporal acquisition.

For temporal troubleshooting, verify the local `edge-time` health/status endpoints and then inspect the `edge-video` logs for context acquisition or fallback messages. Loss of `edge-time` must not stop authoritative video capture or evidence finalization; the evidence manifest records temporal-context unavailability when applicable.
