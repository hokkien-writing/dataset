import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts.wikisource.corrections import CorrectionCatalog, CorrectionRule
from scripts.wikisource.postprocess import fix_orphaned_semicolons
from scripts.wikisource.wikitext import validate_page_markers

mod = importlib.import_module(
    "scripts.wikisource.007_A_Pronouncing_and_Defining_Dictionary_of_the_Swatow_Dialect"
)
_split_embedded_gloss = mod._split_embedded_gloss
_expand_single_reading = mod._expand_single_reading
_expand_example = mod._expand_example
_is_reading_seg = mod._is_reading_seg
_reformat_entries = mod.reformat_entries
_fix_reading_corrections = mod.fix_reading_corrections
_postprocess = mod.postprocess
_normalize_entry_punctuation = mod.normalize_entry_punctuation


class TestSplitEmbeddedGloss(unittest.TestCase):
    def test_splits_embedded_reading(self):
        cases = [
            (
                "concealed from every body's cognizance, aⁿ m̄ lī; irrepressible.",
                ("concealed from every body's cognizance", [("aⁿ m̄ lī", "irrepressible.")]),
            ),
            ("to rear ducks, jīo ah; tend ducks.", ("to rear ducks", [("jīo ah", "tend ducks.")])),
            ("evil ways, tăi ak; great crimes.", ("evil ways", [("tăi ak", "great crimes.")])),
        ]
        for gloss, expected in cases:
            with self.subTest(gloss=gloss):
                self.assertEqual(_split_embedded_gloss(gloss), expected)

    def test_pure_english_returns_none(self):
        for gloss in ["a thermometer.", "it is a work of several days.", "wages."]:
            with self.subTest(gloss=gloss):
                self.assertIsNone(_split_embedded_gloss(gloss))


class TestExpandSingleReading(unittest.TestCase):
    def test_gloss_start_merge(self):
        hit = _split_embedded_gloss("ang cía; husband and wife.")
        self.assertIsNotNone(hit)
        gloss1, items = hit
        self.assertEqual(gloss1, "")
        self.assertEqual(
            _expand_single_reading("ang", gloss1 + "ang cía; husband and wife."),
            [("ang; ang cía", "husband and wife.")],
        )


class TestExpandExampleInlineEnglish(unittest.TestCase):
    def test_p243(self):
        out = _expand_example(
            "cêk kâi kang jîeh cōi cîⁿ? What are the wages for a day's work?",
            "tîeh ŭ kúi kâi kang; it is a work of several days.",
        )
        self.assertEqual(out, [
            ("cêk kâi kang jîeh cōi cîⁿ?", "What are the wages for a day's work?"),
            ("tîeh ŭ kúi kâi kang", "it is a work of several days."),
        ])

    def test_p275(self):
        out = _expand_example(
            "tī-tîang kío lṳ́? Who helped you about it?",
            "kío i khui hâng; help him to open a store.",
        )
        self.assertEqual(out, [
            ("tī-tîang kío lṳ́?", "Who helped you about it?"),
            ("kío i khui hâng", "help him to open a store."),
        ])

    def test_p322(self):
        out = _expand_example(
            "i tó̤ khàu mih sṳ̄? What is she crying about? thâu kîaⁿ thâu khàu",
            "crying as he went.",
        )
        self.assertEqual(out, [
            ("i tó̤ khàu mih sṳ̄?", "What is she crying about?"),
            ("thâu kîaⁿ thâu khàu", "crying as he went."),
        ])

    def test_p324_mixed_reading_semicolon_english(self):
        out = _expand_example(
            "i sĭ taⁿ kheng-kíaⁿ kâi nâng; he is one who does odd jobs. khîeh kha kheng lâi chō̤",
            "take a basket to put it in.",
        )
        self.assertEqual(out, [
            ("i sĭ taⁿ kheng-kíaⁿ kâi nâng", "he is one who does odd jobs."),
            ("khîeh kha kheng lâi chō̤", "take a basket to put it in."),
        ])

    def test_p629(self):
        out = _expand_example(
            "i sĭ m̄ cai sí ûah ā! He is unaware that he is in great danger there! i kâi nâng ûah-phuah căi",
            "she is a very bustling body.",
        )
        self.assertEqual(out, [
            ("i sĭ m̄ cai sí ûah ā!", "He is unaware that he is in great danger there!"),
            ("i kâi nâng ûah-phuah căi", "she is a very bustling body."),
        ])

    def test_p558_quoted_phrase(self):
        out = _expand_example(
            'peh-sèⁿ khṳ̀ kìⁿ kuaⁿ sĭ cheng ka-kī cò̤ "síe ti"',
            'common people who go before a magistrate speak of themselves as "humble selves." cí khí sṳ̄ sĭ ŭ ti; this is something that really happens.',
        )
        self.assertEqual(out, [
            ('peh-sèⁿ khṳ̀ kìⁿ kuaⁿ sĭ cheng ka-kī cò̤ "síe ti"', 'common people who go before a magistrate speak of themselves as "humble selves."'),
            ("cí khí sṳ̄ sĭ ŭ ti", "this is something that really happens."),
        ])


