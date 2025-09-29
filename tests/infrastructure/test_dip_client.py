import pytest
from pytest_httpx import HTTPXMock
from app.infrastructure.dip_client import DIPClient
from app.domain.models import DIPChatRequest, ChatMessage

@pytest.fixture
def dip_client() -> DIPClient:
    return DIPClient(base_url="http://test-dip:11434")

async def test_chat_success(dip_client: DIPClient, httpx_mock: HTTPXMock):
    """Test successful chat completion."""
    mock_response = {
        "model": "qwen2.5vl:3b",
        "created_at": "2023-10-26T15:00:00Z",
        "message": {"role": "assistant", "content": "The sky is blue due to Rayleigh scattering."},
        "done": True,
    }
    httpx_mock.add_response(url=f"{dip_client.base_url}/api/chat", json=mock_response)

    chat_request = DIPChatRequest(
        model="qwen2.5vl:3b",
        messages=[ChatMessage(role="user", content="Why is the sky blue?")]
    )

    response = await dip_client.chat(chat_request)

    assert response.message.content == "The sky is blue due to Rayleigh scattering."
    assert response.done is True

async def test_chat_api_error(dip_client: DIPClient, httpx_mock: HTTPXMock):
    """Test handling of a 500 error from the DIP API."""
    httpx_mock.add_response(url=f"{dip_client.base_url}/api/chat", status_code=500)

    chat_request = DIPChatRequest(
        model="qwen2.5vl:3b",
        messages=[ChatMessage(role="user", content="Why is the sky blue?")]
    )

    with pytest.raises(Exception): # httpx raises an exception on 500
        await dip_client.chat(chat_request)