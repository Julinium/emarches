import json
import logging
import os
from pathlib import Path

from django.conf import settings

from base.helper import get_client_ip

# HOME_DIR = Path(__file__).resolve().parent.parent

HOME_DIR = settings.BASE_DIR


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        request = getattr(record, "request", None)
        if request:
            log_data["user_id"] = request.user.id if request.user.is_authenticated else "--"
            if hasattr(request, "team"):
                log_data["team_id"] = request.team.id if request.team else "--"
            log_data["full_path"] = request.get_full_path()
            ip_address = get_client_ip(request)
            log_data["ip_address"] = ip_address
            proxies = request.META.get("HTTP_X_FORWARDED_FOR", "--")
            if proxies != ip_address:
                log_data["proxies"] = request.META.get("HTTP_X_FORWARDED_FOR", "--")
            log_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "--")
            log_data["referer"] = request.META.get("HTTP_REFERER", "--")

        if record.pathname.startswith(str(HOME_DIR)):
            relative_path = os.path.relpath(record.pathname, HOME_DIR)
        else:
            relative_path = record.pathname
        log_data["logger"] = record.name
        log_data["file"] = relative_path
        log_data["line"] = record.lineno

        return json.dumps(log_data, ensure_ascii=False, default=str)

