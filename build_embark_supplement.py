"""One-off: extracts embark_supplement.json (single-word Tahitian -> French
gloss) from an export of the Embark app's local "fr_FR_ty_PF" course
(IndexedDB EmbarkBrowser > courses > fr_FR_ty_PF > stringifiedObject,
simplified to {ty, fr, pos} for vocabConcepts + phraseConcepts and saved via
the browser as embark_ty_fr.json). Embark is a missionary language-learning
app with gospel/mission-specific vocabulary (church, gospel, priesthood...)
that a general dictionary like REO doesn't cover.

The raw export lives outside this repo (like the REO SQLite dump) and is
NOT a build dependency of generate_pages.py - only embark_supplement.json
is committed. build_tah_dict.py merges it in on top of the SQLite result,
filling gaps only, never overwriting an existing SQLite-sourced gloss.

Only single-word vocab entries are used (multi-word phrases are skipped),
after stripping a leading "ia " infinitive marker (Embark cites verbs as
"ia haamata" = "to begin", same convention as "to" in an English
dictionary - without stripping it, 453 of 2536 vocab entries (including
haamata itself) were silently discarded for looking like a 2-word
phrase) so a gloss always maps to exactly the tapped word, not a phrase.
"""
import json
import re

SOURCE_PATH = r'C:/Users/ariin/Downloads/embark_ty_fr.json'
MAX_GLOSSES = 6

MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
OKINA_RE = re.compile(r"[\u2018\u2019\u02bb\x27]")
IA_PREFIX_RE = re.compile(r'^ia\s+', re.IGNORECASE)


def normalize(word):
    word = word.translate(MACRON_MAP)
    word = OKINA_RE.sub('', word)
    return word.lower()


with open(SOURCE_PATH, encoding='utf-8') as f:
    data = json.load(f)

result = {}
for item in data['vocab']:
    ty, fr = item.get('ty'), item.get('fr')
    if not ty or not fr:
        continue
    ty = IA_PREFIX_RE.sub('', ty.strip())
    if re.search(r'\s', ty):
        continue  # only single-word entries (after stripping "ia ")
    key = normalize(ty)
    if not key:
        continue
    glosses = result.setdefault(key, [])
    for part in fr.split(','):
        part = part.strip()
        if part and part not in glosses and len(glosses) < MAX_GLOSSES:
            glosses.append(part)

result = {k: ', '.join(v) for k, v in result.items()}

with open('embark_supplement.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)

print(f'{len(result)} mots extraits de Embark (vocabulaire mono-mot uniquement).')
