import json
import logging
import re
import subprocess

logger = logging.getLogger(__name__)


class Camera:
    def __init__(self, config):
        self.config = config

    def list_cameras(self):
        result = subprocess.run(
            [self.config.rpicam_bin, "--list-cameras"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "rpicam-hello unavailable")
        return self.parse_list(result.stdout)

    @staticmethod
    def parse_list(text):
        cameras = []
        current = None
        for line in text.splitlines():
            match = re.match(r"\s*(\d+)\s*:\s*([^\[]+)\s*\[([^\]]+)\]\s*\((.+)\)", line)
            if match:
                current = {
                    "index": int(match.group(1)),
                    "sensor": match.group(2).strip(),
                    "native": match.group(3).strip(),
                    "path": match.group(4).strip(),
                    "modes": [],
                }
                cameras.append(current)
                continue
            mode = re.search(r"'([^']+)'\s*:\s*([^\[]+)\[([^\]]+)\s*-\s*([^\]]+)\]", line)
            if mode and current:
                current["modes"].append({
                    "format": mode.group(1),
                    "size": mode.group(2).strip(),
                    "fps": mode.group(3).strip(),
                    "crop": mode.group(4).strip(),
                })
        return cameras

    def selected_camera(self):
        cameras = self.list_cameras()
        for camera in cameras:
            if camera["index"] == self.config.camera_index:
                return camera
        raise RuntimeError(f"Camera index {self.config.camera_index} not found")
