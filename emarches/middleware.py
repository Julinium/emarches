
import logging
import uuid
from django.utils.deprecation import MiddlewareMixin

from emarches.loggino import set_logging_context, clear_logging_context

class CustomLoggingMiddleware(MiddlewareMixin):
    """
    Adds request context (user, IP, UA, request_id, query_dict) to every log record.
    """

    def process_request(self, request):
        request.request_id = str(uuid.uuid4())[:8]
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '-')
        user_id = request.user.id if request.user.is_authenticated else None
        user_agent = request.META.get('HTTP_USER_AGENT', '-')
        query_dict = request.GET.dict()
        request._logging_context = {
            "request_id": request.request_id,
            "ip": ip,
            "user_id": user_id,
            "user_agent": user_agent,
            "query_dict": query_dict,
        }
        # PUSH context into logging
        set_logging_context(request._logging_context)

def process_response(self, request, response):
    ctx = getattr(request, "_logging_context", {})
    ctx["status_code"] = response.status_code
    logging.getLogger("django").info("HTTP request", extra=ctx)
    if hasattr(request, '_log_context'):
        request._log_context["status_code"] = response.status_code

    # CLEAN UP
    clear_logging_context()
    return response

