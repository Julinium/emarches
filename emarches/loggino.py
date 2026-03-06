import json
import logging
import os

from pathlib import Path
from django.conf import settings

import geoip2.database
from user_agents import parse

from base.helper import get_client_ip


HOME_DIR = settings.BASE_DIR

class JsonFormatter(logging.Formatter):
    def format(self, record):
        """
        Constructs a log object. Keys may or may not be present. They may be null/None.
        {
            "time": <time>,
            "level": <level>,
            "message": <message>,
            "user": <user_id>,
            "team": <team_id>,
            "path": <relative_path>,
            "ip": <ip_address>,
            "location": {
                "country": <country_name>,
                "iso": <country_iso_code> (lower case),
                "city": <city name>,
                },
            "proxies": <[proxy ip addresses]>,
            "device": <Device_type / OS +version / Browser+version>,
            "referer": <referer>,
            "logger": <logger>,
            "file": <file>,
            "line": <line>,
            ...
        """

        log_data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add all extra fields except "request"
        super_attrs = ["provider", "uid", "email", 'file_bytes']
        for key, value in record.__dict__.items():
            if key in super_attrs and key != "request":
                log_data[key] = value

        request = getattr(record, "request", None)
        if request:
            user_id = request.user.id if request.user is not None and request.user.is_authenticated else None
            if user_id: log_data["user"] = user_id

            if hasattr(request, "team"):
                team_id = request.team.id if request.team else None
                if team_id: log_data["team"] = team_id
            log_data["path"] = request.get_full_path()
            ip_address = get_client_ip(request)
            log_data["ip"] = ip_address
            
            try:
                city_db_path = os.path.join(HOME_DIR, "geoip/GeoLite2-City.mmdb")
                reader = geoip2.database.Reader(city_db_path)
                response = reader.city(ip_address)
                country_name = response.country.name
                country_code = response.country.iso_code
                city_name    = response.city.name
                location = {}
                if country_name is not None: location["country"] = country_name
                if country_code is not None: location["iso"] = country_code.lower()
                if city_name is not None: location["city"] = city_name
            except Exception: pass
            log_data["location"] = location

            proxies = request.META.get("HTTP_X_FORWARDED_FOR", None)
            if proxies is not None and proxies != ip_address:
                log_data["proxies"] = proxies

            ua = request.META.get("HTTP_USER_AGENT", "-")
            pua = parse(ua)
            log_data["device"] = str(pua)
            log_data["ua"] = ua

            log_data["referer"] = request.META.get("HTTP_REFERER", "-")

        if record.pathname.startswith(str(HOME_DIR)):
            relative_path = os.path.relpath(record.pathname, HOME_DIR)
        else:
            relative_path = record.pathname
        log_data["logger"] = record.name
        log_data["file"] = relative_path
        log_data["line"] = record.lineno

        return json.dumps(log_data, ensure_ascii=False, default=str)


