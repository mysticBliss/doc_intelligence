from typing import Protocol, runtime_checkable
from app.domain.models import DIPRequest, DIPResponse


@runtime_checkable
class DIPClientPort(Protocol):
    """Port defining the contract for the Downstream Intelligence Processing (DIP) service."""

    async def generate(self, request: DIPRequest) -> DIPResponse:
        ...