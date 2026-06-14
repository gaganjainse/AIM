"""Caching service for AIM application."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CACHE_PREFIX_DASHBOARD = "dashboard:"
CACHE_PREFIX_STUDENT = "student:"
CACHE_PREFIX_ATTENDANCE = "attendance:"
CACHE_PREFIX_REPORT = "report:"

TTL_DASHBOARD = 300
TTL_STUDENT = 600
TTL_ATTENDANCE = 300
TTL_REPORT = 600


def _get_cache():
    try:
        from app import cache
        return cache
    except Exception:
        return None


def _make_key(prefix, *args):
    parts = [prefix]
    for arg in args:
        parts.append(arg.isoformat() if isinstance(arg, date) else str(arg))
    return ":".join(parts)


def get_cached_dashboard_data(target_date):
    cache = _get_cache()
    if not cache:
        return None
    try:
        return cache.get(_make_key(CACHE_PREFIX_DASHBOARD, target_date))
    except Exception:
        return None


def set_cached_dashboard_data(target_date, data, ttl=TTL_DASHBOARD):
    cache = _get_cache()
    if not cache:
        return
    try:
        cache.set(_make_key(CACHE_PREFIX_DASHBOARD, target_date), data, timeout=ttl)
    except Exception:
        pass


def invalidate_dashboard_cache():
    cache = _get_cache()
    if not cache:
        return
    try:
        if hasattr(cache, '_cache'):
            for k in [k for k in cache._cache if k.startswith(CACHE_PREFIX_DASHBOARD)]:
                del cache._cache[k]
        else:
            cache.clear()
    except Exception:
        pass


def get_cached_student_list():
    cache = _get_cache()
    if not cache:
        return None
    try:
        return cache.get(_make_key(CACHE_PREFIX_STUDENT, "all"))
    except Exception:
        return None


def set_cached_student_list(students, ttl=TTL_STUDENT):
    cache = _get_cache()
    if not cache:
        return
    try:
        cache.set(_make_key(CACHE_PREFIX_STUDENT, "all"), students, timeout=ttl)
    except Exception:
        pass


def invalidate_student_cache():
    cache = _get_cache()
    if not cache:
        return
    try:
        if hasattr(cache, '_cache'):
            for k in [k for k in cache._cache if k.startswith(CACHE_PREFIX_STUDENT)]:
                del cache._cache[k]
    except Exception:
        pass


def get_cached_attendance_for_date(target_date):
    cache = _get_cache()
    if not cache:
        return None
    try:
        return cache.get(_make_key(CACHE_PREFIX_ATTENDANCE, target_date))
    except Exception:
        return None


def set_cached_attendance_for_date(target_date, data, ttl=TTL_ATTENDANCE):
    cache = _get_cache()
    if not cache:
        return
    try:
        cache.set(_make_key(CACHE_PREFIX_ATTENDANCE, target_date), data, timeout=ttl)
    except Exception:
        pass


def invalidate_attendance_cache(target_date=None):
    cache = _get_cache()
    if not cache:
        return
    try:
        if hasattr(cache, '_cache'):
            if target_date:
                cache._cache.pop(_make_key(CACHE_PREFIX_ATTENDANCE, target_date), None)
            else:
                for k in [k for k in cache._cache if k.startswith(CACHE_PREFIX_ATTENDANCE)]:
                    del cache._cache[k]
    except Exception:
        pass


def get_cached_report_data():
    cache = _get_cache()
    if not cache:
        return None
    try:
        return cache.get(_make_key(CACHE_PREFIX_REPORT, "summary"))
    except Exception:
        return None


def set_cached_report_data(data, ttl=TTL_REPORT):
    cache = _get_cache()
    if not cache:
        return
    try:
        cache.set(_make_key(CACHE_PREFIX_REPORT, "summary"), data, timeout=ttl)
    except Exception:
        pass


def invalidate_report_cache():
    cache = _get_cache()
    if not cache:
        return
    try:
        if hasattr(cache, '_cache'):
            for k in [k for k in cache._cache if k.startswith(CACHE_PREFIX_REPORT)]:
                del cache._cache[k]
    except Exception:
        pass


def invalidate_all_cache():
    cache = _get_cache()
    if not cache:
        return
    try:
        cache.clear()
    except Exception:
        pass
