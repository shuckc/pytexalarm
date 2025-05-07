import pytest
import pytest_asyncio

from typing import Any

from aiohttp.test_utils import TestClient
from pytest_aiohttp import AiohttpClient

from pytexalarm.webpanel import get_web_app
from pytexalarm.pialarm import get_panel_decoder, PanelDecoder

# $ pip install pytest-aiohttp


@pytest.fixture
def mock_panel() -> PanelDecoder:
    panel = get_panel_decoder("Elite 24")
    return panel


@pytest_asyncio.fixture
async def webui_client(
    mock_panel: PanelDecoder, aiohttp_client: AiohttpClient
) -> TestClient[Any, Any]:
    app = get_web_app(mock_panel)
    return await aiohttp_client(app)


@pytest.mark.asyncio
async def test_webpage(
    mock_panel: PanelDecoder, webui_client: TestClient[Any, Any]
) -> None:
    resp = await webui_client.get("/")
    assert resp.status == 200
    assert "Elite 24" in await resp.text()
