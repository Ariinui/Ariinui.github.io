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


# --- Formes flechies : prefixe causatif faa-/haa-, suffixe passif -hia,
# suffixe nominalisant -raa - detachees puis reverifiees contre le vrai
# dictionnaire (jamais une devinette non verifiee : un candidat n'est retenu
# que s'il matche reellement une entree ty existante).
SUFFIXES = ('raa', 'hia')
PREFIXES = ('faa', 'haa')
MIN_ROOT_LEN = 3


def strip_candidates(word):
    bases = {word}
    frontier = [word]
    for _ in range(2):  # jusqu'a 2 suffixes empiles (ex: -hia puis -raa)
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
    candidates.discard(word)
    return candidates


with open('livre_de_mormon.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'lxml')

full_text = ' '.join(d.get_text(' ') for d in soup.find_all('div', class_='tahitien'))
used_keys = {normalize(t) for t in WORD_RE.findall(full_text)}

con = sqlite3.connect(SQLITE_PATH)
cur = con.cursor()
cur.execute("SELECT _id, normalized FROM entries WHERE idiom='ty'")
all_ty = cur.fetchall()
ty_ids_by_norm_all = {}
for _id, norm in all_ty:
    ty_ids_by_norm_all.setdefault(norm, []).append(_id)


def glosses_for(ty_ids):
    q = 'SELECT lexeme FROM entries WHERE idiom="fr" AND entry_id IN (%s)' % ','.join('?' * len(ty_ids))
    cur.execute(q, ty_ids)
    seen = []
    for (lex,) in cur.fetchall():
        if lex not in seen:
            seen.append(lex)
        if len(seen) >= MAX_GLOSSES:
            break
    return seen


result = {}
derived_count = 0
for key in used_keys:
    ty_ids = ty_ids_by_norm_all.get(key)
    if ty_ids:
        seen = glosses_for(ty_ids)
        if seen:
            result[key] = ', '.join(seen)
        continue

    # pas de match direct : tente les formes flechies, garde la premiere
    # racine reelle trouvee dans le dictionnaire
    for cand in strip_candidates(key):
        cand_ids = ty_ids_by_norm_all.get(cand)
        if not cand_ids:
            continue
        seen = glosses_for(cand_ids)
        if seen:
            result[key] = ', '.join(seen) + f' (dérivé de « {cand} »)'
            derived_count += 1
            break

with open('tah_dict.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

print(f'{len(result)} mots avec glose ({derived_count} via formes flechies), sur {len(used_keys)} formes uniques dans le texte.')
import os
print('tah_dict.json:', os.path.getsize('tah_dict.json'), 'octets')
