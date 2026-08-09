from __future__ import annotations

import unittest
from pathlib import Path


class TestRuleAwareStaticContract(unittest.TestCase):
    STATIC_DIR = Path("scripts/proofread_review/static")

    def _html(self) -> str:
        return (self.STATIC_DIR / "index.html").read_text(encoding="utf-8")

    def _script(self) -> str:
        return (self.STATIC_DIR / "app.js").read_text(encoding="utf-8")

    def _css(self) -> str:
        return (self.STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    def test_rule_type_and_status_are_exposed(self) -> None:
        html = self._html()
        script = self._script()
        for value in (
            'id="rule-type-filter"',
            'value="pending"',
            'value="accepted"',
            'value="deferred"',
            'value="rejected"',
        ):
            self.assertIn(value, html)
        self.assertIn("rule_type", script)
        self.assertIn("RULE_TYPE_LABELS", script)

    def test_key_fields_are_read_only_metadata(self) -> None:
        html = self._html()
        script = self._script()
        self.assertIn('id="rule-keys"', html)
        self.assertIn('id="rule-key-list"', html)
        for value in (
            "rule_id",
            "key_reading",
            "key_gloss",
            "key_page",
            "resolved_page",
            "output_count",
        ):
            self.assertIn(value, script)

    def test_current_proposal_final_values_are_all_present(self) -> None:
        script = self._script()
        for value in ("record.current", "record.proposal", "decision.final"):
            self.assertIn(value, script)

    def test_semantic_note_and_disposition_are_preserved(self) -> None:
        html = self._html()
        script = self._script()
        self.assertIn('id="match-disposition"', html)
        self.assertIn('id="decision-note"', html)
        self.assertIn("decision.note", script)
        self.assertIn("decision.disposition", script)

    def test_accepted_rejected_deferred_actions_exist(self) -> None:
        html = self._html()
        script = self._script()
        for value in (
            'id="accept-button"',
            'id="defer-button"',
            'id="reject-button"',
        ):
            self.assertIn(value, html)
        for value in (
            'setStatus("accepted"',
            'setStatus("deferred"',
            'setStatus("rejected"',
        ):
            self.assertIn(value, script)

    def test_split_editor_has_add_remove_reorder_controls(self) -> None:
        html = self._html()
        script = self._script()
        for value in ('id="split-editor"', 'id="split-rows"', 'id="split-add"'):
            self.assertIn(value, html)
        for value in (
            'data-action="remove"',
            'data-action="move"',
            'data-direction="up"',
            'data-direction="down"',
            "elements.splitAdd",
        ):
            self.assertIn(value, script)

    def test_direct_page_input_and_prev_next_navigation(self) -> None:
        html = self._html()
        script = self._script()
        for value in ('id="page-input"', 'id="page-previous"', 'id="page-next"'):
            self.assertIn(value, html)
        self.assertIn("elements.pageInput", script)
        self.assertIn("showPdfPage(", script)

    def test_pointer_centered_wheel_zoom_is_preserved(self) -> None:
        script = self._script()
        self.assertIn('addEventListener("wheel"', script)
        self.assertIn("zoomAt(", script)
        self.assertIn("event.clientX", script)
        self.assertIn("event.clientY", script)
        self.assertIn('addEventListener("pointerdown"', script)
        self.assertIn('addEventListener("dblclick"', script)

    def test_split_and_rejected_styles_exist(self) -> None:
        css = self._css()
        self.assertIn(".is-rejected", css)
        self.assertIn(".split-row", css)
        self.assertIn(".split-actions", css)
        self.assertIn("#page-input", css)
        self.assertIn(".rule-keys", css)


if __name__ == "__main__":
    unittest.main()
