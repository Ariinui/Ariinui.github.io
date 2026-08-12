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
# suffixe nominalisant -raa, redoublement de l'avant-derniere syllabe pour
# le pluriel/l'intensif d'un adjectif (ex. maita'i -> maitata'i, rahi ->
# rarahi) - detachees/desassemblees puis reverifiees contre le vrai
# dictionnaire (jamais une devinette non verifiee : un candidat n'est retenu
# que s'il matche reellement une entree ty existante).
SUFFIXES = ('raa', 'hia')
PREFIXES = ('faa', 'haa')
MIN_ROOT_LEN = 3


def dereduplicate_candidates(word):
    """Un mot forme en redoublant un bloc de 2 lettres adjacent (ex.
    "maitatai" = "maita" + "ta" redouble + "i") redonne la racine en
    retirant une des deux copies. Genere un candidat par occurrence
    trouvee - chacun sera reverifie contre le dictionnaire comme les
    autres formes flechies, donc un faux positif isole ne matche
    simplement rien et est ignore silencieusement."""
    cands = set()
    for i in range(len(word) - 3):
        chunk = word[i:i + 2]
        if chunk == word[i + 2:i + 4] and chunk.isalpha():
            cands.add(word[:i + 2] + word[i + 4:])
    return cands


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
        for dc in dereduplicate_candidates(b):
            if len(dc) >= MIN_ROOT_LEN:
                candidates.add(dc)
                for pre in PREFIXES:
                    if dc.startswith(pre) and len(dc) - len(pre) >= MIN_ROOT_LEN:
                        candidates.add(dc[len(pre):])
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

    # pas de match direct (ou entree existante mais sans glose fr, ex.
    # entree "coquille vide"/gloss anglais seul) : tente les formes
    # flechies, garde la premiere racine reelle trouvee dans le dictionnaire
    for cand in strip_candidates(key):
        cand_ids = ty_ids_by_norm_all.get(cand)
        if not cand_ids:
            continue
        seen = glosses_for(cand_ids)
        if seen:
            result[key] = ', '.join(seen) + f' (dérivé de « {cand} »)'
            derived_count += 1
            break

sqlite_count = len(result)

# Supplements : comblent les mots absents du dump SQLite (coquille vide,
# emprunt biblique/religieux absent d'un dictionnaire general...) via des
# sources verifiees separement (reo.pf en direct, vocabulaire Embark).
import os

# reo.pf ne comble que les trous - ne remplace jamais une glose du SQLite.
if os.path.exists('reo_pf_supplement.json'):
    with open('reo_pf_supplement.json', encoding='utf-8') as f:
        reo_pf_supplement = json.load(f)
    added = 0
    for key, gloss in reo_pf_supplement.items():
        if key in used_keys and key not in result:
            result[key] = gloss
            added += 1
    print(f'{added} mots ajoutes depuis le supplement reo.pf.')

# Embark est prioritaire : ses sens (vocabulaire missionnaire/religieux,
# plus pertinent pour un texte comme le Livre de Mormon) sont places en
# tete, mais fusionnes avec les sens deja trouves (SQLite/reo.pf) plutot
# que de les ecraser - un mot tres frequent (particule grammaticale...) ou
# polysemique garde tous ses sens connus, pas seulement celui d'Embark.
if os.path.exists('embark_supplement.json'):
    with open('embark_supplement.json', encoding='utf-8') as f:
        embark_supplement = json.load(f)
    added, merged = 0, 0
    for key, gloss in embark_supplement.items():
        if key not in used_keys:
            continue
        embark_parts = [p.strip() for p in gloss.split(',') if p.strip()]
        if key in result:
            existing_parts = [p.strip() for p in result[key].split(',') if p.strip()]
            combined = list(embark_parts)
            for p in existing_parts:
                if p not in combined:
                    combined.append(p)
            result[key] = ', '.join(combined[:MAX_GLOSSES])
            merged += 1
        else:
            result[key] = gloss
            added += 1
    print(f'{added} mots ajoutes et {merged} mots enrichis depuis le supplement Embark.')

# Groupes de 2 mots (verbes composes avec particule directionnelle, ex.
# "haere mai" = venir / "haere atu" = partir - un sens propre, pas juste
# "haere" + un modificateur) extraits d'Embark. Cles avec un espace, donc
# jamais en conflit avec une entree mot-a-mot deja presente - inclus tel
# quel, sans filtrage par used_keys (qui ne connait que des mots isoles) :
# generate_pages.py ne s'en sert que s'il trouve reellement les 2 mots
# adjacents dans le texte, une entree non utilisee ne fait rien de mal.
if os.path.exists('embark_phrases.json'):
    with open('embark_phrases.json', encoding='utf-8') as f:
        embark_phrases = json.load(f)
    for key, gloss in embark_phrases.items():
        result.setdefault(key, gloss)
    print(f'{len(embark_phrases)} groupes de 2 mots ajoutes depuis Embark.')

