"""One-off: for every Tahitian word in the Livre de Mormon text still without a
French gloss after build_tah_dict.py (SQLite dump + reo_pf_supplement.json +
Embark), check the official Académie Tahitienne - Fare Vāna'a online
dictionary (https://www.farevanaa.pf/fra/dictionnaire). Writes
farevanaa_supplement.json (word -> gloss), which build_tah_dict.py merges in
as a last-resort supplement, on top of everything else, without overwriting
any existing gloss.

Single-threaded, ~1s delay between requests - this hits a live government
site, not a bulk API, so it is deliberately paced like a human clicking
through searches one at a time (same posture as fetch_reo_pf_supplement.py).

Site quirk (found by manual probing before writing this script): the search
form (POST /fra/dictionnaire, no CSRF token) is macron/okina-insensitive
(accents=SANS) but returns an intermediate "choose the spelling" radio-button
page whenever more than one accented spelling normalizes to the same query
(ex. "mana" -> mana / māna / manā / mānā) - a second POST with orthographe=
set to one of those exact spellings is needed to reach the actual entry. A
query with only one matching spelling (ex. "reo") skips straight to the
entry. Either way, the entry itself (<div class="entree">word</div> followed
by <span class="corps">...) always appears right after the closing </FORM>
tag (no anchor when orthographe was set) or after the "entrees_en_tahitien"
anchor (when there was never any ambiguity to begin with), and always ends at
the next <hr> or the page footer - so we bound extraction on that raw HTML
window rather than relying on a specific anchor name being present.
"""
import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup

BASE = 'https://www.farevanaa.pf/fra/dictionnaire'
DELAY = 1.0
MAX_GLOSSES = 6

MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
OKINA_RE = re.compile(r"[‘’ʻ\x27]")

# Memes mecanismes de formes flechies que fetch_reo_pf_supplement.py/
# build_tah_dict.py (duplique ici pour rester un script autonome).
SUFFIXES = ('raa', 'hia')
PREFIXES = ('faa', 'haa')
MIN_ROOT_LEN = 3


def normalize(word):
    word = word.translate(MACRON_MAP)
    word = OKINA_RE.sub('', word)
    return word.lower()


def dereduplicate_candidates(word):
    cands = set()
    for i in range(len(word) - 3):
        chunk = word[i:i + 2]
        if chunk == word[i + 2:i + 4] and chunk.isalpha():
            cands.add(word[:i + 2] + word[i + 4:])
    return cands


def strip_candidates(word):
    bases = {word}
    frontier = [word]
    for _ in range(2):
        next_frontier = []
        for b in frontier:
            for suf in SUFFIXES:
                if b.endswith(suf) and len(b) - len(suf) >= MIN_ROOT_LEN:
                    nb = b[:-len(suf)]
                    if nb not in bases:
                        bases.add(nb)
                        next_frontier.append(nb)
        frontier = next_frontier

    candidates = set()
    for b in bases:
        candidates.add(b)
        for pre in PREFIXES:
            if b.startswith(pre) and len(b) - len(pre) >= MIN_ROOT_LEN:
                candidates.add(b[len(pre):])
        for dc in dereduplicate_candidates(b):
            if len(dc) >= MIN_ROOT_LEN:
                candidates.add(dc)
                for pre in PREFIXES:
                    if dc.startswith(pre) and len(dc) - len(pre) >= MIN_ROOT_LEN:
                        candidates.add(dc[len(pre):])
    candidates.discard(word)
    return candidates


FORM_END_RE = re.compile(r'</FORM>', re.IGNORECASE)
# La page a jusqu'a 2 balises <hr> avant le vrai contenu tahitien qui nous
# interesse (une 1re separe le recapitulatif des ancres, cf. commentaire de
# module) - il faut donc partir de l'ancre elle-meme (quand elle existe), pas
# juste de </FORM>, pour ne pas se faire piegeer par ce <hr> intermediaire.
CHOIX_ANCHOR_RE = re.compile(r'<a name="choix_entrees_en_tahitien">.*?</a>', re.IGNORECASE)
DIRECT_ANCHOR_RE = re.compile(r'<a name="entrees_en_tahitien">.*?</a>', re.IGNORECASE)
STOP_RE = re.compile(r'<hr>|<div id="footer"|<a name="entrees_en_francais"', re.IGNORECASE)
RADIO_VALUE_RE = re.compile(r'type="radio"[^>]*value="([^"]+)"')
NO_TAHITIEN_MATCH = 'Aucun résultat dans les entrées en tahitien'


