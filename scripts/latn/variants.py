"""Generate pronunciation variants for historical sound changes."""

import re
import itertools
from scripts.latn.systems import puj as _puj_module

_VARIANT_RULES = {
    "PUJ": lambda: _puj_module.create_variant_rules(),
}


def _compile_rules(raw_rules):
    return [(re.compile(pat), variants) for pat, variants in raw_rules.items()]


def _split_syllables(text):
    syllable_re = re.compile(r"[A-Za-z\u00C0-\u1EFF\u0300-\u036F\u207F]+")
    parts = []
    last = 0
    for m in syllable_re.finditer(text):
        if m.start() > last:
            parts.append(("sep", text[last : m.start()]))
        parts.append(("syl", m.group()))
        last = m.end()
    if last < len(text):
        parts.append(("sep", text[last:]))
    return parts


def get_variants(text, system_name):
    rules_fn = _VARIANT_RULES.get(system_name.upper())
    if not rules_fn:
        return [text]

    rules = _compile_rules(rules_fn())

    parts = _split_syllables(text)

    syl_indices = [i for i, (t, _) in enumerate(parts) if t == "syl"]

    if not syl_indices:
        return [text]

    applicable_per_syl = []
    for idx in syl_indices:
        syl = parts[idx][1]
        matched = []
        for ri, (pat, _) in enumerate(rules):
            if pat.search(syl):
                matched.append(ri)
        applicable_per_syl.append(matched)

    combo_choices = []
    for ri, (pat, variants) in enumerate(rules):
        choices = set()
        for matched in applicable_per_syl:
            if ri in matched:
                choices.update(variants)
        if not choices:
            choices = {None}
        combo_choices.append(sorted(choices, key=lambda x: (x is None, x)))

    results = []
    for combo in itertools.product(*combo_choices):
        rebuilt = list(parts)
        for syl_i, idx in enumerate(syl_indices):
            syl = parts[idx][1]
            for ri in applicable_per_syl[syl_i]:
                if combo[ri] is None:
                    continue
                pat, _ = rules[ri]
                syl = pat.sub(combo[ri], syl)
            rebuilt[idx] = ("syl", syl)

        results.append("".join(v for _, v in rebuilt))

    return results