# 2e passe de formes flechies : une racine peut etre une coquille vide
# dans le dump SQLite (comme "tāpuni", derive de "tāpunira'a" - Mosiah
# 20:5) mais avoir une vraie traduction recuperee via reo.pf/Embark. La
# premiere passe (plus haut) ne testait les racines candidates que contre
# le SQLite ; celle-ci les teste aussi contre les 2 supplements, pour les
# mots encore sans glose apres tout ce qui precede.
combined_root_glosses = {}
if os.path.exists('reo_pf_supplement.json'):
    combined_root_glosses.update(reo_pf_supplement)
if os.path.exists('embark_supplement.json'):
    for k, v in embark_supplement.items():
        combined_root_glosses.setdefault(k, v)

second_pass_count = 0
for key in list(used_keys):
    if key in result:
        continue
    for cand in strip_candidates(key):
        if cand in combined_root_glosses:
            result[key] = combined_root_glosses[cand] + f' (dérivé de « {cand} »)'
            second_pass_count += 1
            break
print(f'{second_pass_count} mots recuperes en 2e passe (racine trouvee via reo.pf/Embark, pas le SQLite).')

# Contexte francais : le dictionnaire REO melange parfois plusieurs mots
# tahitiens sans rapport qui partagent la meme forme normalisee (des vrais
# homographes non lies), ex. papa'i affichait "reciter un conte, baton,
# frappeur, cloison..." melange a son vrai sens "ecrire" (confirme a la
# main sur ses 381 occurrences dans le LdM). Le texte francais aligne
# verset par verset sert de preuve reelle (pas une supposition) pour
# trier les sens deja presents : ceux attestes dans au moins un verset
# aligne passent en tete, le reste (mauvais homographes probables) reste
# a la suite - rien n'est jamais supprime, juste reordonne.
# Quand AUCUN sens existant n'est atteste (le bon sens n'est meme pas
# dans la liste, comme papa'i au depart), un mot francais est propose
# depuis le contexte lui-meme (frequence dans les versets contenant le
# mot tahitien, comparee a sa frequence de base dans tout le livre) et
# ajoute en tete, marque "(depuis le contexte)" pour rester distinguable
# d'une glose verifiee par dictionnaire - c'est une deduction, pas un
# hit verifie comme le reste.
import unicodedata
from collections import Counter

FR_STOPWORDS = {
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'a', 'en',
    'que', 'qui', 'quoi', 'se', 'pour', 'dans', 'sur', 'ce', 'cette', 'ces',
    'au', 'aux', 'est', 'etre', 'avoir', 'il', 'elle', 'ils', 'elles', 'je',
    'tu', 'nous', 'vous', 'on', 'ne', 'pas', 'plus', 'moins', 'son', 'sa',
    'ses', 'leur', 'leurs', 'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'notre',
    'votre', 'mais', 'donc', 'or', 'ni', 'car', 'comme', 'si', 'tout',
    'tous', 'toute', 'toutes', 'fut', 'etait', 'ete', 'avait', 'ont', 'sont',
    'oui', 'non', 'moi', 'toi', 'lui', 'eux', 'y', 'meme', 'bien', 'aussi',
    'sa', 'ca', 'la',
    # formules narratives omnipresentes dans le LdM, sans rapport avec le
    # mot tahitien voisin (ex. "il arriva que" ~ tournure de chaque
    # chapitre) - fausses correspondances frequentes sinon.
    'arriva', 'maintenant', 'lorsque', 'voici', 'avec', 'chose', 'choses',
    'alors', 'ainsi', 'ici', 'la-bas', 'toutefois', 'cependant', 'selon',
    # Dieu/Seigneur : mots religieux omnipresents (majorite des versets),
    # deja couverts par le dictionnaire pour leurs vrais mots tahitiens -
    # en excedent, coincident trop souvent avec un mot voisin sans en etre
    # la traduction (observe empiriquement sur plusieurs faux positifs).
    'dieu', 'seigneur',
    # faire/etre a tous les temps : verbes-supports omnipresents (locutions
    # comme "il arriva que", tournures passives...), pas des traductions.
    'fait', 'faire', 'font', 'ferait', 'feront', 'faisait', 'faisaient',
    'firent', 'fis', 'fasse', 'faites', 'faisant',
}


def strip_accents(s):
    s = s.replace('œ', 'oe').replace('Œ', 'OE').replace('æ', 'ae').replace('Æ', 'AE')
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def fr_words(text):
    return re.findall(r"[A-Za-zÀ-ÿŒœÆæ]+", text)


def content_stem(word):
    w = strip_accents(word.lower())
    w = re.sub(r'[^a-z]', '', w)
    if not w or w in FR_STOPWORDS or len(w) < 4:
        return None
    return w[:4]


def part_stem(part):
    for w in fr_words(part):
        st = content_stem(w)
        if st:
            return st
    return None


