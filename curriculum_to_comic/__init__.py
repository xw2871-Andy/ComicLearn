"""curriculum-to-comic: turn any educational curriculum into a comic book lesson."""

from .agent import ComicAgent
from .models import Lesson, Scene, Storyboard, Panel
from .version import __version__

__all__ = ["ComicAgent", "Lesson", "Scene", "Storyboard", "Panel", "__version__"]
