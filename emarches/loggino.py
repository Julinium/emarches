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
            # "logger": record.name,
            # "file": record.pathname,
            "line": record.lineno,
        }

        if record.pathname.startswith(str(BASE_DIR)):
            relative_path = os.path.relpath(record.pathname, BASE_DIR)
        else:
            relative_path = record.pathname
            
        log_data["file"] = relative_path

        def get_client_ip(request):
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for: return x_forwarded_for.split(",")[0].strip()
            else: return request.META.get("REMOTE_ADDR")

        request = getattr(record, "request", None)
        if request:
            log_data["user_id"] = request.user.id if request.user.is_authenticated else "--"
            log_data["ip_address"] = get_client_ip(request)
            log_data["proxies"] = request.META.get("HTTP_X_FORWARDED_FOR", "--")
            log_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "--")
            log_data["referer"] = request.META.get("HTTP_REFERER", "--")
            log_data["full_path"] = request.get_full_path()

        return json.dumps(log_data, ensure_ascii=False, default=str)

