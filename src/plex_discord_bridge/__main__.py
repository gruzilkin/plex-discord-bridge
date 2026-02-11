import logging
import sys

from aiohttp import web
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from pythonjsonlogger import jsonlogger

from .config import settings
from .handler import handle_webhook


def setup_logging() -> None:
    resource = Resource.create({"service.name": settings.otel_service_name})

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    root.addHandler(stdout_handler)

    otel_provider = LoggerProvider(resource=resource)
    set_logger_provider(otel_provider)
    otel_provider.add_log_record_processor(
        BatchLogRecordProcessor(
            OTLPLogExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
    )

    otel_handler = LoggingHandler(level=logging.NOTSET, logger_provider=otel_provider)
    otel_handler.setFormatter(jsonlogger.JsonFormatter(json_ensure_ascii=False))
    root.addHandler(otel_handler)


def main() -> None:
    setup_logging()

    app = web.Application()
    app.router.add_post("/", handle_webhook)

    web.run_app(app, port=8080)


if __name__ == "__main__":
    main()
