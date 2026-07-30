from alto2tei.annotation_engine.parser import parse_annotation


def test_parse_person_with_wikidata_uri():
    raw = {
        "id": "a1",
        "bodies": [
            {"purpose": "tagging", "value": "person"},
            {"purpose": "linking", "value": "Q7251"},
        ],
        "target": {
            "selector": [
                {
                    "type": "TextQuoteSelector",
                    "exact": "Rousseau",
                    "prefix": "Monsieur ",
                    "suffix": " arriva",
                },
                {
                    "type": "TextPositionSelector",
                    "start": 9,
                    "end": 17,
                },
            ]
        },
    }

    annotation = parse_annotation(raw, 0)

    assert annotation.annotation_type == "person"
    assert annotation.authority_uri == (
        "https://www.wikidata.org/entity/Q7251"
    )
    assert annotation.selector.exact == "Rousseau"
    assert annotation.selector.start == 9
    assert annotation.selector.end == 17
