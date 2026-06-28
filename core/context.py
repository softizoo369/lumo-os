import contextvars
from contextlib import contextmanager

# Thread-safe memory variables
_current_workspace = contextvars.ContextVar('current_workspace', default=None)
_system_override = contextvars.ContextVar('system_override', default=False)

def set_workspace(workspace_id):
    """Sets the active workspace ID for the current request thread."""
    return _current_workspace.set(workspace_id)

def get_workspace():
    """Retrieves the active workspace ID."""
    return _current_workspace.get()

def is_system_override():
    return _system_override.get()

@contextmanager
def system_context():
    """
    Bypasses tenant isolation for system-level background jobs (e.g., Celery tasks, Cron jobs).
    Use carefully!
    """
    token = _system_override.set(True)
    try:
        yield
    finally:
        _system_override.reset(token)