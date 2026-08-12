"""Construit en_dict.json (glossaire anglais->francais pour le tap-to-translate
des volumes anglais, ex. General Conference) a partir de deux sources :

1. MUSE (Facebook Research), Downloads/muse-en-fr.txt - dictionnaire de
   113k paires anglais-francais, telecharge une fois depuis
   https://dl.fbaipublicfiles.com/arrival/dictionaries/en-fr.txt
   Licence CC BY-NC 4.0 (attribution + usage non commercial - compatible,
   ce site est gratuit et sans monetisation).
2. FUNCTION_WORDS ci-dessous : complement ecrit a la main pour les ~150 mots
   grammaticaux les plus frequents (pronoms, prepositions, auxiliaires,
   formes archaiques thee/thou/thy/ye/unto tres frequentes dans ce texte
   religieux) - MUSE les rate systematiquement (methode d'induction par
   embeddings, mauvaise sur les mots les plus polysemiques/contextuels :
   "be"/"is"/"of"/"to" etc. sont absents de MUSE alors que "was" y est).

Deux sources deja testees et rejetees avant celle-ci (voir memoire projet) :
- FreeDict eng-fra (8500 mots-cles) : 34,6% de couverture, "be"/"is" absents.
- Wiktionary (kaikki.org, dump complet ~3 Go) : seulement 24% de couverture -
  les tables de traduction anglais->francais de Wiktionary sont elles-memes
  tres incompletes (remplies au cas par cas par des benevoles).
MUSE seul : 77,8% de couverture (mots uniques) / 70,3% (occurrences) sur le
vocabulaire du discours d'avril 1971 - net progres, complete ici avec
FUNCTION_WORDS pour combler le trou sur les mots grammaticaux.

Usage : python build_en_dict.py
"""

import glob
import html
import json
import os
import re

MUSE_DICT_PATH = os.path.expanduser('~/Downloads/muse-en-fr.txt')
OUTPUT_PATH = 'en_dict.json'
MAX_GLOSSES = 6

WORD_RE = re.compile(r"[A-Za-z']+")

# Mots grammaticaux les plus frequents, glose(s) la/les plus courante(s)
# d'abord - complement manuel, pas une source automatisee.
FUNCTION_WORDS = {
    'i': ['je'], 'me': ['moi', 'me'], 'my': ['mon', 'ma', 'mes'], 'mine': ['le mien'],
    'we': ['nous'], 'us': ['nous'], 'our': ['notre', 'nos'], 'ours': ['le nôtre'],
    'you': ['tu', 'vous'], 'your': ['ton', 'ta', 'tes', 'votre'], 'yours': ['le tien'],
    'he': ['il'], 'him': ['lui'], 'his': ['son', 'sa', 'ses'],
    'she': ['elle'], 'her': ['elle', 'sa', 'son'], 'hers': ['le sien'],
    'it': ['il', 'elle', 'ça'], 'its': ['son', 'sa', 'ses'],
    'they': ['ils', 'elles'], 'them': ['les', 'leur'], 'their': ['leur', 'leurs'],
    'who': ['qui'], 'whom': ['qui'], 'whose': ['dont'],
    'which': ['quel', 'lequel'], 'what': ['quoi', 'que'],
    'this': ['ce', 'cette'], 'that': ['que', 'ce', 'cela'],
    'these': ['ces'], 'those': ['ces'],
    'thee': ['toi'], 'thou': ['tu'], 'thy': ['ton', 'ta', 'tes'], 'thine': ['le tien'],
    'ye': ['vous'],
    'a': ['un', 'une'], 'an': ['un', 'une'], 'the': ['le', 'la', 'les'],
    'some': ['quelque', 'du'], 'any': ['aucun', "n'importe quel"],
    'no': ['aucun', 'non'], 'all': ['tout', 'tous'],
    'each': ['chaque'], 'every': ['chaque'], 'both': ['les deux'],
    'either': ["l'un ou l'autre"], 'neither': ["ni l'un ni l'autre"],
    'many': ['beaucoup'], 'much': ['beaucoup'], 'few': ['peu'], 'several': ['plusieurs'],
    'of': ['de'], 'to': ['à'], 'in': ['dans'], 'on': ['sur'], 'at': ['à'],
    'by': ['par'], 'for': ['pour'], 'with': ['avec'], 'without': ['sans'],
    'from': ['de', 'depuis'], 'into': ['dans'], 'onto': ['sur'], 'upon': ['sur'],
    'about': ['à propos de'], 'above': ['au-dessus de'], 'below': ['en dessous de'],
    'under': ['sous'], 'over': ['au-dessus de'], 'between': ['entre'], 'among': ['parmi'],
    'through': ['à travers'], 'during': ['pendant'], 'before': ['avant'], 'after': ['après'],
    'since': ['depuis'], 'until': ["jusqu'à"], 'unto': ['vers', 'à'],
    'against': ['contre'], 'toward': ['vers'], 'towards': ['vers'],
    'within': ['dans'], 'beyond': ['au-delà de'], 'near': ['près de'], 'behind': ['derrière'],
    'and': ['et'], 'or': ['ou'], 'but': ['mais'], 'so': ['donc'],
    'because': ['parce que'], 'if': ['si'], 'when': ['quand'], 'while': ['pendant que'],
    'although': ['bien que'], 'unless': ['à moins que'], 'than': ['que'], 'as': ['comme'],
    'be': ['être'], 'am': ['suis'], 'is': ['est'], 'are': ['es', 'êtes', 'sont'],
    'was': ['était'], 'were': ['étaient'], 'been': ['été'], 'being': ['étant'],
    'have': ['avoir'], 'has': ['a'], 'had': ['avait'], 'having': ['ayant'],
    'do': ['faire'], 'does': ['fait'], 'did': ['fit', 'faisait'], 'done': ['fait'],
    'will': ['futur : va'], 'would': ['conditionnel : -rait'], 'shall': ['devra'],
    'should': ['devrait'], 'can': ['peut'], 'could': ['pouvait'],
    'may': ['peut'], 'might': ['pourrait'], 'must': ['doit'], 'ought': ['devrait'],
    'not': ['ne...pas'], 'yes': ['oui'],
    'here': ['ici'], 'there': ['là'], 'where': ['où'], 'why': ['pourquoi'], 'how': ['comment'],
    'then': ['alors', 'puis'], 'now': ['maintenant'],
    'also': ['aussi'], 'too': ['aussi'], 'very': ['très'],
    'more': ['plus'], 'most': ['le plus'], 'less': ['moins'], 'least': ['le moins'],
    'just': ['juste'], 'only': ['seulement'], 'even': ['même'], 'still': ['encore'],
    'again': ['encore'], 'always': ['toujours'], 'never': ['jamais'],
    'sometimes': ['parfois'], 'often': ['souvent'], 'hath': ['a'], 'doth': ['fait'],
}


