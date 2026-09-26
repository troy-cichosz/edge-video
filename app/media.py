import logging
import subprocess
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MediaPipeline:
    """
    Owns the single CSI-camera capture process and fans its encoded H.264
    bitstream out to the authoritative evidence path and optional live stream.

    The camera is opened exactly once by rpicam-vid.

    Evidence is authoritative:
      rpicam H.264 stdout -> evidence ffmpeg stdin

    Live streaming is disposable:
      rpicam H.264 stdout -> bounded queue -> live ffmpeg stdin

    If the live branch fails or falls behind, evidence capture continues.
    """

    def __init__(self, config):
        self.config = config

        self.capture_process = None
        self.evidence_process = None
        self.live_process = None

        self._reader = None
        self._stop = threading.Event()

        self.live_enabled = bool(
            config.enable_stream
        )
        self.live_error = None

        self.started_at = None
        self.started_monotonic_ns = None

    def capture_command(self):
        command = [
            self.config.rpicam_bin,
            "--camera",
            str(self.config.camera_index),
            "--timeout",
            "0",
            "--nopreview",
            "--width",
            str(self.config.width),
            "--height",
            str(self.config.height),
            "--framerate",
            str(self.config.framerate),
            "--bitrate",
            str(self.config.bitrate),
            "--codec",
            "h264",
            "-o",
            "-",
        ]

        if self.config.inline_headers:
            command.insert(-2, "--inline")

        return command

    def evidence_command(self):
        pattern = str(
            self.config.evidence_root / "segment%06d.h264"
        )

        return [
            self.config.ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "warning",

            "-f",
            "h264",
            "-framerate",
            str(self.config.framerate),
            "-i",
            "pipe:0",

            "-an",
            "-c:v",
            "copy",

            "-f",
            "segment",
            "-segment_time",
            str(self.config.segment_seconds),
            "-segment_format",
            "h264",

            pattern,
        ]

    def live_command(self):
        if not self.config.enable_stream:
            return None

        playlist = (
            self.config.live_root
            / "index.m3u8"
        )

        segment_pattern = (
            self.config.live_root
            / "segment%03d.ts"
        )

        return [
            self.config.ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "warning",

            "-f",
            "h264",
            "-framerate",
            str(self.config.framerate),
            "-fflags",
            "+genpts",
            "-i",
            "pipe:0",

            "-an",
            "-c:v",
            "copy",

            "-f",
            "hls",
            "-hls_time",
            str(self.config.hls_segment_seconds),
            "-hls_list_size",
            str(self.config.hls_segment_count),
            "-hls_flags",
            "delete_segments+append_list+omit_endlist",
            "-hls_segment_filename",
            str(segment_pattern),

            str(playlist),
        ]

    def start(self):
        self.config.evidence_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.started_at = datetime.now(timezone.utc)


        if self.config.enable_stream:
            self.config.live_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            for path in self.config.live_root.glob("*"):
                try:
                    path.unlink()
                except OSError:
                    logger.warning(
                        "Unable to remove stale live-stream file: %s",
                        path,
                    )


        import time

        self.started_monotonic_ns = time.monotonic_ns()

        self.evidence_process = subprocess.Popen(
            self.evidence_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=None,
        )

        if self.live_enabled:
            self._start_live_process()

        self.capture_process = subprocess.Popen(
            self.capture_command(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=None,
            bufsize=0,
        )

        self._reader = threading.Thread(
            target=self._read_capture,
            name="edge-video-media-reader",
            daemon=True,
        )
        self._reader.start()


        logger.info(
            "Media pipeline started: %s",
            " ".join(self.capture_command()),
        )

        logger.info(
            "Evidence pipeline: %s",
            " ".join(self.evidence_command()),
        )

        if self.live_enabled:
            logger.info(
                "Live stream pipeline: %s",
                " ".join(self.live_command()),
            )
        else:
            logger.info(
                "Live stream disabled"
            )

    def _start_live_process(self):
        command = self.live_command()

        if not command:
            return

        try:
            self.live_process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=None,
                bufsize=0,
            )

            self.live_error = None

        except Exception as exc:
            self.live_process = None
            self.live_error = str(exc)

            logger.exception(
                "Unable to start live stream"
            )

    def _read_capture(self):
        """
        Read encoded H.264 from rpicam once and distribute it.

        Evidence is authoritative and is written synchronously.

        The live HLS branch receives the same encoded H.264 data,
        but failures in the live branch never terminate evidence capture.
        """
        capture = self.capture_process
        evidence = self.evidence_process
        live = self.live_process

        if not capture or not capture.stdout:
            return

        if not evidence or not evidence.stdin:
            logger.error(
                "Evidence pipeline is unavailable"
            )
            return

        try:
            while not self._stop.is_set():
                chunk = capture.stdout.read(64 * 1024)

                if not chunk:
                    break

                # Evidence is authoritative.
                try:
                    evidence.stdin.write(chunk)
                    evidence.stdin.flush()
                except (BrokenPipeError, OSError):
                    logger.error(
                        "Evidence FFmpeg pipe closed"
                    )
                    break

                # Live HLS is best-effort.
                if self.live_enabled and live and live.stdin:
                    if live.poll() is not None:
                        self.live_error = (
                            f"live ffmpeg exited with code "
                            f"{live.returncode}"
                        )
                        continue

                    try:
                        live.stdin.write(chunk)
                        live.stdin.flush()
                    except (BrokenPipeError, OSError) as exc:
                        self.live_error = str(exc)
                        logger.warning(
                            "Live HLS pipe failed: %s",
                            exc,
                        )

            try:
                evidence.stdin.close()
            except Exception:
                pass

            if live and live.stdin:
                try:
                    live.stdin.close()
                except Exception:
                    pass

        except Exception:
            logger.exception(
                "Media capture fan-out failed"
            )
        finally:
            try:
                if evidence.stdin and not evidence.stdin.closed:
                    evidence.stdin.close()
            except Exception:
                pass

            logger.info(
                "Media capture reader stopped"
            )

    def capture_alive(self):
        return bool(
            self.capture_process
            and self.capture_process.poll() is None
        )

    def evidence_alive(self):
        return bool(
            self.evidence_process
            and self.evidence_process.poll() is None
        )

    def live_alive(self):
        if not self.live_enabled:
            return False

        return bool(
            self.live_process
            and self.live_process.poll() is None
        )

    def stop(self):
        self._stop.set()

        if self.capture_process:
            if self.capture_process.poll() is None:
                self.capture_process.terminate()

            try:
                self.capture_process.wait(
                    timeout=10
                )
            except subprocess.TimeoutExpired:
                self.capture_process.kill()

        if self._reader:
            self._reader.join(timeout=5)

        if self.evidence_process:
            try:
                if (
                    self.evidence_process.stdin
                    and not self.evidence_process.stdin.closed
                ):
                    self.evidence_process.stdin.close()
            except Exception:
                pass

            if self.evidence_process.poll() is None:
                try:
                    self.evidence_process.wait(
                        timeout=10
                    )
                except subprocess.TimeoutExpired:
                    self.evidence_process.kill()

        if self.live_process:
            try:
                if (
                    self.live_process.stdin
                    and not self.live_process.stdin.closed
                ):
                    self.live_process.stdin.close()
            except Exception:
                pass

            if self.live_process.poll() is None:
                try:
                    self.live_process.wait(
                        timeout=5
                    )
                except subprocess.TimeoutExpired:
                    self.live_process.kill()
