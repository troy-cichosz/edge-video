#!/bin/sh
set -eu

echo "=== Camera ==="
rpicam-hello --list-cameras

echo

echo "=== V4L2 ==="
v4l2-ctl --list-devices || true

echo

echo "=== Media ==="
ls -l /dev/media* 2>/dev/null || true

echo

echo "=== Video ==="
ls -l /dev/video* 2>/dev/null || true
