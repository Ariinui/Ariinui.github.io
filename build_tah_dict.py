"""One-off extraction: builds tah_dict.json (word -> short French gloss) from
the REO dictionary SQLite, restricted to the vocabulary actually used in the
Tahitian Livre de Mormon text. Run once; the SQLite source (from an extracted
APK, outside this repo) is NOT a build dependency of generate_pages.py -
only the resulting JSON is committed.
"""
import json
import re
import sqlite3
from bs4 import BeautifulSoup

SQLITE_PATH = r'C:/Users/ariin/Downloads/REO_3.0.2_APKPure (2)/pf.culture.sti.reo/assets/reo4_clear.sqlite'
MAX_GLOSSES = 6

MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
OKINA_RE = re.compile(r"[\u2018\u2019\u02bb\x27]")
WORD_RE = re.compile(r"[A-Za-zĀĒĪŌŪāēīōū][A-Za-zĀĒĪŌŪāēīōū\u2018\u2019\u02bb\x27]*")


def normalize(word):
    word = word.translate(MACRON_MAP)
    word = OKINA_RE.sub('', word)
    return word.lower()


with open('livre_de_mormon.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'lxml')

full_text = ' '.join(d.get_text(' ') for d in soup.find_all('div', class_='tahitien'))
used_keys = {normalize(t) for t in WORD_RE.findall(full_text)}

con = sqlite3.connect(SQLITE_PATH)
cur = con.cursor()
cur.execute("SELECT _id, normalized FROM entries WHERE idiom='ty'")
ty_ids_by_norm = {}
for _id, norm in cur.fetchall():
    if norm in used_keys:
        ty_ids_by_norm.setdefault(norm, []).append(_id)

result = {}
for norm, ty_ids in ty_ids_by_norm.items():
    q = 'SELECT lexeme FROM entries WHERE idiom="fr" AND entry_id IN (%s)' % ','.join('?' * len(ty_ids))
    cur.execute(q, ty_ids)
    seen = []
    for (lex,) in cur.fetchall():
        if lex not in seen:
            seen.append(lex)
        if len(seen) >= MAX_GLOSSES:
            break
    if seen:
        result[norm] = ', '.join(seen)

with open('tah_dict.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

print(f'{len(result)} mots avec glose, sur {len(used_keys)} formes uniques dans le texte.')
import os
print('tah_dict.json:', os.path.getsize('tah_dict.json'), 'octets')
