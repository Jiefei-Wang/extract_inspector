"""Web inspector for source texts and extracted data."""

from extract_inspector.inspect.app import inspector_web
from extract_inspector.inspect.models import Inspector

__all__ = ["Inspector", "inspector_web"]
