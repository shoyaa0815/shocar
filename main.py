import argparse
import uvicorn

from server.app import create_app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shocar web server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = uvicorn.Server(uvicorn.Config(
        create_app(), host=args.host, port=args.port,
        timeout_graceful_shutdown=2,
    ))

    web_host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    if ":" in web_host:
        web_host = f"[{web_host}]"
    print(f"Web: http://{web_host}:{args.port}/", flush=True)
    try:
        server.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