def extract_book_vocab():
    """Vocabulaire reel de tous les livres anglais deja importes - pas les
    dizaines de milliers de mots des dictionnaires entiers. Aujourd'hui :
    conference-sources/. Un futur dossier source s'ajoutera ici."""
    vocab = set()
    for path in glob.glob('conference-sources/*/index.html'):
        with open(path, encoding='utf-8') as f:
            raw = f.read()
        text = html.unescape(re.sub(r'<[^>]+>', ' ', raw))
        for m in WORD_RE.finditer(text):
            vocab.add(m.group(0).strip("'").lower())
    return vocab


def load_muse_dict():
    if not os.path.isfile(MUSE_DICT_PATH):
        raise SystemExit(
            f"Dictionnaire MUSE introuvable : {MUSE_DICT_PATH}\n"
            "Telecharger depuis https://dl.fbaipublicfiles.com/arrival/dictionaries/en-fr.txt"
        )
    muse = {}
    with open(MUSE_DICT_PATH, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(' ', 1)
            if len(parts) != 2:
                continue
            en, fr = parts
            en = en.lower()
            if fr.lower() == en:
                # ~65% des lignes de MUSE sont des paires identiques
                # (en==fr) - bruit d'induction par embeddings (nombres,
                # entites, artefacts), jamais une vraie traduction utile
                # pour un lecteur qui apprend l'anglais - on les ignore.
                continue
            glosses = muse.setdefault(en, [])
            if fr not in glosses and len(glosses) < MAX_GLOSSES:
                glosses.append(fr)
    return muse


def build_dict(vocab):
    muse = load_muse_dict()
    print(f'MUSE : {len(muse)} mots-cles anglais charges.')

    result = {}
    for word in vocab:
        glosses = []
        # Complement manuel prioritaire pour les mots grammaticaux (MUSE
        # les rate souvent), puis MUSE complete/rallonge la liste.
        for source in (FUNCTION_WORDS.get(word, []), muse.get(word, [])):
            for g in source:
                if g not in glosses and len(glosses) < MAX_GLOSSES:
                    glosses.append(g)
        if glosses:
            # Meme format que tah_dict.json (chaine unique, pas une liste) -
            # le JS de tap-to-translate est partage entre les deux glossaires.
            result[word] = ', '.join(glosses)
    return result


if __name__ == '__main__':
    vocab = extract_book_vocab()
    print(f'Vocabulaire cible (livres anglais importes) : {len(vocab)} mots uniques.')
    en_dict = build_dict(vocab)

    hit = len(en_dict)
    print(f'{hit}/{len(vocab)} mots avec glose ({hit / len(vocab):.1%}).')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(en_dict, f, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    print(f'Ecrit {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH) / 1024:.0f} Ko).')
