from nexportal_gate import text


def test_normalise_crlf_trailing_and_outer_blanks():
    assert text.normalise("\n\na \r\nb  \r\n\n") == "a\nb"


def test_body_hash_is_stable_across_normalisation():
    assert text.body_hash("a\r\nb  \n") == text.body_hash("\na\nb")


def test_body_hash_changes_with_content():
    assert text.body_hash("a") != text.body_hash("b")


def test_strip_comments_multiline():
    assert text.strip_comments("x <!-- a\nb --> y") == "x  y"


def test_sections_h2_and_h3():
    b = "## Outcome\nx\n### Users\ny\n#### deeper\nz\n"
    assert text.sections(b) == {"outcome": "x", "users": "y\n#### deeper\nz"}


def test_sections_ignore_preamble_and_h1():
    b = "# Title\npreamble\n## Outcome\nx"
    assert text.sections(b) == {"outcome": "x"}


def test_list_items_forms():
    assert text.list_items("- a\n* b\n- [ ] c\n- [x] d\n1. e\nprose") == ["a", "b", "c", "d", "e"]


def test_marker_prefix_no_whitespace_tolerance():
    assert text.marker_line_matches("NX-GATE: ready", "NX-GATE:")
    assert not text.marker_line_matches("  NX-GATE: ready", "NX-GATE:")
    assert not text.marker_line_matches("> NX-GATE: ready", "NX-GATE:")
