from alto2tei.annotation_engine.models import (
    Annotation,
    AnnotationManifest,
    TextSelector,
)
from alto2tei.annotation_engine.validators import validate_annotations


def test_valid_positioned_annotation():
    text = "Je rencontrai Rousseau à Genève."
    start = text.index("Rousseau")
    end = start + len("Rousseau")

    manifest = AnnotationManifest(
        annotations=[
            Annotation(
                annotation_id="a1",
                annotation_type="person",
                selector=TextSelector(
                    exact="Rousseau",
                    start=start,
                    end=end,
                ),
            )
        ]
    )

    report = validate_annotations(manifest, text)

    assert report.valid is True
    assert report.errors == []


def test_missing_replacement_text_is_invalid():
    manifest = AnnotationManifest(
        annotations=[
            Annotation(
                annotation_id="a2",
                annotation_type="normalization",
                selector=TextSelector(
                    exact="etoit",
                    start=0,
                    end=5,
                ),
            )
        ]
    )

    report = validate_annotations(manifest, "etoit")

    assert report.valid is False
    assert any(
        issue.code == "REPLACEMENT_TEXT_MISSING"
        for issue in report.errors
    )
