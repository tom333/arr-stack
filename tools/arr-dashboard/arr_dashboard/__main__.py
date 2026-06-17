import uvicorn

from arr_dashboard.app import create_app
from arr_dashboard.settings import load_settings


def main() -> None:
    settings = load_settings()
    host, _, port = settings.bind.partition(":")
    uvicorn.run(
        create_app(settings=settings),
        host=host or "0.0.0.0",
        port=int(port or "8080"),
    )


if __name__ == "__main__":
    main()
