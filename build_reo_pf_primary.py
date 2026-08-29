"""Bulk-builds reo_pf_primary.json: for every one of the ~2318 words already
in tah_dict.json, fetches the live https://reo.pf/ dictionary entry in its
own structured form (grammatical category + comma-separated gloss list per
sense, e.g. "vt: battre, frapper," / "vt: tuer,") - same presentation reo.pf
itself uses, validated by hand on 'aamu' and 'taparahi' before being
generalized here.

This is a SEPARATE step from applying the result to tah_dict.json on
purpose: tah_dict.json is a large single-line, insertion-ordered JSON file,
and a full json.load()+json.dump() round-trip reformats and diffs the whole
file for a handful of changed values (already hit once this session, see
memory) - apply_to_tah_dict() instead does a single targeted string
replacement per changed word, verified to occur exactly once, so the git
diff stays proportional to what actually changed.

When a normalized word resolves to more than one reo.pf lexeme (homographs,
ex. "aamu" -> glutton/corrode sense AND recit/histoire sense), every
lexeme's lines are concatenated in order - merge everything found, never
guess which homograph is the intended one (matches build_farevanaa_definitions.py
and the pre-existing tah_dict.json glosses, which already mixed homographs).

A word with NO reo.pf entry keeps its existing tah_dict.json gloss untouched
(this script only ever fills reo_pf_primary.json for words it actually
found - apply_to_tah_dict() only ever replaces entries present there).

Single-threaded, ~1s delay between requests - hits a live government site,
paced like a human clicking through searches one at a time.
"""
import json
import os
import re
import sys
import time
import requests

import fetch_reo_pf_supplement as fv

DELAY = 1.0


def structured_lines_for_lexeme(session, href):
    from bs4 import BeautifulSoup
    r = session.get(href)
    soup = BeautifulSoup(r.text, 'html.parser')
    cols = soup.select('.col-md-4')
    if len(cols) < 2:
        return []
    fr_col = cols[1]
    lines = []
    for li in fr_col.select('ul li'):
        u = li.find('u')
        cat = u.get_text(strip=True) if u else ''
        text = re.sub(r'\s+', ' ', li.get_text(' ', strip=True))
        if cat:
            text = re.sub(r'^' + re.escape(cat) + r'\s*:\s*', '', text, count=1)
        lines.append(f'{cat}: {text}' if cat else text)
    return lines


def structured_text_for_word(session, token, word):
    hrefs = fv.search_exact(session, token, word)
    all_lines = []
    for href in hrefs:
        time.sleep(DELAY)
        for line in structured_lines_for_lexeme(session, href):
            if line not in all_lines:
                all_lines.append(line)
    if not all_lines:
        return None
    return '\n'.join(all_lines)


def scrape():
    with open('tah_dict.json', encoding='utf-8') as f:
        tah_dict = json.load(f)

    targets = sorted(tah_dict.keys())
    print(f'{len(targets)} mots du glossaire a verifier sur reo.pf.')

    result = {}
    if os.path.exists('reo_pf_primary.json'):
        with open('reo_pf_primary.json', encoding='utf-8') as f:
            result = json.load(f)

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (research script, ariinui.github.io Buka a Moromona project)'})
    token = fv.get_token(session)

    done = 0
    for i, word in enumerate(targets, 1):
        if word in result:
            continue
        try:
            text = structured_text_for_word(session, token, word)
        except Exception as e:
            print(f'[{i}/{len(targets)}] {word}: erreur ({e}), nouveau jeton + retente')
            time.sleep(DELAY)
            try:
                token = fv.get_token(session)
                text = structured_text_for_word(session, token, word)
            except Exception as e2:
                print(f'[{i}/{len(targets)}] {word}: 2e echec ({e2}), mot saute')
                text = None

        time.sleep(DELAY)

        if text:
            result[word] = text
            done += 1
            print(f'[{i}/{len(targets)}] {word} -> trouve')

        if i % 50 == 0:
            with open('reo_pf_primary.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
            print(f'--- checkpoint: {len(result)} mots au total ({done} nouveaux) sur {i}/{len(targets)} verifies ---')

    with open('reo_pf_primary.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Termine: {len(result)} mots au total ({done} nouveaux) sur {len(targets)} verifies.')


def apply_to_tah_dict():
    """Merges reo_pf_primary.json into tah_dict.json via targeted string
    replacement (never a full json.dump of tah_dict.json - see module
    docstring)."""
    with open('reo_pf_primary.json', encoding='utf-8') as f:
        replacements = json.load(f)

    with open('tah_dict.json', encoding='utf-8') as f:
        raw = f.read()
    current = json.loads(raw)

    changed = 0
    skipped_missing = 0
    for word, new_val in replacements.items():
        if word not in current:
            skipped_missing += 1
            continue
        old_val = current[word]
        if old_val == new_val:
            continue
        old_frag = json.dumps(word) + ':' + json.dumps(old_val, ensure_ascii=False)
        new_frag = json.dumps(word) + ':' + json.dumps(new_val, ensure_ascii=False)
        count = raw.count(old_frag)
        if count != 1:
            print(f'ATTENTION: {word!r} -> {count} occurrences de son fragment actuel (attendu 1), saute pour securite')
            continue
        raw = raw.replace(old_frag, new_frag)
        changed += 1

    with open('tah_dict.json', 'w', encoding='utf-8') as f:
        f.write(raw)

    final = json.loads(raw)
    assert len(final) == len(current), 'le nombre total de cles a change, quelque chose a mal tourne'
    print(f'{changed} gloses remplacees, {skipped_missing} mots de reo_pf_primary.json absents de tah_dict.json (ignores).')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'apply':
        apply_to_tah_dict()
    else:
        scrape()