class TestExpandExampleConservative(unittest.TestCase):
    def test_multi_clause_readings_not_split(self):
        cases = [
            (
                "lṳ́ mih huang? lṳ́ sĭm-mih huang chue lâi?",
                "What brought you here?",
            ),
            ("sĭ mē? hēⁿ.", "Is it so? Yes."),
            (
                "hía hṳ̂ cò̤-nî ŏi khó-but? sĭ thâi phùa táⁿ a m̄ sĭ?",
                "Why should they not be able to eat it? is it because the gall-bladder has been ruptured or not?",
            ),
        ]
        for ph, gl in cases:
            with self.subTest(ph=ph):
                self.assertEqual(_expand_example(ph, gl), [(ph, gl)])

    def test_single_examples_never_dropped(self):
        cases = [
            ("hâng-sú-cam", "a thermometer."),
            ("sie ah", "roast duck."),
            ("a-~~nôⁿ~~(noⁿ)", "my child."),
            ("pang-cam; thng-sî cam", "the pin used to fasten the coiffure."),
            ("220", "royal, regal, princely."),
            ("", "a thermometer."),
        ]
        for ph, gl in cases:
            with self.subTest(ph=ph):
                self.assertEqual(_expand_example(ph, gl), [(ph, gl)])


class TestReformatEntries(unittest.TestCase):
    def test_normalizes_semantic_punctuation_without_changing_markdown(self):
        raw = (
            "<!-- page:1 -->\n"
            "- **話,好!** ua，ho！ — say，\"good！\"\n"
            "  - *ua，ho！* — say，‘don‘t！’\n"
            "## TITLE: UNCHANGED!\n"
        )
        self.assertEqual(
            "<!-- page:1 -->\n"
            "- **話，好！** ua, ho! — say, \"good!\"\n"
            "  - *ua, ho!* — say, 'don't!'\n"
            "## TITLE: UNCHANGED!\n",
            _normalize_entry_punctuation(raw),
        )

    def test_normalizes_corrections_without_changing_correction_markup(self):
        raw = (
            "- **~~話,~~(話,好!)** ~~ua，~~(ua，ho！) — "
            "~~say，~~(say，good！)\n"
        )
        self.assertEqual(
            "- **~~話，~~(話，好！)** ~~ua,~~(ua, ho!) — "
            "~~say,~~(say, good!)\n",
            _normalize_entry_punctuation(raw),
        )

    def test_postprocess_normalizes_entry_punctuation(self):
        raw = (
            "<!-- page:1 -->\n\n"
            "**話,好!** ua，ho！\n"
            "* say，‘don‘t！’\n"
        )
        out = _postprocess(raw)
        self.assertIn("- **話，好！** ua, ho!", out)
        self.assertIn("— say, 'don't!'", out)

    def test_page_marker_validation_rejects_inline_or_reordered_markers(self):
        validate_page_markers("<!-- page:1 -->\ntext\n<!-- page:2 -->\n", 1, 2)
        with self.assertRaises(ValueError):
            validate_page_markers("text <!-- page:1 -->\n<!-- page:2 -->\n", 1, 2)
        with self.assertRaises(ValueError):
            validate_page_markers("<!-- page:2 -->\n<!-- page:1 -->\n", 1, 2)

    def test_orphan_repair_does_not_embed_page_marker(self):
        raw = (
            "i sí sí kīo, kĭo kàu jī-ke phok\n"
            "\n"
            "<!-- page:498 -->\n"
            "\n"
            "khṳ̀;\n"
            ": he will incite them to mortal strife.\n"
            "; teh sí;\n"
        )
        out = fix_orphaned_semicolons(raw)
        self.assertIn(
            "  - *i sí sí kīo, kĭo kàu jī-ke phok khṳ̀* — he will incite them to mortal strife.\n"
            "<!-- page:498 -->\n"
            "; teh sí;",
            out,
        )
        leading_marker = fix_orphaned_semicolons(
            "<!-- page:626 -->\n"
            "koiⁿ u-u ùe-ùe;\n"
            ": the whole place is filthy.\n"
        )
        self.assertEqual(
            "<!-- page:626 -->\n"
            "  - *koiⁿ u-u ùe-ùe* — the whole place is filthy.\n",
            leading_marker,
        )

    def test_page_marker_after_head_stays_after_head(self):
        raw = (
            "* **陣** cūn (19|170|7)\n"
            "\n"
            "<!-- page:100 -->\n"
            "\n"
            "* A gust or blast.\n"
            "; cêk cūn huang;\n"
            ": a gust of wind.\n"
        )
        out = _reformat_entries(raw)
        self.assertLess(out.index("- **陣**"), out.index("<!-- page:100 -->"))
        self.assertLess(out.index("<!-- page:100 -->"), out.index("  - *cêk cūn huang*"))

    def test_page_marker_between_examples_stays_between_examples(self):
        raw = (
            "* **面** mīn (595|176|0)\n"
            "* The visage.\n"
            "; mīn cia miⁿ;\n"
            ": the face concealed.\n"
            "\n"
            "<!-- page:405 -->\n"
            "\n"
            "; mīn hong-jŭn;\n"
            ": fresh looking.\n"
        )
        out = _reformat_entries(raw)
        self.assertLess(out.index("  - *mīn cia miⁿ*"), out.index("<!-- page:405 -->"))
        self.assertLess(out.index("<!-- page:405 -->"), out.index("  - *mīn hong-jŭn*"))

    def test_postprocess_keeps_page_markers_standalone_and_ordered(self):
        raw = (
            "<!-- page:497 -->\n"
            "* **勢** sì (780|61|10)\n"
            "* Power.\n"
            "; i sí sí kīo, kĭo kàu jī-ke phok\n"
            "<!-- page:498 -->\n"
            "khṳ̀;\n"
            ": he will incite them to mortal strife.\n"
            "<!-- page:499 -->\n"
            "* **事** sṳ̄ (837|6|7)\n"
            "* An affair.\n"
        )
        out = _postprocess(raw)
        marker_lines = [line for line in out.splitlines() if "<!-- page:" in line]
        self.assertEqual(
            ["<!-- page:497 -->", "<!-- page:498 -->", "<!-- page:499 -->"],
            marker_lines,
        )

    def test_p243_inline_english(self):
        raw = (
            "* **工** kang (9|48|1)\n"
            "* Work; labor; a day's work.\n"
            "; cêk kâi kang jîeh cōi cîⁿ? What are the wages for a day's work?\n"
            ": tîeh ŭ kúi kâi kang; it is a work of several days.\n"
            "; kang cîⁿ;\n"
            ": wages.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn("- **工** kang (9|48|1) — Work; labor; a day's work.", out)
        self.assertIn(
            "  - *cêk kâi kang jîeh cōi cîⁿ?* — What are the wages for a day's work?", out
        )
        self.assertIn("  - *tîeh ŭ kúi kâi kang* — it is a work of several days.", out)
        self.assertIn("  - *kang cîⁿ* — wages.", out)
        self.assertEqual(out.count("  - *"), 3)

    def test_defn_colon_continuation(self):
        raw = (
            "* **米** bí (590|119|0)\n"
            "* Rice, hulled but not cooked;\n"
            ": small grains.\n"
            "; pêh bí;\n"
            ": clean hulled rice.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn("- **米** bí (590|119|0) — Rice, hulled but not cooked; small grains.", out)
        self.assertIn("  - *pêh bí* — clean hulled rice.", out)

    def test_gloss_continuation_across_page(self):
        raw = (
            "* **插** chah (9|64|9)\n"
            "* To insert; to stick in; to set in a socket.\n"
            "; chah hieⁿ;\n"
            ": to\n"
            "\n"
            "<!-- page:103 -->\n"
            "\n"
            ": set the lower end of incense sticks into the ashes of the incense pot; to worship the gods.\n"
            "; chah cháu ûi pie;\n"
            ": to stick in a spear of grass as a label.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn(
            "  - *chah hieⁿ* — to set the lower end of incense sticks into the ashes of the incense pot; to worship the gods.",
            out,
        )
        self.assertIn("<!-- page:103 -->", out)

    def test_bare_colon_gloss_across_page(self):
        raw = (
            "* **鄉** hieⁿ (375|24|9)\n"
            "* A district; a village.\n"
            "; lô̤h hieⁿ;\n"
            ":\n"
            "\n"
            "<!-- page:167 -->\n"
            "\n"
            ": go into the country.\n"
            "; mō̤ⁿ-kìⁿ ke-hieⁿ;\n"
            ": look from afar upon his native place.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn("  - *lô̤h hieⁿ* — go into the country.", out)
        self.assertIn("  - *mō̤ⁿ-kìⁿ ke-hieⁿ* — look from afar upon his native place.", out)

    def test_semicolon_defn_with_gloss(self):
        raw = (
            "* **蟛** pê (662|172|12)\n"
            "* ; pê-khî;\n"
            ": a small land-crab common in rice-fields.\n"
            "; âng kha pê-khî;\n"
            ": red clawed land crabs.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn("- **蟛** pê (662|172|12)", out)
        self.assertIn("  - *pê-khî* — a small land-crab common in rice-fields.", out)
        self.assertIn("  - *âng kha pê-khî* — red clawed land crabs.", out)
        self.assertNotIn("; pê-khî;", out)

    def test_colon_reading_phrase_with_gloss(self):
        raw = (
            "* **束** sok (779|75|3)\n"
            "* To bind many things together.\n"
            "; kwn lăi kâi sok-siu sĭ jîeh cōi?\n"
            ": In the written agreement with the teacher, what is the sum agreed upon as his wages?\n"
            ": ak-sok; iak-sok;\n"
            ": to repress, to keep down.\n"
            ": i cí hûe sît-căi sok chíu;\n"
            ": he is now really unable to act.\n"
            "; tîeh cai ak-sok i màiⁿ hùang-sṳ̀;\n"
            ": must keep him under restraint so that he will not be impudent.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn("  - *ak-sok; iak-sok* — to repress, to keep down.", out)
        self.assertIn("  - *i cí hûe sît-căi sok chíu* — he is now really unable to act.", out)
        self.assertIn(
            "  - *tîeh cai ak-sok i màiⁿ hùang-sṳ̀* — must keep him under restraint so that he will not be impudent.",
            out,
        )

    def test_gloss_continuation_after_semicolon_gloss(self):
        raw = (
            "* **隨** sûi (921|128|12)\n"
            "* To follow; to accord with.\n"
            "; sûi-pĭen;\n"
            ": as you like;\n"
            ": when convenient.\n"
        )
        out = _reformat_entries(raw)
        self.assertIn("  - *sûi-pĭen* — as you like; when convenient.", out)


def _catalog_shim(**tables: object) -> SimpleNamespace:
    defaults = {
        "reading": {},
        "gloss": {},
        "example_splits": {},
        "review": {},
        "headword_review": {},
    }
    defaults.update(tables)
    return SimpleNamespace(**defaults)


_fixture_rule_counter = 0


def _fixture_rule(
    rule_type: str,
    *,
    headword: str = "",
    key: tuple[str, str, str] = ("raw", "gloss", "25"),
    output_index: int = 1,
    replacement_reading: str = "",
    replacement_gloss: str = "",
) -> CorrectionRule:
    global _fixture_rule_counter
    _fixture_rule_counter += 1
    return CorrectionRule(
        rule_id=f"007-{rule_type}-{_fixture_rule_counter:016x}",
        rule_type=rule_type,
        headword=headword,
        key=key,
        output_index=output_index,
        replacement_reading=replacement_reading,
        replacement_gloss=replacement_gloss,
        enabled=True,
        review_status="pending",
        note="",
    )


def _build_catalog(rules: list[CorrectionRule]) -> CorrectionCatalog:
    reading: dict[tuple[str, str, str], str] = {}
    gloss: dict[tuple[str, str, str], str] = {}
    example_splits: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    review: dict[tuple[str, str, str], tuple[str | None, str | None]] = {}
    headword_review: dict[tuple[str, str, str, str], tuple[str | None, str | None]] = {}
    for rule in rules:
        if not rule.enabled:
            continue
        if rule.rule_type == "reading":
            reading[rule.key] = rule.replacement_reading
        elif rule.rule_type == "gloss":
            gloss[rule.key] = rule.replacement_gloss
        elif rule.rule_type == "example_split":
            example_splits.setdefault(rule.key, []).append(
                (rule.replacement_reading, rule.replacement_gloss)
            )
        elif rule.rule_type == "review":
            review[rule.key] = (
                rule.replacement_reading or None,
                rule.replacement_gloss or None,
            )
        elif rule.rule_type == "headword_review":
            headword_review[(rule.headword, *rule.key)] = (
                rule.replacement_reading or None,
                rule.replacement_gloss or None,
            )
    return CorrectionCatalog(
        rules=tuple(rules),
        reading=reading,
        gloss=gloss,
        example_splits=example_splits,
        review=review,
        headword_review=headword_review,
    )


def _fixed_reading_token(text: str) -> str:
    line = text.split("\n", 1)[1]
    return line.split(" — ", 1)[0].split("** ", 1)[1]


def _apply_fixture(
    catalog: CorrectionCatalog,
    headword: str = "字",
    reading: str = "raw",
    gloss: str = "gloss",
    page: str = "25",
) -> str:
    loader_patch = patch(
        "scripts.wikisource.corrections.load_correction_catalog",
        return_value=catalog,
    )
    loader_patch.start()
    try:
        importlib.reload(mod)
        text = f"<!-- page:{page} -->\n- **{headword}** {reading} — {gloss}\n"
        fixed = _fix_reading_corrections(text)
    finally:
        loader_patch.stop()
        importlib.reload(mod)
    return _fixed_reading_token(fixed)


class TestCorrectionCatalogRouting(unittest.TestCase):
    def test_headword_review_beats_review(self) -> None:
        catalog = _build_catalog(
            [
                _fixture_rule(
                    "headword_review",
                    headword="字",
                    replacement_reading="headword result",
                ),
                _fixture_rule("review", replacement_reading="review result"),
                _fixture_rule(
                    "example_split",
                    replacement_reading="one",
                    replacement_gloss="first.",
                ),
                _fixture_rule("gloss", replacement_gloss="gloss result"),
                _fixture_rule("reading", replacement_reading="reading result"),
            ]
        )
        self.assertEqual(
            "headword result",
            _apply_fixture(catalog, headword="字", reading="raw", gloss="gloss", page="25"),
        )

    def test_review_beats_split(self) -> None:
        catalog = _build_catalog(
            [
                _fixture_rule("review", replacement_reading="review result"),
                _fixture_rule(
                    "example_split",
                    replacement_reading="one",
                    replacement_gloss="first.",
                ),
                _fixture_rule("gloss", replacement_gloss="gloss result"),
                _fixture_rule("reading", replacement_reading="reading result"),
            ]
        )
        self.assertEqual("review result", _apply_fixture(catalog))

    def test_split_beats_gloss(self) -> None:
        catalog = _build_catalog(
            [
                _fixture_rule(
                    "example_split",
                    replacement_reading="one",
                    replacement_gloss="first.",
                ),
                _fixture_rule("gloss", replacement_gloss="gloss result"),
                _fixture_rule("reading", replacement_reading="reading result"),
            ]
        )
        self.assertEqual("one", _apply_fixture(catalog))

    def test_gloss_beats_reading(self) -> None:
        catalog = _build_catalog(
            [
                _fixture_rule("gloss", replacement_gloss="gloss result"),
                _fixture_rule("reading", replacement_reading="reading result"),
            ]
        )
        self.assertEqual("raw", _apply_fixture(catalog))


class TestReviewCorrections(unittest.TestCase):
    def test_correction_survives_nearby_page_marker_repair(self):
        text = "<!-- page:101 -->\n  - *au* — To cudgel; to maul."
        with patch.object(
            mod,
            "CORRECTION_CATALOG",
            _catalog_shim(
                review={("au", "To cudgel; to maul.", "99"): ("áu", "To fight with sticks or fists.")}
            ),
        ):
            self.assertEqual(
                _fix_reading_corrections(text),
                "<!-- page:101 -->\n  - *áu* — To fight with sticks or fists.",
            )

    def test_empty_key_never_falls_back_to_an_adjacent_headword(self):
        text = "<!-- page:466 -->\n- **狽** pŭe (1|2|3)"
        with patch.object(
            mod,
            "CORRECTION_CATALOG",
            _catalog_shim(
                review={("pŭe", "", "467"): ("pŭe", "To add or heap up dirt.")}
            ),
        ):
            self.assertEqual(_fix_reading_corrections(text), text)

    def test_combined_review_correction_changes_reading_and_gloss_atomically(self):
        text = "<!-- page:32 -->\n  - *au* — To cudgel; to maul."
        with patch.object(
            mod,
            "CORRECTION_CATALOG",
            _catalog_shim(
                review={("au", "To cudgel; to maul.", "32"): ("áu", "To fight with sticks or fists.")}
            ),
        ):
            self.assertEqual(
                _fix_reading_corrections(text),
                "<!-- page:32 -->\n  - *áu* — To fight with sticks or fists.",
            )

    def test_headword_context_disambiguates_duplicate_empty_keys(self):
        text = "<!-- page:474 -->\n- **翩** phî (1|2|3)\n- **脾** phî (4|5|6)"
        with patch.object(
            mod,
            "CORRECTION_CATALOG",
            _catalog_shim(
                headword_review={
                    ("翩", "phî", "", "474"): (None, "To fly about; to flutter."),
                    ("脾", "phî", "", "474"): (None, "The temper; whims"),
                }
            ),
        ):
            output = _fix_reading_corrections(text)
        self.assertIn("- **翩** phî (1|2|3) — To fly about; to flutter.", output)
        self.assertIn("- **脾** phî (4|5|6) — The temper; whims", output)


if __name__ == "__main__":
    unittest.main()
