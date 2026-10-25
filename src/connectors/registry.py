import time
from typing import Dict, List, Optional
from src.connectors.base import BaseConnector, ConnectorException
from src.connectors.discourse.connector import DiscourseConnector
from src.connectors.lemmy.connector import LemmyConnector
from src.connectors.devto.connector import DevtoConnector
from src.connectors.ghost.connector import GhostConnector
from src.connectors.webhook.connector import WebhookConnector
from src.connectors.assisted.connector import AssistedConnector
from src.connectors.hashnode.connector import HashnodeConnector
from src.connectors.slack.connector import SlackConnector
from src.connectors.mrss.connector import MRSSConnector


class ConnectorRegistry:
    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._disabled_connectors: set = set()
        self._circuit_breakers: Dict[str, Dict] = {}
        self._register_default_connectors()

    def _register_default_connectors(self):
        self.register(DiscourseConnector())
        self.register(LemmyConnector())
        self.register(DevtoConnector())
        self.register(GhostConnector())
        self.register(WebhookConnector())
        self.register(AssistedConnector())
        self.register(HashnodeConnector())
        self.register(SlackConnector())
        self.register(MRSSConnector())

    def register(self, connector: BaseConnector):
        self._connectors[connector.key] = connector

    def get(self, key: str) -> BaseConnector:
        if key in self._disabled_connectors:
            raise ConnectorException(
                code="CONNECTOR_DISABLED",
                message=f"Kill switch is active for connector: {key}",
                retryable=False,
            )
        if self.is_circuit_open(key):
            raise ConnectorException(
                code="CONNECTOR_CIRCUIT_OPEN",
                message=f"Circuit breaker is OPEN for connector: {key} due to repeated platform errors (in cooldown).",
                retryable=True,
            )
        if key not in self._connectors:
            raise ConnectorException(
                code="DEST_SPEC_VIOLATION",
                message=f"Connector '{key}' not found in registry.",
                retryable=False,
            )
        return self._connectors[key]

    def set_disabled(self, key: str, disabled: bool = True):
        if disabled:
            self._disabled_connectors.add(key)
        else:
            self._disabled_connectors.discard(key)

    def is_disabled(self, key: str) -> bool:
        return key in self._disabled_connectors

    # --- Circuit Breaker System ---
    def record_failure(self, key: str, error_code: str = "ERROR"):
        now = time.time()
        cb = self._circuit_breakers.setdefault(key, {"failures": 0, "status": "closed", "tripped_at": 0.0, "cooldown_seconds": 600})
        cb["failures"] += 1
        cb["last_error"] = error_code
        cb["last_failed_at"] = now
        if cb["failures"] >= 3:
            cb["status"] = "open"
            cb["tripped_at"] = now

    def record_success(self, key: str):
        if key in self._circuit_breakers:
            self._circuit_breakers[key]["failures"] = 0
            self._circuit_breakers[key]["status"] = "closed"

    def is_circuit_open(self, key: str) -> bool:
        if key not in self._circuit_breakers:
            return False
        cb = self._circuit_breakers[key]
        if cb["status"] == "open":
            if (time.time() - cb["tripped_at"]) > cb.get("cooldown_seconds", 600):
                cb["status"] = "half-open"
                return False
            return True
        return False

    def reset_circuit_breaker(self, key: str):
        if key in self._circuit_breakers:
            self._circuit_breakers[key] = {"failures": 0, "status": "closed", "tripped_at": 0.0, "cooldown_seconds": 600}

    def get_circuit_breakers(self) -> Dict[str, Dict]:
        return self._circuit_breakers

    def list_all(self) -> List[Dict]:
        return [
            {
                "key": key,
                "tier": conn.manifest.get("tier", "native"),
                "auth": conn.manifest.get("auth", "none"),
                "capabilities": conn.manifest.get("capabilities", []),
                "disabled": key in self._disabled_connectors,
                "circuit_breaker": self._circuit_breakers.get(key, {"status": "closed", "failures": 0}),
            }
            for key, conn in self._connectors.items()
        ]


registry = ConnectorRegistry()
