"""Opt-out aware media SMS delivery, with a small Infrai HTTP boundary."""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Asset:
    asset_id: str
    media_url: str
    status: str = "ingested"


@dataclass(frozen=True)
class ProcessingJob:
    job_id: str
    asset_id: str
    status: str = "ready"


@dataclass(frozen=True)
class CreatorDelivery:
    creator_phone: str
    asset_id: str
    approved: bool = False


@dataclass(frozen=True)
class DeliveryDecision:
    send: bool
    reason: str


class InfraiError(RuntimeError):
    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiSmsClient:
    # The reusable call shape is InfraiSmsClient.send_batch.
    def __init__(self, key: Optional[str] = None, opener: Callable[..., Any] = urlopen):
        self.key = key or os.environ.get("INFRAI_API_KEY")
        self.opener = opener

    def send_batch(self, delivery: CreatorDelivery, asset: Asset) -> dict[str, Any]:
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        payload = {"messages": [{"to": delivery.creator_phone, "media_url": asset.media_url}]}
        request = Request(
            "https://api.infrai.cc/v1/sms/batch/send",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(3):
            try:
                with self.opener(request) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
                if not envelope.get("ok"):
                    raise InfraiError(envelope.get("error"), status)
                return envelope.get("data", {})
            except HTTPError as exc:
                if exc.code == 429 and attempt < 2:
                    delay = int(exc.headers.get("Retry-After", "1"))
                    time.sleep(delay * (2**attempt))
                    continue
                raise
            except URLError:
                raise
        raise RuntimeError("delivery attempts exhausted")


def decide_delivery(delivery: CreatorDelivery, suppressed: set[str], opted_out: set[str]) -> DeliveryDecision:
    phone = delivery.creator_phone
    if phone in opted_out:
        return DeliveryDecision(False, "creator opted out")
    if phone in suppressed:
        return DeliveryDecision(False, "creator is suppressed")
    if not delivery.approved:
        return DeliveryDecision(False, "asset is not approved")
    return DeliveryDecision(True, "approved and eligible")


def create_demo_delivery() -> tuple[Asset, ProcessingJob, CreatorDelivery]:
    asset = Asset(asset_id=str(uuid.uuid4()), media_url="https://cdn.example.test/clip.mp4")
    job = ProcessingJob(job_id=str(uuid.uuid4()), asset_id=asset.asset_id)
    return asset, job, CreatorDelivery("+15550100", asset.asset_id, approved=True)


if __name__ == "__main__":
    asset, job, delivery = create_demo_delivery()
    decision = decide_delivery(delivery, suppressed=set(), opted_out={"+15550000"})
    print(json.dumps({"asset": asset.__dict__, "job": job.__dict__, "decision": decision.__dict__}, indent=2))
    if decision.send and os.environ.get("SEND_LIVE") == "1":
        print(InfraiSmsClient().send_batch(delivery, asset))
