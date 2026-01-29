

NO_PROPAGATE_LOGGERS = (
    'uvicorn.access',
    'watchfiles.main',
)
LOGGER_FORMAT = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | '
    '<level>{level: <8}</level> | '
    'cid=<cyan>{extra[correlation_id]}</cyan> | '
    '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | '
    '<level>{message}</level>'
)

DOCUMENTATION_URLS = {
    'openapi_url': '/openapi.json',
    'redoc_url': '/redoc',
    'docs_url': '/swagger_ui',
}
