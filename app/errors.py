class AppError(Exception):
    status = 500; code = "INTERNAL_ERROR"
    def __init__(self, message: str, details: dict | None = None, *, code=None, status=None):
        super().__init__(message)
        self.message, self.details = message, details
        if code: self.code = code
        if status: self.status = status

class InvalidURL(AppError):          status, code = 422, "INVALID_URL"
class BlockedURL(AppError):          status, code = 400, "BLOCKED_URL"
class SiteUnreachable(AppError):     status, code = 502, "SITE_UNREACHABLE"
class SiteTimeout(AppError):         status, code = 504, "SITE_TIMEOUT"
class SiteBlocked(AppError):         status, code = 502, "SITE_BLOCKED_OR_RESTRICTED"
class UnsupportedContent(AppError):  status, code = 415, "UNSUPPORTED_CONTENT"
class InsufficientContent(AppError): status, code = 422, "INSUFFICIENT_CONTENT"
class LLMUnavailable(AppError):      status, code = 503, "LLM_UNAVAILABLE"

class InvalidQuery(AppError):        status, code = 422, "INVALID_QUERY"
class BudgetExceeded(AppError):      status, code = 503, "DISCOVERY_BUDGET_EXCEEDED"
