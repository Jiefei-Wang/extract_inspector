"""Web inspector for source texts and extracted data."""

from extract_inspector.inspect.app import inspector_web
from extract_inspector.inspect.models import Corpus, FilterSpec, Inspector

__all__ = ["Corpus", "FilterSpec", "Inspector", "inspector_web"]
