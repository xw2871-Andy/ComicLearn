"""curriculum-to-comic: turn any educational curriculum into a comic book lesson."""

__version__ = "0.1.0"

from .agent import ComicAgent
from .models import Lesson, Scene, Storyboard, Panel

__all__ = ["ComicAgent", "Lesson", "Scene", "Storyboard", "Panel", "__version__"]
