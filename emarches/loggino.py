import json
import logging
import os
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(__file__).resolve().parent.parent


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

        try: context = get_request_context()
        except: context = None

        # data = {
        #     "ip": get_client_ip(request), 
        #     "user_agent": request.META.get("HTTP_USER_AGENT", ""), 
        #     "method": request.method, 
        #     "path": request.path, 
        #     "full_path": request.get_full_path(), 
        #     "host": request.get_host(), 
        #     "is_secure": request.is_secure(), 
        #     "referer": request.META.get("HTTP_REFERER"), 
        #     "accept_language": request.META.get("HTTP_ACCEPT_LANGUAGE"), 
        # }

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
            'handlers': ['portal_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}