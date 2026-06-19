import threading
from datetime import timedelta

from django.utils import timezone

_thread_locals = threading.local()
_backup_lock = threading.Lock()


def get_current_request():
    return getattr(_thread_locals, 'request', None)


class RequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            return self.get_response(request)
        finally:
            _thread_locals.request = None


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from mainapp.models import BackupSettings
            tzname = BackupSettings.load().timezone
            timezone.activate(tzname)
        except Exception:
            timezone.deactivate()
        response = self.get_response(request)
        timezone.deactivate()
        if not request.path.startswith('/static/'):
            _maybe_auto_backup()
        return response


def _maybe_auto_backup():
    if not _backup_lock.acquire(blocking=False):
        return
    try:
        from mainapp.models import BackupSettings, BackupLog
        cfg = BackupSettings.load()
        last = BackupLog.objects.order_by('-created_at').first()
        if last is None or (timezone.now() - last.created_at) >= timedelta(days=cfg.interval_days):
            from mainapp.admin import _do_backup
            _do_backup()
    except Exception:
        pass
    finally:
        _backup_lock.release()
