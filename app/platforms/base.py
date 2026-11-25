"""Pluggable platform adapters. Add a platform = add one module + @register."""
from typing import Protocol
from app.models import SourceRecord
from app.services.search_service import Ctx

class PlatformAdapter(Protocol):
    name: str          # spec platform name
    method: str        # how it discovers: shown in README coverage matrix + platform_status
    async def discover(self, ctx: Ctx) -> list[SourceRecord]: ...

REGISTRY: dict[str, PlatformAdapter] = {}

def register(adapter: PlatformAdapter) -> PlatformAdapter:
    REGISTRY[adapter.name] = adapter
    return adapter
