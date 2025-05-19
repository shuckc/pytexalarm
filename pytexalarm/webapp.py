from aiohttp import web
import aiohttp_jinja2
import json
import jinja2
import argparse
from typing import Any
from .hexdump import hexdump
from .pialarm import PanelDecoder, get_panel_decoder, panel_from_file
from . import DEFAULT_MEMFILE


@aiohttp_jinja2.template("config.jinja2")
async def handle_config(request: web.Request) -> Any:
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


@aiohttp_jinja2.template("memory.jinja2")
async def handle_memory(request: web.Request) -> Any:
    panel = request.app["panel"]
    return {"memory": hexdump(panel.get_mem()), "io": hexdump(panel.get_io())}


def get_web_app(panel: PanelDecoder) -> web.Application:
    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_config),
            web.get("/json", handle_json),
            web.get("/memory", handle_memory),
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
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--mem", help="read saved panel file", default=DEFAULT_MEMFILE)
    parser.add_argument("--banner", help="empty panel from banner")
    args = parser.parse_args()

    panel: PanelDecoder
    if args.mem:
        panel = panel_from_file(args.mem)
    elif args.banner:
        panel = get_panel_decoder(args.banner)
    else:
        panel = get_panel_decoder("Elite 24")

    web.run_app(get_web_app(panel))
