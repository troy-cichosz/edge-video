import json
import logging
import platform
import socket
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


class ControllerClient:
    def __init__(self, config):
        self.base_url = config.controller_url
        self.timeout = config.controller_timeout
        self.node_id = config.node_id
        self.service_id = config.service_id
        self.service_name = config.service_name
        self.service_version = config.service_version

        logger.info(
            "Controller client configured: base_url=%s node_id=%s "
            "service_id=%s service_version=%s",
            self.base_url,
            self.node_id,
            self.service_id,
            self.service_version,
        )

    def _request(self, method, path, payload=None):
        if not self.base_url:
            raise RuntimeError(
                "EDGE_CONTROLLER_URL is not configured"
            )

        url = f"{self.base_url}{path}"

        data = (
            None
            if payload is None
            else json.dumps(payload).encode("utf-8")
        )

        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        logger.info(
            "Controller request: %s %s payload=%s",
            method,
            url,
            payload,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read()

                logger.info(
                    "Controller response: %s %s -> HTTP %s",
                    method,
                    url,
                    response.status,
                )

                if not raw:
                    return None

                return json.loads(raw.decode("utf-8"))

        except urllib.error.HTTPError as exc:
            response_body = ""

            try:
                response_body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                pass

            logger.error(
                "Controller HTTP error: %s %s -> HTTP %s body=%s",
                method,
                url,
                exc.code,
                response_body,
            )

            raise

        except urllib.error.URLError as exc:
            logger.error(
                "Controller connection error: %s %s -> %s",
                method,
                url,
                exc,
            )

            raise

        except Exception:
            logger.exception(
                "Controller request failed unexpectedly: %s %s",
                method,
                url,
            )

            raise

    def register(self):
        if not self.base_url:
            logger.info("Controller registration disabled")
            return False

        logger.info(
            "Beginning controller registration: node_id=%s service_id=%s",
            self.node_id,
            self.service_id,
        )

        try:
            self._register_node()
            self._register_service()
            self.update_status(
                "online",
                self.status_payload(),
            )

            logger.info(
                "Controller registration completed successfully: "
                "node_id=%s service_id=%s",
                self.node_id,
                self.service_id,
            )

            return True

        except Exception as exc:
            logger.warning(
                "Controller registration failed: node_id=%s "
                "service_id=%s error=%s",
                self.node_id,
                self.service_id,
                exc,
            )

            return False

    def _register_node(self):
        try:
            result = self._request(
                "GET",
                f"/api/v1/nodes/{self.node_id}",
            )

            logger.info(
                "Controller node already exists: node_id=%s result=%s",
                self.node_id,
                result,
            )

            return

        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise

            logger.info(
                "Controller node does not exist yet; creating node: "
                "node_id=%s",
                self.node_id,
            )

        self._request(
            "POST",
            "/api/v1/nodes",
            {
                "node_id": self.node_id,
                "hostname": socket.gethostname(),
                "platform": (
                    f"{platform.system().lower()}-"
                    f"{platform.machine()}"
                ),
            },
        )

        logger.info(
            "Controller node registration completed: node_id=%s",
            self.node_id,
        )

    def _register_service(self):
        services = self._request(
            "GET",
            f"/api/v1/nodes/{self.node_id}/services",
        ) or []

        for service in services:
            if service.get("service_id") == self.service_id:
                logger.info(
                    "Controller service already exists: node_id=%s "
                    "service_id=%s",
                    self.node_id,
                    self.service_id,
                )
                return

        self._request(
            "POST",
            f"/api/v1/nodes/{self.node_id}/services",
            {
                "service_id": self.service_id,
                "name": self.service_name,
                "version": self.service_version,
            },
        )

        logger.info(
            "Controller service registration completed: node_id=%s "
            "service_id=%s",
            self.node_id,
            self.service_id,
        )

    def get_configuration(self):
        try:
            result = self._request(
                "GET",
                (
                    f"/api/v1/nodes/{self.node_id}"
                    f"/services/{self.service_id}"
                    "/configuration"
                ),
            )

            return (
                result.get("configuration", {})
                if result
                else {}
            )

        except Exception as exc:
            logger.warning(
                "Controller configuration unavailable: "
                "node_id=%s service_id=%s error=%s",
                self.node_id,
                self.service_id,
                exc,
            )

            return {}

    def update_status(self, status, details=None):
        if not self.base_url:
            return False

        try:
            self._request(
                "PUT",
                (
                    f"/api/v1/nodes/{self.node_id}"
                    f"/services/{self.service_id}"
                    "/status"
                ),
                {
                    "status": status,
                    "data": details or {},
                },
            )

            return True

        except Exception as exc:
            logger.warning(
                "Unable to update controller status: "
                "node_id=%s service_id=%s error=%s",
                self.node_id,
                self.service_id,
                exc,
            )

            return False

    def status_payload(self):
        return {
            "service": self.service_id,
        }