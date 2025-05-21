from typing import Any

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient
from pytest_aiohttp import AiohttpClient

from pytexalarm.pialarm import PanelDecoder, get_panel_decoder
from pytexalarm.webapp import get_web_app

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
