import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("context_id", "capture_utc", "capture_monotonic_ns", "device_id", "selected_source", "source_observation", "uncertainty_ms", "freshness", "synchronization_state", "authority_id", "authority_source", "consistency_state", "holdover_state", "attestation_sequence", "attestation_record_hash", "attestation_signature")

class EdgeTimeClient:
    def __init__(self, base_url: str, timeout_seconds: int = 2):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout_seconds = timeout_seconds

    def capture_context(self):
        if not self.base_url:
            logger.info("edge-time URL is not configured; temporal context unavailable")
            return None
        request = Request(f"{self.base_url}/time/context", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            missing = [field for field in _REQUIRED_FIELDS if field not in payload]
            if missing:
                logger.warning("edge-time context missing fields: %s", ", ".join(missing))
                return None
            return payload
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            logger.warning("edge-time context unavailable: %s", exc)
            return None
