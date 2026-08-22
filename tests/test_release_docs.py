from scripts.validate_release_docs import validate


def test_release_documentation_matches_frozen_implementation() -> None:
    report = validate()

    assert report["status"] == "PASS", report["errors"]
    assert report["error_count"] == 0