# Pre-passe : detecte les noms propres (mots capitalises ailleurs qu'en
# debut de verset, ex. Nephi, Lamana, Sion...) pour ne jamais les proposer
# comme "traduction" d'un mot tahitien courant plus bas - un personnage ou
# lieu tres mentionne peut co-occurrer tres souvent avec un verbe/adjectif
# frequent sans en etre du tout la traduction (observe empiriquement :
# "faaara" (reveiller) ressortait "nephi", "ati" ressortait "lamanites").
# Bloque le MOT EXACT (pas sa racine) : "Ecritures" (majuscule legitime,
# reference aux ecritures saintes) partage la racine "ecri" avec le verbe
# "ecrire"/"ecrit" - bloquer toute la racine aurait aussi exclu ce dernier,
# qui lui est un vrai sens frequent (papa'i).
proper_noun_words = set()
for tah_div in soup.find_all('div', class_='tahitien'):
    container = tah_div.parent
    fr_div = container.find('div', class_='francais') if container else None
    if not fr_div:
        continue
    words = fr_words(fr_div.get_text(' '))
    for i, w in enumerate(words):
        if i > 0 and w[0].isupper():
            proper_noun_words.add(w.lower())

# mot tahitien normalise -> liste des textes francais des versets ou il
# apparait. Compte aussi la frequence de base de chaque RACINE francaise
# (verbes conjugues regroupes - "ecrit"/"ecrire"/"ecrivit" partagent tous
# la racine "ecri") sur l'ensemble du livre, et garde la forme de surface
# la plus frequente de chaque racine pour l'affichage.
word_to_french = {}
global_stem_counts = Counter()
stem_surface_counts = {}
total_verses = 0
for tah_div in soup.find_all('div', class_='tahitien'):
    container = tah_div.parent
    fr_div = container.find('div', class_='francais') if container else None
    if not fr_div:
        continue
    fr_text = fr_div.get_text(' ')
    total_verses += 1
    stems_in_fr = set()
    for w in fr_words(fr_text):
        if w.lower() in proper_noun_words:
            continue
        st = content_stem(w)
        if not st:
            continue
        stems_in_fr.add(st)
        stem_surface_counts.setdefault(st, Counter())[w.lower()] += 1
    global_stem_counts.update(stems_in_fr)
    words_in_tah = {normalize(t) for t in WORD_RE.findall(tah_div.get_text(' '))}
    for w in words_in_tah:
        word_to_french.setdefault(w, []).append(fr_text)

DERIVED_RE = re.compile(r'^(.*?)( \(dérivé de.*)$', re.DOTALL)

reordered_count, contextualized_count = 0, 0
for key in list(result.keys()):
    gloss = result[key]
    m = DERIVED_RE.match(gloss)
    main, suffix = (m.group(1), m.group(2)) if m else (gloss, '')
    parts = [p.strip() for p in main.split(',') if p.strip()]
    if len(parts) <= 1:
        continue
    verses = word_to_french.get(key, [])
    if not verses:
        continue
    n = len(verses)
    local_stem_counts = Counter()
    for fr_text in verses:
        stems_here = {content_stem(w) for w in fr_words(fr_text) if w.lower() not in proper_noun_words}
        stems_here.discard(None)
        local_stem_counts.update(stems_here)

    # atteste = la racine apparait dans au moins 15% des versets contenant
    # le mot (et au moins 2 en absolu) - un seuil proportionnel, pas juste
    # un compte brut : sur un mot tres frequent (des centaines de versets),
    # 2 occurrences suffisent presque toujours par pur hasard (ex.
    # "reciter un conte" ~ "recit" apparait dans 8% des versets de papa'i
    # sans etre sa traduction), donc ca ne doit pas suffire a bloquer
    # ci-dessous la proposition du vrai sens dominant.
    min_hits = max(2, round(n * 0.15))
    attested, rest = [], []
    for p in parts:
        st = part_stem(p)
        if st and local_stem_counts.get(st, 0) >= min_hits:
            attested.append(p)
        else:
            rest.append(p)

    if parts != attested + rest:
        parts = attested + rest
        result[key] = ', '.join(parts) + suffix
        reordered_count += 1

    # Si aucun sens existant n'est atteste, un mot est propose depuis le
    # contexte lui-meme - seuil volontairement strict (majorite des
    # versets, nettement au-dessus de la frequence de base dans tout le
    # livre) car on invente ici une info qui n'est dans aucun dictionnaire,
    # contrairement au reordonnancement ci-dessus qui ne fait que trier
    # des sens deja verifies.
    if attested or n < 5:
        continue
    best_stem, best_score = None, 0
    for st, local_c in local_stem_counts.items():
        if local_c < max(5, round(n * 0.5)):
            continue
        expected = global_stem_counts[st] / total_verses * n
        score = local_c - expected
        if score > best_score:
            best_stem, best_score = st, score
    if best_stem:
        best_word = stem_surface_counts[best_stem].most_common(1)[0][0]
        result[key] = f'{best_word} (depuis le contexte), ' + ', '.join(parts) + suffix
        contextualized_count += 1

print(f'{reordered_count} mots reordonnes selon le contexte francais, {contextualized_count} mots enrichis avec un mot deduit du contexte.')

with open('tah_dict.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

print(f'{len(result)} mots avec glose sur {len(used_keys)} formes uniques dans le texte ({derived_count} via formes flechies).')
print('tah_dict.json:', os.path.getsize('tah_dict.json'), 'octets')
