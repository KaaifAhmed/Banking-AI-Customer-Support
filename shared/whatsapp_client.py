"""
Shared HTTP client for the WhatsApp Service's outbound send endpoint.
Imported directly by ai-worker and background-worker (see architecture.md —
outbound goes worker -> WhatsApp Service directly, never through Main Service).

Every send is gated by the output guard (docs/ai-system.md §5.1) here,
at the choke point — so no call site can forget the check.
"""
import os
import httpx

from shared.security_guards import output_guard

WHATSAPP_SERVICE_URL = os.environ.get("WHATSAPP_SERVICE_URL", "http://whatsapp-service:3001")


async def send_whatsapp_message(phone: str, text: str) -> dict:
    guard = output_guard(text)
    if not guard["ok"]:
        raise ValueError(f"blocked by output guard: {guard['reason']}")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{WHATSAPP_SERVICE_URL}/whatsapp/send", json={"phone": phone, "text": text})
        response.raise_for_status()
        return response.json()
