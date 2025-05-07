from aiohttp import web
import aiohttp_jinja2
import json
import jinja2
from typing import Any

from .pialarm import PanelDecoder, get_panel_decoder


@aiohttp_jinja2.template("template.jinja2")
async def handle_index(request: web.Request) -> Any:
    panel = request.app["panel"]
    return {"panel": panel.decode()}


async def handle_json_raw(request: web.Request) -> Any:
    panel = request.app["panel"]
    text = json.dumps(panel.decode(), indent=4)
    return web.Response(text=text)


@aiohttp_jinja2.template("json.jinja2")
async def handle_json(request: web.Request) -> Any:
    panel = request.app["panel"]
    text = json.dumps(panel.decode(), indent=4)
    return {"json": text}


@aiohttp_jinja2.template("config.jinja2")
async def handle_config(request: web.Request) -> Any:
    panel = request.app["panel"]
    return {"panel": panel.decode()}


@aiohttp_jinja2.template("user-detail.jinja2")
async def handle_user_detail(request: web.Request) -> Any:
    return {"user": ""}


def get_web_app(panel: PanelDecoder) -> web.Application:
    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_config),
            web.get("/user", handle_user_detail),
            web.get("/json", handle_json),
            web.static("/static", "static", show_index=True),
        ]
    )
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))

    app["panel"] = panel
    return app


async def start_server(panel: PanelDecoder, web_port: int) -> web.AppRunner:
    app = get_web_app(panel)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "", web_port)
    await site.start()
    print(f"Serving web interface on {web_port}")
    return runner


if __name__ == "__main__":
    panel = get_panel_decoder("Elite 24")
    web.run_app(get_web_app(panel))
