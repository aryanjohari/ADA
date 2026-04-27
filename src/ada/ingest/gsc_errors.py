"""Structured error taxonomy for GSC ingestion."""

from __future__ import annotations


class GSCError(Exception):
    error_code = "gsc_error"


class GSCAuthError(GSCError):
    error_code = "gsc_auth_error"


class GSCPermissionError(GSCError):
    error_code = "gsc_permission_error"


class GSCQuotaError(GSCError):
    error_code = "gsc_quota_error"


class GSCTransientHttpError(GSCError):
    error_code = "gsc_transient_http_error"


class GSCValidationError(GSCError):
    error_code = "gsc_validation_error"


class GSCInvariantError(GSCError):
    error_code = "gsc_invariant_error"


class GSCTimeBudgetExceeded(GSCError):
    error_code = "gsc_time_budget_exceeded"
