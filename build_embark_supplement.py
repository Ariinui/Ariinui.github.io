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

Only single-word vocab entries are used (multi-word phrases are skipped) so
a gloss always maps to exactly the tapped word, not a whole phrase.
"""
import json
import re

SOURCE_PATH = r'C:/Users/ariin/Downloads/embark_ty_fr.json'
MAX_GLOSSES = 6

MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
OKINA_RE = re.compile(r"[\u2018\u2019\u02bb\x27]")


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
    if re.search(r'\s', ty.strip()):
        continue  # only single-word entries
    key = normalize(ty.strip())
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
