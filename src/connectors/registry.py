"""Connector registry and dispatch engine."""
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

    def list_all(self) -> List[Dict]:
        return [
            {
                "key": key,
                "tier": conn.manifest.get("tier", "native"),
                "auth": conn.manifest.get("auth", "none"),
                "capabilities": conn.manifest.get("capabilities", []),
                "disabled": key in self._disabled_connectors,
            }
            for key, conn in self._connectors.items()
        ]


registry = ConnectorRegistry()
