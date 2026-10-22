"""Channel adapter: planning does not depend on WAHA."""
import os
from typing import Protocol

import httpx


class MessagingProvider(Protocol):
    def send_text(self, *, session: str, chat_id: str, text: str) -> None: ...


class WahaMessagingProvider:
    def __init__(self, base_url: str, api_key: str, transport=None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.transport = transport

    @classmethod
    def from_env(cls):
        return cls(os.getenv("WAHA_BASE_URL", "http://localhost:3000"),
                   os.getenv("WAHA_API_KEY", ""))

    def send_text(self, *, session: str, chat_id: str, text: str) -> None:
        if not self.api_key:
            raise ValueError("WAHA_API_KEY is not configured")
        with httpx.Client(timeout=5, transport=self.transport, trust_env=False) as client:
            response = client.post(
                f"{self.base_url}/api/sendText",
                headers={"X-Api-Key": self.api_key},
                json={"session": session, "chatId": chat_id, "text": text},
            )
            response.raise_for_status()
