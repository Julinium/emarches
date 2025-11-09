import os, json, logging #, logging.config, threading
from pathlib import Path


from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent

# Thread-local storage to hold request context
# _thread_locals = threading.local()

# def get_request_context():
#     """Return current request context (or empty dict if no request)"""
#     return getattr(_thread_locals, "context", {})


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            # "file": record.pathname,
            # "line": record.lineno,
        }

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        context = get_request_context()
        if context:
            log_data.update({
                "request_id": context.get("request_id"),
                "ip": context.get("ip"),
                "user_id": context.get("user_id"),
                "user_agent": context.get("user_agent"),
                "query_dict": context.get("query_dict"),
                "status_code": context.get("status_code"),
            })

        return json.dumps(log_data, ensure_ascii=False, default=str)


# Push context into thread-local storage
# def set_logging_context(context):
#     _thread_locals.context = context

# Clear after request
# def clear_logging_context():
#     if hasattr(_thread_locals, "context"):
#         del _thread_locals.context

# Full logging config for Django
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,  # Keep Django's default loggers
    'formatters': {
        'verbose': {
            'format': '[{asctime}][{levelname}][{module}] {process:d}x{thread:d}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        "json": {
            "()": JsonFormatter,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'portal_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/portal.log'),
            'maxBytes': 1024*1024*16,
            'backupCount': 20,
            'formatter': 'json',
        },
        'request_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/requests.log'),
            'maxBytes': 1024*1024*32,
            'backupCount': 20,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['request_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'portal': {  # Your app
            'handlers': ['console', 'portal_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}