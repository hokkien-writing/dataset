# Reading Notation Diff Columns Design

## Goal

Improve `match_by_en.py` so notation-only differences between the 斐姑娘 and 007 readings are identified explicitly instead of being misclassified as phonological differences.

## Output

Add these columns to `books/斐姑娘詞典_真實讀音差異_最終.csv`:

- `diff_連字號`
- `diff_標調符號`

Keep the existing `diff_第六調` column for breve/caron differences. A sixth-tone breve/caron difference must not also set `diff_標調符號`.

## Classification

Classification runs before the existing initial, final, tone, and syllable-count analysis.

### Hyphen differences

Normalize spaces and the separator characters `-`, `–`, and `—` for comparison. If the readings otherwise have identical characters, set `diff_連字號` to `Y`.

This category includes hyphen versus space, hyphen versus concatenation, and equivalent dash forms. It does not ignore punctuation other than those separator characters.

Example:

- 斐: `á-cîh`
- 007: `á cîh`
- Result: `diff_連字號=Y`

### Tone-mark differences

After separator normalization, compare the readings through the existing PUJ-to-`LATN_NORM` translator. If the original normalized strings differ but their `LATN_NORM` values are identical, set `diff_標調符號` to `Y`.

This captures equivalent placement or Unicode representation of a tone mark, such as `úa / uá`, without treating a true tone-number difference as notation-only.

If the only tone-mark difference is the sixth-tone breve/caron pair already recognized by the existing logic, set only `diff_第六調=Y`.

## Interaction With Existing Columns

Both new columns may be `Y` when a row contains both separator and tone-mark differences.

When all differences are fully explained by `diff_連字號`, `diff_標調符號`, or `diff_第六調`, do not set:

- `diff_聲母`
- `diff_韻母`
- `diff_聲調`
- `diff_音節數`
- `diff_拼寫`

If other content differences remain, run the existing phonological analysis on consistently tokenized readings and retain the relevant existing flags.

## Structure

Move the executable CSV-generation flow behind a `main()` entry point so the comparison helpers can be imported by unit tests without regenerating files. Keep the comparison and generation behavior in `match_by_en.py`; no new production module or one-off postprocessor is needed.

## Verification

Add `unittest` coverage for:

- `á-cîh / á cîh` as a hyphen-only difference.
- `úa / uá` as a tone-mark-only difference.
- A row containing both difference types.
- A sixth-tone breve/caron pair remaining exclusive to `diff_第六調`.
- A genuine tone difference remaining `diff_聲調`.

Run the focused test file, regenerate the output CSV, and verify the new column counts and representative rows.
