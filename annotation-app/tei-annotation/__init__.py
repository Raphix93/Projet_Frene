"""Moteur d’enrichissement TEI du Projet Frêne."""

from .models import Annotation, AnnotationManifest, TextSelector
from .parser import load_annotations, load_tei
from .validators import validate_annotations

__all__ = [
    "Annotation",
    "AnnotationManifest",
    "TextSelector",
    "load_annotations",
    "load_tei",
    "validate_annotations",
]

__version__ = "0.4.0"
