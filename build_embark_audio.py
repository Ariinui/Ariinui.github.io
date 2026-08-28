"""One-off: extracts tah_audio.json (word/locution -> pronunciation mp3 URL)
from a richer export of the Embark app's local "fr_FR_ty_PF" course than the
one used by build_embark_supplement.py - this one keeps vocabConcepts,
phraseConcepts and mediaPaths as-is (not flattened to {ty, fr, pos}), saved
via the browser as embark_ty_fr_audio.json (IndexedDB EmbarkBrowser >
courses > fr_FR_ty_PF > stringifiedObject > vocabConcepts/phraseConcepts/
mediaPaths, kept outside the repo like the other raw exports).

Each vocabConcepts/phraseConcepts entry has an audioMediaId - either a real
id resolving through mediaPaths to a public embark-cdn.churchofjesuschrist.org
mp3 (no auth needed, confirmed by direct curl), or the MD5-of-empty-string
placeholder d41d8cd9-8f00-3204-a980-0998ecf8427e meaning "no audio recorded
for this entry" (2278/2536 vocab and 438/556 phrases have a real one).

Deliberately does NOT try to reproduce build_embark_supplement.py's
single-word/VERB-phrase filtering (that script derives a `pos` field this
raw export doesn't expose in the same shape, and reverse-engineering it
would be fragile). Instead: normalize every entry's text as a candidate key
(same normalize()/"ia "-prefix-stripping convention as
build_embark_supplement.py) and keep the audio URL only if that exact key
is already a real tap target in the current tah_dict.json - i.e. audio is a
pure enrichment layered on words/locutions this project's existing,
already-vetted glossary pipeline decided are worth tapping, never a new
source of what counts as tappable.
"""
import json
import os
import re

SOURCE_PATH = r'C:/Users/ariin/Downloads/embark_ty_fr_audio.json'
EMPTY_AUDIO_ID = 'd41d8cd9-8f00-3204-a980-0998ecf8427e'

MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
OKINA_RE = re.compile(r"[\u2018\u2019\u02bb\x27]")
IA_PREFIX_RE = re.compile(r'^ia\s+', re.IGNORECASE)


def normalize(word):
    word = word.translate(MACRON_MAP)
    word = OKINA_RE.sub('', word)
    return word.lower()


with open(SOURCE_PATH, encoding='utf-8') as f:
    data = json.load(f)

with open('tah_dict.json', encoding='utf-8') as f:
    tah_dict = json.load(f)

media_paths = data['mediaPaths']

candidates = {}
seen_raw = 0
for bucket in (data['vocabConcepts'], data['phraseConcepts']):
    for item in bucket.values():
        seen_raw += 1
        ty = item.get('textInTargetLanguage')
        audio_id = item.get('audioMediaId')
        if not ty or not audio_id or audio_id == EMPTY_AUDIO_ID:
            continue
        media = media_paths.get(audio_id)
        if not media or not media.get('webUrl'):
            continue
        ty = IA_PREFIX_RE.sub('', ty.strip())
        norm_words = [normalize(w) for w in ty.split()]
        if not all(norm_words):
            continue
        key = ' '.join(norm_words)
        candidates.setdefault(key, media['webUrl'])

result = {k: url for k, url in candidates.items() if k in tah_dict}
embark_count = len(result)

# Fare Vana'a (fetch_farevanaa_audio.py) : ne comble que les mots mono-mot
# encore sans audio apres Embark - jamais prioritaire, Embark reste la
# source de reference deja en place.
if os.path.exists('farevanaa_audio.json'):
    with open('farevanaa_audio.json', encoding='utf-8') as f:
        farevanaa_audio = json.load(f)
    added = 0
    for key, url in farevanaa_audio.items():
        if key in tah_dict and key not in result:
            result[key] = url
            added += 1
    print(f'{added} mots ajoutes depuis Fare Vana\'a (sur {embark_count} deja via Embark).')

with open('tah_audio.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)

print(f'{seen_raw} entrees Embark vues (vocab+phrase), {len(candidates)} avec audio reel apres normalisation.')
print(f'{len(result)} mots/locutions du glossaire actuel ont maintenant un audio (sur {len(tah_dict)} entrees dans tah_dict.json).')
