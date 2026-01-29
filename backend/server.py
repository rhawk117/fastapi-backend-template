from typing import Final

import uvicorn

from backend.config import get_app_config

ASGI_APP_MODULE: Final[str] = 'backend.main:app'
HTTP_BACKEND: Final[str] = 'httptools'


def main() -> None:
    print('[entrypoint] Starting uvicorn server.')
    runtime_config = get_app_config()

    server = runtime_config.server
    uvicorn.run(
        ASGI_APP_MODULE,
        host=server.HOST,
        port=server.PORT,
        reload=server.RELOAD,
        workers=server.WORKERS,
        proxy_headers=server.PROXY_HEADER,
        timeout_keep_alive=server.TIMEOUT_KEEP_ALIVE,
        http=HTTP_BACKEND,
        server_header=server.SERVER_HEADER,
        date_header=server.DATE_HEADER,
    )
    print('[shutdown] Server stopped.')


if __name__ == '__main__':
    main()
