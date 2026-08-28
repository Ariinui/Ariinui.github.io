"""One-off: harvests Tahitian multi-word expressions (locutions) from the
Académie Tahitienne - Fare Vāna'a online dictionary and keeps only the ones
that actually occur, word-for-word and adjacently, in the Livre de Mormon
Tahitian text - so they can be tap-to-translate'd as a single group, exactly
like the 71 Embark verb+particle groups in embark_phrases.json already are
(generate_pages.py's wrap_tah_words() already matches groups of 2-5 adjacent
words against tah_dict, MAX_PHRASE_WORDS=5 - no site code change needed,
only more phrase data).

Unlike fetch_farevanaa_supplement.py (which only queries the ~425 words
still missing a gloss), this queries EVERY word actually used in the text
(~2385, `used_keys`) - a locution can be tucked inside the dictionary page
of a word that is itself already fully glossed (ex. "mana" is resolved, but
its page also lists the locutions "mana fa'ahepo"/"mana 'aifaufa'a"), so
the gap-only word list from the other script would miss it entirely.

Site quirk (locution sub-entries, found by inspecting a raw "mana" result
page before writing this script): inside a headword's <span class="corps">,
a locution is a <div class="phrase" style="font-weight:550;...;
text-transform:uppercase;">LOCUTION TEXT</div> immediately followed by a
plain <div class="phrase"> holding its French definition in single curly
quotes - visually and structurally distinct from an example sentence, which
uses font-weight:bold (700, not 550) without text-transform:uppercase and is
followed by a source citation before its translation, not a definition
directly.

Same posture as the two scripts above: single-threaded, ~1s delay, hits a
live government site like a human clicking through searches one at a time.
"""
import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup

import fetch_farevanaa_supplement as fv

MAX_PHRASE_WORDS = 5  # garde en phase avec generate_pages.py


def locutions_in_window(window):
    """List of (locution_text, definition) found in this HTML window - a
    locution headword is bold(550)+uppercase, its definition is the very
    next plain <div class="phrase"> (no style at all)."""
    soup = BeautifulSoup(window, 'html.parser')
    phrases = soup.find_all('div', class_='phrase')
    out = []
    for i, div in enumerate(phrases):
        style = (div.get('style') or '').lower().replace(' ', '')
        if 'font-weight:550' not in style or 'text-transform:uppercase' not in style:
            continue
        locution_text = div.get_text(' ', strip=True)
        if i + 1 >= len(phrases):
            continue
        nxt = phrases[i + 1]
        if nxt.get('style'):
            continue  # pas une definition (ex: encore une autre locution)
        definition = re.sub(r'\s+', ' ', nxt.get_text(' ', strip=True)).strip()
        definition = definition.strip('‘’\' ').strip()
        # "- Cf. X" / "- Syn. X" : renvoi vers une autre entree, pas une
        # vraie definition - inutile (voire trompeur) en popup de traduction.
        if definition.lower().startswith(('cf.', 'syn.', '- cf.', '- syn.')):
            continue
        if locution_text and definition:
            out.append((locution_text, definition))
    return out


def locutions_for_word(session, word):
    """Comme fv.glosses_for_word, mais recolte les locutions plutot que la
    glose principale - interroge les memes pages (1 ou plusieurs
    orthographes selon ambiguite)."""
    r = session.post(fv.BASE, data={
        'entree': word, 'orthographe': '', 'sousentree': '',
        'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
    })
    window = fv.tahitien_window(r.text)
    if not window or fv.NO_TAHITIEN_MATCH in window:
        return []

    radio_values = []
    for v in fv.RADIO_VALUE_RE.findall(window):
        if v not in radio_values:
            radio_values.append(v)

    found = []
    if radio_values:
        for spelling in radio_values:
            time.sleep(fv.DELAY)
            r2 = session.post(fv.BASE, data={
                'entree': word, 'orthographe': spelling, 'sousentree': '',
                'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
            })
            w2 = fv.tahitien_window(r2.text)
            found.extend(locutions_in_window(w2))
    else:
        found.extend(locutions_in_window(window))

    return found


def build_real_ngrams(soup):
    """Toute sequence de 2 a MAX_PHRASE_WORDS mots reellement adjacents
    (separes par un seul espace, jamais au travers de 2 divs differents -
    evite les faux positifs de fin/debut de verset) dans le texte tahitien,
    sous forme de cle 'mot1 mot2 ...' normalisee - exactement le format que
    wrap_tah_words() (generate_pages.py) cherche dans tah_dict a la
    generation."""
    real = set()
    for tah_div in soup.find_all('div', class_='tahitien'):
        text = tah_div.get_text(' ')
        matches = list(WORD_RE.finditer(text))
        for i in range(len(matches)):
            for span in range(2, min(MAX_PHRASE_WORDS, len(matches) - i) + 1):
                group = matches[i:i + span]
                if any(text[group[j].end():group[j + 1].start()] != ' ' for j in range(len(group) - 1)):
                    break  # un trou casse toute extension plus longue aussi
                key = ' '.join(fv.normalize(g.group(0)) for g in group)
                real.add(key)
    return real


WORD_RE = re.compile(r"[A-Za-zĀĒĪŌŪāēīōū][A-Za-zĀĒĪŌŪāēīōū‘’ʻ\x27]*")


def main():
    with open('livre_de_mormon.html', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    full_text = ' '.join(d.get_text(' ') for d in soup.find_all('div', class_='tahitien'))
    used_keys = sorted({fv.normalize(t) for t in WORD_RE.findall(full_text)})

    print(f'{len(used_keys)} mots a interroger sur farevanaa.pf pour en extraire les locutions.')
    real_ngrams = build_real_ngrams(soup)
    print(f'{len(real_ngrams)} groupes de 2-{MAX_PHRASE_WORDS} mots reellement adjacents dans le texte (candidats a matcher).')

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (research script, ariinui.github.io Buka a Moromona project)'})
    session.get(fv.BASE)

    result = {}
    if os.path.exists('farevanaa_phrases.json'):
        with open('farevanaa_phrases.json', encoding='utf-8') as f:
            result = json.load(f)

    all_found_raw = 0
    for i, word in enumerate(used_keys, 1):
        try:
            locutions = locutions_for_word(session, word)
        except Exception as e:
            print(f'[{i}/{len(used_keys)}] {word}: erreur ({e}), on retente une fois')
            time.sleep(fv.DELAY)
            try:
                locutions = locutions_for_word(session, word)
            except Exception as e2:
                print(f'[{i}/{len(used_keys)}] {word}: 2e echec ({e2}), mot saute')
                locutions = []

        time.sleep(fv.DELAY)
        all_found_raw += len(locutions)

        for loc_text, definition in locutions:
            words = [fv.normalize(w) for w in WORD_RE.findall(loc_text)]
            if not (2 <= len(words) <= MAX_PHRASE_WORDS):
                continue
            key = ' '.join(words)
            if key not in real_ngrams:
                continue  # locution valide mais absente du texte de ce livre
            if key not in result:
                result[key] = definition
                print(f'[{i}/{len(used_keys)}] {word} -> locution retenue "{key}" : {definition}')

        if i % 100 == 0:
            with open('farevanaa_phrases.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
            print(f'--- checkpoint: {len(result)} locutions retenues sur {i}/{len(used_keys)} mots verifies ({all_found_raw} locutions brutes vues) ---')

    with open('farevanaa_phrases.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Termine: {len(result)} locutions retenues (presentes dans le texte) sur {all_found_raw} locutions brutes vues au total.')


if __name__ == '__main__':
    main()
