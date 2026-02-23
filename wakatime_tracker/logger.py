import logging
import sys
from typing import Any, Callable

import structlog
from orjson import orjson
from structlog.typing import Processor

from wakatime_tracker.config import LoggingSettings

ProcessorType = Callable[[structlog.types.WrappedLogger, str, structlog.types.EventDict], str | bytes]


def additionally_serialize(obj: Any) -> Any:
    try:
        return str(obj)
    except Exception:
        raise TypeError(f"TypeError: Type is not JSON serializable: {type(obj)}")


def serialize_to_json(data: Any, default: Any) -> str:
    return orjson.dumps(data, default=additionally_serialize).decode()


def get_render_processor(
    render_json_logs: bool = False, serializer: Callable[..., str | bytes] = serialize_to_json, colors: bool = True
) -> ProcessorType:
    if render_json_logs:
        return structlog.processors.JSONRenderer(serializer=serializer)
    return structlog.dev.ConsoleRenderer(colors=colors)


def configure_logging(config: LoggingSettings) -> None:
    """Configuring structlog logging"""

    common_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=True),
        structlog.contextvars.merge_contextvars,
        # structlog.processors.dict_tracebacks,
        structlog.processors.CallsiteParameterAdder(
            (structlog.processors.CallsiteParameter.FILENAME, structlog.processors.CallsiteParameter.LINENO)
        ),
    ]
    structlog_processors: list[Processor] = [
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.UnicodeDecoder(),  # convert bytes to str
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        # structlog.processors.format_exc_info,
    ]

    logging_console_processors = (
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        get_render_processor(render_json_logs=config.render_json_logs, colors=True),
    )

    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("aiogram_dialog").setLevel(logging.WARNING)
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("multipart").setLevel(logging.INFO)
    logging.getLogger("python_multipart.multipart").setLevel(logging.INFO)

    # Removing existing logging handlers
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)

    handler.set_name("default")
    handler.setLevel(config.level)
    console_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=common_processors, processors=logging_console_processors  # type: ignore
    )
    handler.setFormatter(console_formatter)

    handlers: list[logging.Handler] = [handler]

    logging.basicConfig(handlers=handlers, level=config.level)
    structlog.configure(
        processors=common_processors + structlog_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore  # noqa
        cache_logger_on_first_use=True,
    )
