import logging
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level, structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict, logger_factory=structlog.stdlib.LoggerFactory(),
)