def tahitien_window(html):
    """Raw HTML slice covering only the Tahitian-entries section of a
    result page (excludes the French-entries section entirely, so a
    reverse French->Tahitian match never leaks into our gloss)."""
    if NO_TAHITIEN_MATCH in html:
        return ''
    m = CHOIX_ANCHOR_RE.search(html) or DIRECT_ANCHOR_RE.search(html)
    if m:
        start = m.end()
    else:
        # Pas d'ancre du tout : cas d'une reponse directe apres un 2e POST
        # avec orthographe deja fixee (voir docstring de module) - le
        # contenu suit directement la fermeture du formulaire.
        m2 = FORM_END_RE.search(html)
        if not m2:
            return ''
        start = m2.end()
    rest = html[start:]
    m3 = STOP_RE.search(rest)
    return rest[:m3.start()] if m3 else rest


def entries_in_window(window):
    """List of (word_text, definitions[]) for every headword found in this
    HTML window - definitions are the blue "color:#04408C" phrase divs,
    which is where this dictionary's actual French gloss text lives
    (orange divs are grammatical category, plain/italic divs are usage
    examples - both skipped)."""
    soup = BeautifulSoup(window, 'html.parser')
    out = []
    for entree_div in soup.select('div.entree'):
        word_text = entree_div.get_text(strip=True)
        corps = entree_div.find_next('span', class_='corps')
        if not corps:
            continue
        defs = []
        for phrase in corps.find_all('div', class_='phrase'):
            style = (phrase.get('style') or '').lower().replace(' ', '')
            if 'color:#04408c' in style:
                text = re.sub(r'\s+', ' ', phrase.get_text(' ', strip=True)).strip(' .')
                if text and text not in defs:
                    defs.append(text)
        out.append((word_text, defs))
    return out


def glosses_for_word(session, word):
    """Queries the dictionary for `word` (already normalized) and returns
    a merged, deduped list of French definitions across every accented
    spelling / homograph sense the site returns for it."""
    r = session.post(BASE, data={
        'entree': word, 'orthographe': '', 'sousentree': '',
        'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
    })
    window = tahitien_window(r.text)
    if not window or NO_TAHITIEN_MATCH in window:
        return []

    radio_values = []
    for v in RADIO_VALUE_RE.findall(window):
        if v not in radio_values:
            radio_values.append(v)

    all_defs = []
    if radio_values:
        for spelling in radio_values:
            time.sleep(DELAY)
            r2 = session.post(BASE, data={
                'entree': word, 'orthographe': spelling, 'sousentree': '',
                'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
            })
            w2 = tahitien_window(r2.text)
            for word_text, defs in entries_in_window(w2):
                if normalize(word_text) != word:
                    continue
                for d in defs:
                    if d not in all_defs:
                        all_defs.append(d)
    else:
        for word_text, defs in entries_in_window(window):
            if normalize(word_text) != word:
                continue
            for d in defs:
                if d not in all_defs:
                    all_defs.append(d)

    return all_defs[:MAX_GLOSSES]


def main():
    with open('tah_dict.json', encoding='utf-8') as f:
        tah_dict = json.load(f)

    with open('livre_de_mormon.html', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    WORD_RE = re.compile(r"[A-Za-zĀĒĪŌŪāēīōū][A-Za-zĀĒĪŌŪāēīōū‘’ʻ\x27]*")
    full_text = ' '.join(d.get_text(' ') for d in soup.find_all('div', class_='tahitien'))
    used_keys = {normalize(t) for t in WORD_RE.findall(full_text)}
    unglossed = sorted(k for k in used_keys if k not in tah_dict)

    to_query = set(unglossed)
    for w in unglossed:
        to_query.update(strip_candidates(w))
    to_query = sorted(to_query)

    print(f'{len(unglossed)} mots sans glose, {len(to_query)} formes a verifier sur farevanaa.pf (racines candidates incluses)')

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (research script, ariinui.github.io Buka a Moromona project)'})
    session.get('https://www.farevanaa.pf/fra/dictionnaire')

    result = {}
    if os.path.exists('farevanaa_supplement.json'):
        with open('farevanaa_supplement.json', encoding='utf-8') as f:
            result = json.load(f)

    for i, word in enumerate(to_query, 1):
        try:
            defs = glosses_for_word(session, word)
        except Exception as e:
            print(f'[{i}/{len(to_query)}] {word}: erreur ({e}), on retente une fois')
            time.sleep(DELAY)
            try:
                defs = glosses_for_word(session, word)
            except Exception as e2:
                print(f'[{i}/{len(to_query)}] {word}: 2e echec ({e2}), mot saute')
                defs = []

        time.sleep(DELAY)

        if defs:
            result[word] = ', '.join(defs)
            print(f'[{i}/{len(to_query)}] {word} -> {result[word]}')

        if i % 50 == 0:
            with open('farevanaa_supplement.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
            print(f'--- checkpoint: {len(result)} mots recuperes sur {i} verifies ---')

    with open('farevanaa_supplement.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Termine: {len(result)} mots recuperes sur {len(to_query)} verifies.')


if __name__ == '__main__':
    main()
