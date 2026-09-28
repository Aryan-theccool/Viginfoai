"""FDA MAUDE ingestion via the openFDA device event API."""
from typing import Any

import requests

BASE_URL = "https://api.fda.gov/device/event.json"
TIMEOUT = 30


class MaudeIngestor:
    """Fetch adverse-event (MDR) records for a device from openFDA."""

    def fetch_incidents(self, device_name: str, limit: int = 10) -> list[dict[str, Any]]:
        q = device_name.replace('"', "")
        params = {
            "search": f'device.generic_name:"{q}" OR device.brand_name:"{q}"',
            "limit": max(1, min(limit, 100)),
        }
        resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json().get("results", [])
        incidents: list[dict[str, Any]] = []
        for item in data:
            mdr_texts = item.get("mdr_text") or []
            mdr_text = mdr_texts[0].get("text", "No detailed text available") if mdr_texts else "No detailed text available"
            devices = item.get("device") or [{}]
            device_info = devices[0] if devices else {}
            incidents.append({
                "source": "FDA MAUDE",
                "source_id": item.get("report_number", "UNKNOWN"),
                "title": f"MDR Report: {device_info.get('brand_name', 'Unknown Device')}",
                "text": mdr_text,
                "event_type": item.get("event_type", "Unknown"),
                "date_of_event": item.get("date_of_event", "Unknown"),
                "date_received": item.get("date_received", "Unknown"),
                "manufacturer": device_info.get("manufacturer_d_name", "Unknown"),
                "device_name": device_info.get("generic_name", device_name),
            })
        return incidents
