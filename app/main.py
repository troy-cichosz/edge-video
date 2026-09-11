import logging
import signal
import threading

from .camera import Camera
from .config import load_config
from .controller import ControllerClient
from .health import HealthServer
from .media import MediaPipeline
from .recorder import Recorder
from .stream import Streamer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    config = load_config()

    camera = Camera(config)
    info = camera.selected_camera()

    logger.info(
        "Selected camera: %s",
        info,
    )

    controller = ControllerClient(config)

    controller.register()

    controller_config = (
        controller.get_configuration()
    )

    if controller_config:
        logger.info(
            "Controller configuration received: %s",
            controller_config,
        )

        # Configuration merge remains intentionally conservative.
        # Hardware identity remains local and authoritative.

    media = MediaPipeline(config)

    recorder = Recorder(
        config,
        info,
        media,
    )

    streamer = Streamer(
        config,
        media,
    )

    state = {
        "status": "starting",
        "camera": info,
        "recording": False,
        "stream": streamer.status(),
    }

    def status():
        state["stream"] = streamer.status()
        return dict(state)

    health = HealthServer(
        config,
        status,
    )

    health.start()

    stop = threading.Event()

    def handle_signal(_signum, _frame):
        stop.set()

    signal.signal(
        signal.SIGTERM,
        handle_signal,
    )

    signal.signal(
        signal.SIGINT,
        handle_signal,
    )

    try:
        recorder.start()
        streamer.start()

        state.update(
            status="ok",
            recording=True,
        )

        controller.update_status(
            "online",
            status(),
        )

        while not stop.wait(5):
            state["stream"] = streamer.status()

            if not media.capture_alive():
                exit_code = (
                    media.capture_process.returncode
                    if media.capture_process
                    else None
                )

                logger.error(
                    "rpicam-vid exited with code %s",
                    exit_code,
                )

                state.update(
                    status="degraded",
                    recording=False,
                    error=(
                        "rpicam-vid exited with "
                        f"code {exit_code}"
                    ),
                )

                controller.update_status(
                    "degraded",
                    status(),
                )

                break

            if not media.evidence_alive():
                exit_code = (
                    media.evidence_process.returncode
                    if media.evidence_process
                    else None
                )

                logger.error(
                    "Evidence FFmpeg exited with code %s",
                    exit_code,
                )

                state.update(
                    status="degraded",
                    recording=False,
                    error=(
                        "authoritative evidence pipeline "
                        f"exited with code {exit_code}"
                    ),
                )

                controller.update_status(
                    "degraded",
                    status(),
                )

                break

    finally:
        state.update(
            status="stopping",
            recording=False,
        )

        streamer.stop()
        recorder.stop()

        controller.update_status(
            "offline",
            status(),
        )

        health.stop()


if __name__ == "__main__":
    main()