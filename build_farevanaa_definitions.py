"""Bulk-builds tah_definitions.json: for every one of the ~2318 words already
in tah_dict.json (not just gap words), fetches the full, structured
definition from the official Academie Tahitienne - Fare Vana'a online
dictionary (https://www.farevanaa.pf/fra/dictionnaire).

Reuses the disambiguation-page handling (multiple accented spellings for one
normalized query) already proven in fetch_farevanaa_supplement.py, but the
extraction itself is new: instead of grabbing only the blue "definition"
divs (color:#04408C), this walks every relevant child of span.corps in
document order (grammatical category in orange color:#ff8c00, sense number
in div.sn, definition in blue) to reconstruct a multi-sense, multi-category
text exactly like the site itself presents it - validated by hand on
'ā'amu (1 sense) and taparahi (2 numbered senses under one category) before
being generalized here. Examples, Cf./Syn., and sub-locutions are skipped
by construction (they never match the 3 markers above).

When a normalized word resolves to more than one accented spelling (ex.
"aamu" -> 'a'amu AND 'ā'amu, two different homographs), every spelling's
structured text is concatenated in turn - same "merge every sense found,
never guess which homograph is the right one" posture as the primary
reo.pf replacement (build_reo_pf_primary.py) and as the pre-existing
tah_dict.json glosses (which already mixed homographs before this feature
existed).

Single-threaded, ~1s delay between requests - hits a live government site,
paced like a human clicking through searches one at a time.

Checkpointed to tah_definitions.json every 50 words so an interruption never
loses progress; already-present words are skipped on a re-run.
"""
import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup

import fetch_farevanaa_supplement as fv

DELAY = 1.0


def structured_definition_for_window(window):
    """List of (word_text, structured_text) for every headword entry found
    in this HTML window, walking span.corps children in order."""
    soup = BeautifulSoup(window, 'html.parser')
    out = []
    for entree_div in soup.select('div.entree'):
        word_text = entree_div.get_text(strip=True)
        corps = entree_div.find_next('span', class_='corps')
        if not corps:
            continue
        lines = []
        pending_cat = None
        pending_num = None
        cat_emitted = True
        for div in corps.find_all('div'):
            classes = div.get('class') or []
            style = (div.get('style') or '').lower().replace(' ', '')
            text = div.get_text(' ', strip=True)
            if 'sn' in classes:
                if pending_cat is not None and not cat_emitted:
                    lines.append(pending_cat)
                    cat_emitted = True
                pending_num = text
                continue
            if 'color:#ff8c00' in style:
                pending_cat = text
                cat_emitted = False
                pending_num = None
                continue
            if 'color:#04408c' in style:
                if pending_num:
                    lines.append(f'{pending_num} {text}')
                    pending_num = None
                elif pending_cat is not None and not cat_emitted:
                    lines.append(f'{pending_cat} {text}')
                    cat_emitted = True
                else:
                    lines.append(text)
                continue
            # tout le reste (exemples, sous-locutions, Cf./Syn.) est ignore
        if lines:
            out.append((word_text, '\n'.join(lines)))
    return out


def structured_definition_for_word(session, word):
    """Queries farevanaa.pf for `word` (already normalized) and returns the
    merged structured text across every accented spelling / homograph the
    site returns for it, or None if nothing found."""
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

    all_lines = []
    if radio_values:
        for spelling in radio_values:
            time.sleep(DELAY)
            r2 = session.post(fv.BASE, data={
                'entree': word, 'orthographe': spelling, 'sousentree': '',
                'perimetre': 'TAH+FRA', 'mode': 'EXACT', 'accents': 'SANS',
            })
            w2 = fv.tahitien_window(r2.text)
            for word_text, text in structured_definition_for_window(w2):
                if fv.normalize(word_text) != word:
                    continue
                if text not in all_lines:
                    all_lines.append(text)
    else:
        for word_text, text in structured_definition_for_window(window):
            if fv.normalize(word_text) != word:
                continue
            if text not in all_lines:
                all_lines.append(text)

    if not all_lines:
        return None
    return '\n'.join(all_lines)


def main():
    with open('tah_dict.json', encoding='utf-8') as f:
        tah_dict = json.load(f)

    targets = sorted(tah_dict.keys())
    print(f'{len(targets)} mots du glossaire a verifier sur farevanaa.pf.')

    result = {}
    if os.path.exists('tah_definitions.json'):
        with open('tah_definitions.json', encoding='utf-8') as f:
            result = json.load(f)

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (research script, ariinui.github.io Buka a Moromona project)'})
    session.get('https://www.farevanaa.pf/fra/dictionnaire')

    done = 0
    for i, word in enumerate(targets, 1):
        if word in result:
            continue
        try:
            text = structured_definition_for_word(session, word)
        except Exception as e:
            print(f'[{i}/{len(targets)}] {word}: erreur ({e}), on retente une fois')
            time.sleep(DELAY)
            try:
                text = structured_definition_for_word(session, word)
            except Exception as e2:
                print(f'[{i}/{len(targets)}] {word}: 2e echec ({e2}), mot saute')
                text = None

        time.sleep(DELAY)

        if text:
            result[word] = {'text': text}
            done += 1
            print(f'[{i}/{len(targets)}] {word} -> trouve')

        if i % 50 == 0:
            with open('tah_definitions.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
            print(f'--- checkpoint: {len(result)} definitions au total ({done} nouvelles) sur {i}/{len(targets)} mots verifies ---')

    with open('tah_definitions.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Termine: {len(result)} definitions au total ({done} nouvelles) sur {len(targets)} mots verifies.')


if __name__ == '__main__':
    main()
