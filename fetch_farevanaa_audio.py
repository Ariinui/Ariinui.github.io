"""One-off: harvests Tahitian word pronunciation (mp3) URLs from the
Academie Tahitienne - Fare Vana'a online dictionary, for every single-word
tah_dict.json entry that doesn't already have audio from Embark
(build_embark_audio.py runs first and is the priority source - this only
fills the remaining gap, same "fills holes only, never overwrites" posture
as every other supplement on this project).

Site quirk (found while building fetch_farevanaa_supplement.py): each
headword entry's pronunciation is a single <audio src="..."> tag right
after its <div class="entree">word</div>, pointing at a public
farevanaa.cloud.pf URL - confirmed playable via a plain hotlink (foreign
Referer, no cookie/session needed) despite the file being served with
Content-Disposition: attachment. Locutions/sub-entries inside a headword's
page do NOT have their own audio, only the headword itself - so unlike
fetch_farevanaa_phrases.py, this only ever queries single words.

Same posture as the other farevanaa.pf scripts: single-threaded, ~1s delay,
hits a live government site like a human clicking through searches one at
a time.
"""
import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup

import fetch_farevanaa_supplement as fv

AUDIO_SRC_RE = re.compile(r'<audio[^>]*\bsrc="([^"]+)"')


def audio_url_for_word(session, word):
    r = session.post(fv.BASE, data={
        'entree': word, 'orthographe': '', 'sousentree': '',
        'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
    })
    window = fv.tahitien_window(r.text)
    if not window or fv.NO_TAHITIEN_MATCH in window:
        return None

    radio_values = []
    for v in fv.RADIO_VALUE_RE.findall(window):
        if v not in radio_values:
            radio_values.append(v)

    if radio_values:
        # meme mot normalise, plusieurs orthographes possibles - prend la
        # 1re qui a effectivement un audio (evite de tomber sur une variante
        # rare sans enregistrement quand une plus courante en a un).
        for spelling in radio_values:
            time.sleep(fv.DELAY)
            r2 = session.post(fv.BASE, data={
                'entree': word, 'orthographe': spelling, 'sousentree': '',
                'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
            })
            w2 = fv.tahitien_window(r2.text)
            m = AUDIO_SRC_RE.search(w2)
            if m:
                return m.group(1)
        return None

    m = AUDIO_SRC_RE.search(window)
    return m.group(1) if m else None


def main():
    with open('tah_dict.json', encoding='utf-8') as f:
        tah_dict = json.load(f)
    with open('tah_audio.json', encoding='utf-8') as f:
        tah_audio = json.load(f)

    targets = sorted(k for k in tah_dict if ' ' not in k and k not in tah_audio)
    print(f'{len(targets)} mots mono-mot cibles (sans audio Embark deja connu).')

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (research script, ariinui.github.io Buka a Moromona project)'})
    session.get(fv.BASE)

    result = {}
    if os.path.exists('farevanaa_audio.json'):
        with open('farevanaa_audio.json', encoding='utf-8') as f:
            result = json.load(f)

    for i, word in enumerate(targets, 1):
        if word in result:
            continue
        try:
            url = audio_url_for_word(session, word)
        except Exception as e:
            print(f'[{i}/{len(targets)}] {word}: erreur ({e}), on retente une fois')
            time.sleep(fv.DELAY)
            try:
                url = audio_url_for_word(session, word)
            except Exception as e2:
                print(f'[{i}/{len(targets)}] {word}: 2e echec ({e2}), mot saute')
                url = None

        time.sleep(fv.DELAY)

        if url:
            result[word] = url
            print(f'[{i}/{len(targets)}] {word} -> audio trouve')

        if i % 100 == 0:
            with open('farevanaa_audio.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
            print(f'--- checkpoint: {len(result)} audios trouves sur {i}/{len(targets)} mots verifies ---')

    with open('farevanaa_audio.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Termine: {len(result)} audios Fare Vana\'a trouves sur {len(targets)} mots verifies.')


if __name__ == '__main__':
    main()
