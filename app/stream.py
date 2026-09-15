import logging

logger = logging.getLogger(__name__)


class Streamer:
    """
    Live-stream interface for edge-video.

    The camera remains owned exclusively by MediaPipeline.

    The live stream is exposed locally by HealthServer as HLS:
        /stream
        /stream/index.m3u8
    """

    def __init__(self, config, media):
        self.config = config
        self.media = media

    def start(self):
        if not self.config.enable_stream:
            logger.info(
                "Live stream disabled"
            )
            return

        logger.info(
            "Live HLS stream enabled at /stream"
        )

    def status(self):
        if not self.config.enable_stream:
            return {
                "enabled": False,
                "alive": False,
                "protocol": None,
                "endpoint": None,
            }

        return {
            "enabled": True,
            "alive": self.media.live_alive(),
            "protocol": "hls",
            "endpoint": "/stream",
            "playlist": "/stream/index.m3u8",
            "error": self.media.live_error,
        }

    def stop(self):
        return None