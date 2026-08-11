"""One-off: for every Tahitian word in the Livre de Mormon text still without a
French gloss after build_tah_dict.py, check the live https://reo.pf/ dictionary
(same REO project, but kept up to date - unlike our offline APK-extracted
SQLite dump which is a stale snapshot). Writes reo_pf_supplement.json
(word -> gloss), which build_tah_dict.py merges in on top of the SQLite
result without overwriting anything the SQLite already answered.

Single-threaded, ~1s delay between requests - this hits a live government
site, not a bulk API, so it is deliberately paced like a human clicking
through searches one at a time.
"""
import json
import re
import time
import requests
from bs4 import BeautifulSoup

BASE = 'https://reo.pf'
DELAY = 1.0
MAX_GLOSSES = 6

MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
OKINA_RE = re.compile(r"[‘’ʻ\x27]")


def normalize(word):
    word = word.translate(MACRON_MAP)
    word = OKINA_RE.sub('', word)
    return word.lower()


def get_token(session):
    r = session.get(BASE + '/')
    soup = BeautifulSoup(r.text, 'html.parser')
    return soup.find('input', {'name': '_token'})['value']


def search_exact(session, token, word):
    """Returns list of (href, normalized_lexeme) for exact normalized matches
    in the 'Tahitien' results column."""
    r = session.post(BASE + '/search', data={'_token': token, 'q': word})
    soup = BeautifulSoup(r.text, 'html.parser')
    columns = soup.select('.col-md-4')
    if not columns:
        return []
    tahitien_col = columns[0]
    matches = []
    for a in tahitien_col.select('ul li a'):
        lexeme = a.get_text(strip=True)
        if normalize(lexeme) == word:
            matches.append(a['href'])
    return matches


def glosses_from_lexeme_page(session, href):
    r = session.get(href)
    soup = BeautifulSoup(r.text, 'html.parser')
    columns = soup.select('.col-md-4')
    if len(columns) < 2:
        return []
    fr_col = columns[1]
    glosses = []
    for li in fr_col.select('ul li'):
        text = li.get_text(' ', strip=True)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^[^:]*:\s*', '', text, count=1)  # drop leading "nc :" / "n nom :" etc.
        for part in text.split(','):
            part = part.strip().rstrip(',')
            if part and part not in glosses:
                glosses.append(part)
            if len(glosses) >= MAX_GLOSSES:
                break
        if len(glosses) >= MAX_GLOSSES:
            break
    return glosses


def main():
    with open('tah_dict.json', encoding='utf-8') as f:
        tah_dict = json.load(f)

    from bs4 import BeautifulSoup as BS
    with open('livre_de_mormon.html', encoding='utf-8') as f:
        soup = BS(f, 'html.parser')
    WORD_RE = re.compile(r"[A-Za-zĀĒĪŌŪāēīōū][A-Za-zĀĒĪŌŪāēīōū‘’ʻ\x27]*")
    full_text = ' '.join(d.get_text(' ') for d in soup.find_all('div', class_='tahitien'))
    used_keys = {normalize(t) for t in WORD_RE.findall(full_text)}
    unglossed = sorted(k for k in used_keys if k not in tah_dict)

    print(f'{len(unglossed)} mots a revernifier sur reo.pf')

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (research script, ariinui.github.io Buka a Moromona project)'})
    token = get_token(session)

    result = {}
    for i, word in enumerate(unglossed, 1):
        try:
            hrefs = search_exact(session, token, word)
        except Exception as e:
            print(f'[{i}/{len(unglossed)}] {word}: erreur recherche ({e}), on retente avec un nouveau jeton')
            time.sleep(DELAY)
            token = get_token(session)
            hrefs = search_exact(session, token, word)

        time.sleep(DELAY)

        glosses = []
        for href in hrefs:
            time.sleep(DELAY)
            glosses.extend(g for g in glosses_from_lexeme_page(session, href) if g not in glosses)

        if glosses:
            result[word] = ', '.join(glosses[:MAX_GLOSSES])
            print(f'[{i}/{len(unglossed)}] {word} -> {result[word]}')

        if i % 50 == 0:
            with open('reo_pf_supplement.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
            print(f'--- checkpoint: {len(result)} mots recuperes sur {i} verifies ---')

    with open('reo_pf_supplement.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f'Termine: {len(result)} mots recuperes sur {len(unglossed)} verifies.')


if __name__ == '__main__':
    main()
