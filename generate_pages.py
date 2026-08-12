from bs4 import BeautifulSoup
import json
import os
import re
import shutil

VERSE_REF_RE = re.compile(r'(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?')

SUPERSCRIPT_DIGITS = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def to_superscript(n):
    return str(n).translate(SUPERSCRIPT_DIGITS)


# ---------------------------------------------------------------------------
# Volume 1 source : Livre de Mormon tahitien/francais (livre_de_mormon.html)
# ---------------------------------------------------------------------------

def parse_bom_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'lxml')

    chapters = soup.find_all('h1', id=re.compile(r'chapitre-\d+'))
    book_data = []
    current_book = None
    chapter_list = []

    for chapter in chapters:
        chapter_title = chapter.text.strip()
        book_name = ' '.join(chapter_title.split()[:-2])  # retire "Chapitre X"
        if book_name != current_book:
            if current_book is not None:
                book_data.append({'book_title': current_book, 'chapters': chapter_list})
            current_book = book_name
            chapter_list = []

        verses = []
        introduction = None
        next_element = chapter.find_next()
        while next_element and (next_element.name != 'h1' or not next_element.get('id', '').startswith('chapitre-')):
            if next_element.name == 'div' and 'verse-container' in next_element.get('class', []):
                tahitien = next_element.find('div', class_='tahitien')
                francais = next_element.find('div', class_='francais')
                verse_text = {
                    'tahitien': tahitien.text.strip() if tahitien else '',
                    'francais': francais.text.strip() if francais else ''
                }
                if 'introduction' in next_element.get('class', []):
                    introduction = verse_text
                else:
                    verses.append(verse_text)
            next_element = next_element.find_next()

        chapter_list.append({
            'title': chapter_title,
            'verses': verses,
            'introduction': introduction
        })

    if current_book and chapter_list:
        book_data.append({'book_title': current_book, 'chapters': chapter_list})

    return book_data


def split_verse_number(francais_text):
    """Renvoie (numero_de_verset, texte_sans_le_numero) ou (None, texte) si pas de numero en tete."""
    m = re.match(r'^(\d+)\s+(.*)$', francais_text, re.DOTALL)
    if m:
        return int(m.group(1)), m.group(2)
    return None, francais_text


# ---------------------------------------------------------------------------
# Volume 6 source : Livre de Mormon anglais (book-of-mormon-en/index.html,
# export Calibre). Structure differente de livre_de_mormon.html (source deja
# structuree en 'verse-container') : ici chaque verset est un <p class="verse">
# contenant un <span class="verse-number"> puis le texte, avec des
# <a class="scripture-ref"> intercales pour les notes de bas de page - leur
# texte colle la lettre de la note directement au mot qui suit (ex.
# <a><sup class="marker">a</sup>born</a> -> get_text() = "aborn"), donc on ne
# peut pas decomposer l'ancre entiere sans perdre le mot : seul le
# <sup class="marker"> interne est retire, le reste (le vrai mot) est garde
# en place via unwrap(). Chapitres = <div class="calibre2"> contenant des
# p.verse ; le titre du livre (h1, present seulement au 1er chapitre de
# chaque livre) est reporte sur les chapitres suivants via un etat courant.
# Aucune image (pas de <img> dans les chapitres de toute facon, verifie).
# ---------------------------------------------------------------------------

def clean_bom_en_verse_text(p_verse):
    vn = p_verse.find('span', class_='verse-number')
    if vn:
        vn.decompose()
    for ref in p_verse.find_all('a', class_='scripture-ref'):
        sup = ref.find('sup', class_='marker')
        if sup:
            sup.decompose()
        ref.unwrap()
    return p_verse.get_text(' ', strip=True)


def parse_bom_en_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'lxml')

    # Meme ordre canonique que BOOK_NAME_MAP (verifie : les 15 livres de la
    # source anglaise apparaissent dans cet ordre exact) - sert a donner a
    # chaque chapitre un titre court style "1 Nephi 1" plutot que le nom
    # complet de la source ("The First Book of Nephi").
    short_names = list(BOOK_NAME_MAP.values())

    books = []
    current_book_full = None

    for container in soup.find_all('div', class_='calibre2'):
        header = container.find('header', recursive=False)
        h1 = header.find('h1', recursive=False) if header else None
        if h1:
            current_book_full = h1.get_text(' ', strip=True)

        verses_p = container.find_all('p', class_='verse')
        if not verses_p:
            continue

        if not books or books[-1]['book_title_full'] != current_book_full:
            book_idx = len(books)
            short_name = short_names[book_idx] if book_idx < len(short_names) else current_book_full
            books.append({'book_title_full': current_book_full, 'book_title': short_name, 'chapters': []})

        chap_num = len(books[-1]['chapters']) + 1
        short_name = books[-1]['book_title']

        verses = []
        for vp in verses_p:
            vn = vp.find('span', class_='verse-number')
            num_txt = vn.get_text(strip=True) if vn else ''
            try:
                num = int(num_txt)
            except ValueError:
                num = None
            verses.append((num, clean_bom_en_verse_text(vp)))

        books[-1]['chapters'].append({'title': f'{short_name} {chap_num}', 'verses': verses})

    return books


# ---------------------------------------------------------------------------
# Glossaire tahitien au tap (tah_dict.json, extrait une fois pour toutes du
# dictionnaire REO via build_tah_dict.py - pas une dependance de generation,
# juste un fichier de donnees commite comme livre_de_mormon.html)
# ---------------------------------------------------------------------------

TAH_MACRON_MAP = str.maketrans('āēīōūĀĒĪŌŪ', 'aeiouAEIOU')
TAH_OKINA_RE = re.compile(r"[‘’ʻ\x27]")
TAH_WORD_RE = re.compile(r"[A-Za-zĀĒĪŌŪāēīōū][A-Za-zĀĒĪŌŪāēīōū‘’ʻ\x27]*")

try:
    with open('tah_dict.json', 'r', encoding='utf-8') as f:
        tah_dict = json.load(f)
except FileNotFoundError:
    tah_dict = {}


def tah_normalize(word):
    word = word.translate(TAH_MACRON_MAP)
    word = TAH_OKINA_RE.sub('', word)
    return word.lower()


MAX_PHRASE_WORDS = 5


def wrap_tah_words(text):
    """Entoure chaque mot (ou groupe de 2 a 5 mots adjacents formant un verbe
    compose connu, ex. "haere mai" = venir, une seule bulle pour le groupe
    entier) ayant une glose dans tah_dict d'un <span class="tah-word"> pour
    le tap-to-translate - laisse tel quel tout mot absent du glossaire (nom
    propre, forme flechie...) ou tah_dict vide. Essaie toujours le plus long
    groupe d'abord (match exact requis contre tah_dict a chaque longueur -
    c'est ce qui evite les faux positifs, pas une liste de POS autorises)."""
    if not tah_dict:
        return text

    matches = list(TAH_WORD_RE.finditer(text))
    if not matches:
        return text

    out = []
    last_end = 0
    i = 0
    while i < len(matches):
        matched_phrase = False
        max_len = min(MAX_PHRASE_WORDS, len(matches) - i)
        for span in range(max_len, 1, -1):
            group = matches[i:i + span]
            if any(text[group[j].end():group[j + 1].start()] != ' ' for j in range(len(group) - 1)):
                continue
            phrase_key = ' '.join(tah_normalize(g.group(0)) for g in group)
            if phrase_key in tah_dict:
                out.append(text[last_end:group[0].start()])
                out.append(f'<span class="tah-word" data-w="{phrase_key}">{text[group[0].start():group[-1].end()]}</span>')
                last_end = group[-1].end()
                i += span
                matched_phrase = True
                break
        if matched_phrase:
            continue
        m = matches[i]
        key = tah_normalize(m.group(0))
        if key in tah_dict:
            out.append(text[last_end:m.start()])
            out.append(f'<span class="tah-word" data-w="{key}">{m.group(0)}</span>')
            last_end = m.end()
        i += 1
    out.append(text[last_end:])
    return ''.join(out)


# ---------------------------------------------------------------------------
# Volume 3 source : Book of Mormon Study Guide (commentaire par verset)
# ---------------------------------------------------------------------------

# Le guide nomme ses livres en anglais complet, le Livre de Mormon en
# abreviations francaises - et le guide n'a PAS de section pour "Words of
# Mormon" (aucun commentaire ecrit pour ce livre d'un seul chapitre). On fait
# donc correspondre les deux sources par nom, jamais par position.
BOOK_NAME_MAP = {
    '1 Ne': '1 Nephi', '2 Ne': '2 Nephi', 'Jacob': 'Jacob', 'Enos': 'Enos',
    'Jarom': 'Jarom', 'Omni': 'Omni', 'W Of M': 'Words of Mormon',
    'Mosiah': 'Mosiah', 'Alma': 'Alma', 'Hel': 'Helaman', '3 Ne': '3 Nephi',
    '4 Ne': '4 Nephi', 'Morm': 'Mormon', 'Ether': 'Ether', 'Moro': 'Moroni',
}


def parse_guide_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        # html.parser (pas lxml) : sur ce fichier, lxml imbrique a tort chaque
        # <section> dans la precedente (probablement une balise mal fermee
        # ailleurs dans le document), ce qui fait qu'une page de chapitre
        # engloberait tout ce qui suit. html.parser garde les sections
        # correctement independantes.
        soup = BeautifulSoup(file, 'html.parser')

    sections = soup.find_all('section', id=True)
    intro_items = []
    books_by_name = {}  # nom complet -> {chapter_num: {'title':..., 'section':...}}

    for sec in sections:
        h2 = sec.find('h2')
        if not h2:
            continue
        title = h2.get_text(strip=True)
        tokens = title.split()

        if not tokens or not tokens[-1].isdigit():
            intro_items.append({'title': title, 'section': sec})
            continue

        chapter_num = int(tokens[-1])
        book_name = ' '.join(tokens[:-1])
        books_by_name.setdefault(book_name, {})[chapter_num] = {'title': title, 'section': sec}

    # Pose une ancre id="vN" sur chaque <h4> de reference verset, regroupe ce
    # <h4> et tout ce qui le suit (jusqu'au <h4> suivant) dans un
    # <div class="guide-entry" id="vN"> - pour pouvoir isoler une seule
    # entree a l'affichage au lieu de montrer tout le chapitre en dessous -
    # et indexe (nom_de_livre, chapitre, verset) -> ancre.
    verse_index_by_name = {}
    for book_name, chapters in books_by_name.items():
        for chap_num, chapter in chapters.items():
            seen = {}
            for h4 in chapter['section'].find_all('h4'):
                text = h4.get_text(' ', strip=True)
                m = VERSE_REF_RE.search(text)
                if not m:
                    continue
                h4_chap, h4_verse = int(m.group(1)), int(m.group(2))
                h4_verse_end = int(m.group(3)) if m.group(3) else h4_verse
                seen[(h4_chap, h4_verse)] = seen.get((h4_chap, h4_verse), 0) + 1
                n = seen[(h4_chap, h4_verse)]
                anchor_id = f'v{h4_verse}' if n == 1 else f'v{h4_verse}-{n}'

                wrapper = soup.new_tag('div')
                wrapper['class'] = 'guide-entry'
                wrapper['id'] = anchor_id
                # Plage de versets couverte par cette entree (souvent un seul
                # verset, parfois une plage genre "2:8-13") - utilisee plus
                # tard pour prefixer le texte du/des verset(s) francais avant
                # le commentaire lors du Copier/Partager.
                wrapper['data-verse-start'] = str(h4_verse)
                wrapper['data-verse-end'] = str(h4_verse_end)
                h4.insert_before(wrapper)
                node = h4
                while node is not None and not (node is not h4 and getattr(node, 'name', None) == 'h4'):
                    nxt = node.next_sibling
                    wrapper.append(node.extract())
                    node = nxt

                key = (book_name, h4_chap, h4_verse)
                if key not in verse_index_by_name:
                    verse_index_by_name[key] = anchor_id

    return intro_items, books_by_name, verse_index_by_name


def guide_section_content_html(section_tag):
    """HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'."""
    h2 = section_tag.find('h2')
    if h2:
        h2.decompose()
    back_to_top = section_tag.find('a', class_='back-to-top')
    if back_to_top:
        back_to_top.decompose()
    apply_en_translate(section_tag)
    return section_tag.decode_contents()


# ---------------------------------------------------------------------------
# Volume 5 source : General Conference talks (conference-sources/<dossier>/index.html,
# un dossier par numero - export Calibre depuis churchofjesuschrist.org). Pas
# d'images (jamais copiees, <img> retirees a l'extraction).
# ---------------------------------------------------------------------------

CONFERENCE_TALK_TITLE_RE = re.compile(r'^(.*)\s\(([^()]+)\)$')

EN_WORD_RE = re.compile(r"[A-Za-z']+")

try:
    with open('en_dict.json', 'r', encoding='utf-8') as f:
        en_dict = json.load(f)
except FileNotFoundError:
    en_dict = {}


def wrap_en_words(text):
    """Equivalent anglais de wrap_tah_words() - pas de detection de groupes
    de mots ici (pas necessaire pour l'anglais, contrairement aux verbes
    composes tahitiens), juste un lookup mot a mot dans en_dict."""
    if not en_dict:
        return text
    matches = list(EN_WORD_RE.finditer(text))
    if not matches:
        return text
    out = []
    last_end = 0
    for m in matches:
        key = m.group(0).strip("'").lower()
        if key in en_dict:
            out.append(text[last_end:m.start()])
            out.append(f'<span class="en-word" data-w="{key}">{m.group(0)}</span>')
            last_end = m.end()
    out.append(text[last_end:])
    return ''.join(out)


def apply_en_translate(tag):
    """Enveloppe chaque mot connu de en_dict dans un <span> tappable, en ne
    touchant que les noeuds de texte du HTML deja parse - jamais les balises
    ni les attributs, pour ne pas casser les liens <a href> ou les italiques
    <em> deja presents dans le corps du discours source."""
    if not en_dict:
        return
    for node in list(tag.find_all(string=True)):
        if node.parent.name in ('script', 'style'):
            continue
        wrapped = wrap_en_words(str(node))
        if wrapped == str(node):
            continue
        frag = BeautifulSoup(wrapped, 'html.parser')
        node.replace_with(frag)


def parse_conference_issue(path):
    """Un <section id=...> de premier niveau sans div.body-block est un
    separateur de session (ex. "Saturday Morning Session") - pas un
    discours, juste une metadonnee gardee pour les discours suivants.

    Certains discours a tiroirs (ex. 1977 : "The Foundations of
    Righteousness" continue en sous-<section> imbriquees DANS son propre
    div.body-block - 2.1 "Home Evening", 2.2 "Patriarchal Blessings"...,
    chacune son <h2> mais sans son propre div.body-block) - detectees et
    aplaties (h2 remplace par un marqueur <h3 class="conf-subhead">) avant
    de figer le contenu du discours parent en un seul decode_contents(),
    plutot que traitees comme des discours separes. Uniquement
    soup.find_all('section', id=True) DIRECTEMENT sur soup (jamais sur un
    body-block deja trouve) donnerait ces sous-sections en double - elles
    ne sont jamais iterees comme entrees de premier niveau."""
    with open(path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    titlepage_h1 = soup.find('h1', class_='title')
    issue_title = titlepage_h1.get_text(strip=True) if titlepage_h1 else os.path.basename(os.path.dirname(path))

    all_sections = soup.find_all('section', id=True)
    top_sections = [s for s in all_sections if s.find_parent('section', id=True) is None]

    talks = []
    current_session = None
    for sec in top_sections:
        h1 = sec.find('h1')
        if not h1:
            continue
        title_raw = h1.get_text(' ', strip=True)
        body_block = sec.find('div', class_='body-block')
        if body_block is None:
            current_session = title_raw
            continue
        m = CONFERENCE_TALK_TITLE_RE.match(title_raw)
        talk_title, speaker = (m.group(1).strip(), m.group(2).strip()) if m else (title_raw, None)

        for sub in body_block.find_all('section', id=True):
            sub_heading = sub.find(['h1', 'h2'])
            sub_title = sub_heading.get_text(' ', strip=True) if sub_heading else None
            if sub_heading:
                sub_heading.decompose()
            if sub_title:
                marker = soup.new_tag('h3')
                marker['class'] = 'conf-subhead'
                marker.string = sub_title
                sub.insert_before(marker)

        for img in body_block.find_all('img'):
            img.decompose()
        apply_en_translate(body_block)
        talks.append({
            'title': talk_title,
            'speaker': speaker,
            'session': current_session,
            'content_html': body_block.decode_contents(),
        })
    return issue_title, talks


def load_conference_issues(sources_dir='conference-sources'):
    """Forme attendue par render_volume_block : un 'livre' par numero de
    conference, ses discours comme 'chapitres'. Un futur numero n'a qu'a
    etre depose dans un nouveau sous-dossier - aucun code a modifier."""
    issues = []
    if not os.path.isdir(sources_dir):
        return issues
    for folder in sorted(os.listdir(sources_dir)):
        issue_path = os.path.join(sources_dir, folder, 'index.html')
        if not os.path.isfile(issue_path):
            continue
        issue_title, talks = parse_conference_issue(issue_path)
        issues.append({
            'book_title': issue_title,
            'folder': folder,
            'chapters': [dict(t, chapter_num=n) for n, t in enumerate(talks, 1)],
        })
    return issues


# ---------------------------------------------------------------------------
# Rendu HTML generique (accordeon volume > livre > grille de chapitres)
# ---------------------------------------------------------------------------

def render_volume_block(title, books, chapter_href):
    """books: liste de {'book_title', 'chapters': [...]} ; chapter_href(book_idx, chap_idx, chapter) -> url"""
    html = f'''
        <div class="volume">
            <button class="volume-toggle" type="button" aria-expanded="false">
                <span class="chevron" aria-hidden="true"></span>
                {title}
            </button>
            <div class="volume-content">
                <div class="accordion">
'''
    for book_idx, book in enumerate(books, 1):
        html += f'''
                    <div class="accordion-item">
                        <button class="accordion-button" type="button" aria-expanded="false">
                            <span class="chevron" aria-hidden="true"></span>
                            {book["book_title"]}
                        </button>
                        <div class="accordion-content">
                            <div class="chapter-grid">
'''
        for chap_idx, chapter in enumerate(book['chapters'], 1):
            chap_num = chapter.get('chapter_num', chap_idx)
            href = chapter_href(book_idx, chap_num, chapter)
            html += f'<a class="chapter-link" href="{href}" title="{chapter["title"]}">{chap_num}</a>'
        html += '''
                            </div>
                        </div>
                    </div>
'''
    html += '''
                </div>
            </div>
        </div>
'''
    return html


PAGE_HEAD = '''
<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="color-scheme" content="light dark">
    <title>{title}</title>
    <link rel="stylesheet" href="{styles_href}">
    <script src="{script_href}"></script>
</head>
<body>
    <div class="page">
        <div class="page-controls">
            {extra_controls}
            <button class="theme-toggle" type="button" aria-label="Changer de theme"></button>
        </div>
'''

PAGE_TAIL = '''
    </div>
</body>
</html>
'''

TEXT_SIZE_CONTROL = '''
            <div class="text-size-control">
                <button class="text-size-toggle" type="button" aria-label="Taille du texte" title="Taille du texte">A</button>
                <div class="text-size-popover" id="text-size-popover" hidden>
                    <button type="button" class="text-size-step" data-dir="-1" aria-label="Reduire la taille du texte" title="Reduire">
                        <span class="ts-glyph ts-small">A</span>
                    </button>
                    <button type="button" class="text-size-step" data-dir="1" aria-label="Agrandir la taille du texte" title="Agrandir">
                        <span class="ts-glyph ts-large">A</span>
                    </button>
                </div>
            </div>
'''

CHAPTER_NAV = '''
    <nav>
        {prev_link}
        {next_link}
        <a href="{index_href}">Retour a la table des matieres</a>
    </nav>
'''


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

bom_book_data = parse_bom_source('livre_de_mormon.html')
bom_en_book_data = parse_bom_en_source('book-of-mormon-en/index.html')
guide_intro_items, guide_books_by_name, guide_verse_index_by_name = parse_guide_source(
    'The_Book_of_Mormon_Study_Guide/The_Book_of_Mormon_Study_Guide.html'
)
conference_issues = load_conference_issues()

# (book_idx, chapter_num, verse_num) -> texte francais sans le numero de
# verset en tete - utilise pour prefixer le(s) verset(s) au Copier/Partager
# d'une entree du guide.
french_verse_text = {}
for book_idx, book in enumerate(bom_book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        for verse in chapter['verses']:
            verse_num, verse_text = split_verse_number(verse['francais'])
            if verse_num is not None:
                french_verse_text[(book_idx, chap_idx, verse_num)] = verse_text

# Associe chaque livre bilingue (par nom, via BOOK_NAME_MAP) a ses chapitres
# du guide, sous le meme book_idx que le Livre de Mormon (1..15). Un livre
# absent du guide (Words of Mormon) donne simplement une liste vide - pas
# d'erreur, juste aucun signet/aucune page pour ce livre-la.
guide_name_to_bom_idx = {
    BOOK_NAME_MAP.get(bom_book['book_title']): book_idx
    for book_idx, bom_book in enumerate(bom_book_data, 1)
}

guide_chapters_by_bom_idx = {}   # book_idx -> {chapter_num: {'title','section'}}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide_chapters = guide_books_by_name.get(guide_name, {})
    guide_chapters_by_bom_idx[book_idx] = guide_chapters
    if not guide_chapters:
        print(f"INFO: pas de contenu guide pour {bom_book['book_title']!r} ({guide_name!r}) - normal si absent du guide source.")
    elif set(guide_chapters.keys()) != set(range(1, len(bom_book['chapters']) + 1)):
        print(f"ATTENTION: {bom_book['book_title']!r} a {len(bom_book['chapters'])} chapitres cote Livre de Mormon "
              f"mais le guide a les chapitres {sorted(guide_chapters.keys())}.")

guide_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide_verse_index[(book_idx, chap_num, verse_num)] = anchor

# Repart de zero a chaque generation : les numeros de chapitre du guide ont
# des trous (livres/chapitres absents de la source), donc une ancienne
# execution peut laisser des fichiers a un chemin qui n'est plus le bon.
for d in ('chapters', 'chapters-fr', 'chapters-tah', 'chapters-en', 'guide', 'conference'):
    shutil.rmtree(d, ignore_errors=True)
os.makedirs('chapters', exist_ok=True)
os.makedirs('chapters-fr', exist_ok=True)
os.makedirs('chapters-tah', exist_ok=True)
os.makedirs('chapters-en', exist_ok=True)
os.makedirs('guide/chapters', exist_ok=True)
os.makedirs('conference', exist_ok=True)

# --- index.html : bibliotheque a 3 volumes ---------------------------------

toc_html = PAGE_HEAD.format(title='Bibliotheque - Table des matieres', styles_href='styles.css', script_href='script.js', lang='fr', extra_controls='')
toc_html += '        <h1>Bibliotheque</h1>\n'
toc_html += '        <div id="continue-reading-slot"></div>\n'

toc_html += render_volume_block(
    'Livre de Mormon (tahitien / francais)',
    bom_book_data,
    lambda bi, ci, ch: f'chapters/chapter_{bi}_{ci}.html'
)

toc_html += render_volume_block(
    'Livre de Mormon (francais)',
    bom_book_data,
    lambda bi, ci, ch: f'chapters-fr/chapter_{bi}_{ci}.html'
)

toc_html += render_volume_block(
    'Livre de Mormon (tahitien)',
    bom_book_data,
    lambda bi, ci, ch: f'chapters-tah/chapter_{bi}_{ci}.html'
)

toc_html += render_volume_block(
    'Livre de Mormon (anglais)',
    bom_en_book_data,
    lambda bi, ci, ch: f'chapters-en/chapter_{bi}_{ci}.html'
)

guide_all_books = []
if guide_intro_items:
    guide_all_books.append({
        'book_title': 'Introductory Pages',
        'book_idx': None,
        'chapters': [{'title': item['title'], 'chapter_num': n} for n, item in enumerate(guide_intro_items, 1)]
    })
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_chapters = guide_chapters_by_bom_idx[book_idx]
    if not guide_chapters:
        continue  # ex: Words of Mormon, pas de contenu guide
    guide_all_books.append({
        'book_title': bom_book['book_title'],
        'book_idx': book_idx,
        'chapters': [dict(guide_chapters[n], chapter_num=n) for n in sorted(guide_chapters.keys())]
    })

def guide_href(bi, ci, ch):
    if guide_intro_items and bi == 1:
        return f'guide/chapters/intro_{ci}.html'
    real_book = guide_all_books[bi - 1]
    return f'guide/chapters/chapter_{real_book["book_idx"]}_{ci}.html'

toc_html += render_volume_block('Book of Mormon Study Guide', guide_all_books, guide_href)

def conference_href(bi, ci, ch):
    return f'conference/{conference_issues[bi - 1]["folder"]}/talk_{ci}.html'

if conference_issues:
    toc_html += render_volume_block('General Conference', conference_issues, conference_href)

toc_html += PAGE_TAIL
write('index.html', toc_html)

# --- Volume 1 : chapitres tahitien/francais (inchange) ----------------------

for book_idx, book in enumerate(bom_book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        verses_html = ''
        for verse in chapter['verses']:
            verse_num, _ = split_verse_number(verse['francais'])
            id_attr = f' id="v{verse_num}"' if verse_num is not None else ''
            verses_html += f'<div class="verse-container"{id_attr}>'
            verses_html += f'<div class="tahitien">{verse["tahitien"]}</div>'
            verses_html += f'<div class="francais">{verse["francais"]}</div>'
            verses_html += '</div>'

        introduction_html = ''
        if chapter['introduction']:
            introduction_html = '<div class="verse-container introduction">'
            introduction_html += f'<div class="tahitien">{chapter["introduction"]["tahitien"]}</div>'
            introduction_html += f'<div class="francais">{chapter["introduction"]["francais"]}</div>'
            introduction_html += '</div>'

        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="verses-bi" data-volume-key="bilingual" data-volume-title="Livre de Mormon (tahitien / français)">'
        html += verses_html + introduction_html
        html += '</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../index.html')
        html += PAGE_TAIL

        write(f'chapters/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 2 : Livre de Mormon francais seul, avec signets vers le guide ---

for book_idx, book in enumerate(bom_book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        verses_html = ''
        for verse in chapter['verses']:
            verse_num, verse_text = split_verse_number(verse['francais'])
            if verse_num is None:
                verses_html += f'<p class="verse-fr">{verse_text}</p>'
                continue
            anchor = guide_verse_index.get((book_idx, chap_idx, verse_num))
            verses_html += f'<p class="verse-fr" id="v{verse_num}">'
            verses_html += f'<sup>{verse_num}</sup>{verse_text}'
            if anchor:
                guide_link = f'../guide/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor}'
                verses_html += (f' <a class="bookmark" href="{guide_link}" '
                                 f'title="Voir le commentaire du guide d\'etude" aria-label="Voir le commentaire">'
                                 f'\U0001F516</a>')
            verses_html += '</p>'

        introduction_html = ''
        if chapter['introduction']:
            introduction_html = f'<p class="verse-fr introduction">{chapter["introduction"]["francais"]}</p>'

        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="verses-fr" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}" data-volume-key="french" data-volume-title="Livre de Mormon (français)">'
        html += verses_html + introduction_html
        html += '</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../index.html')
        html += PAGE_TAIL

        write(f'chapters-fr/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 3 : Livre de Mormon tahitien seul --------------------------------

for book_idx, book in enumerate(bom_book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        verses_html = ''
        for verse in chapter['verses']:
            verse_num, verse_text = split_verse_number(verse['tahitien'])
            verse_text = wrap_tah_words(verse_text)
            if verse_num is None:
                verses_html += f'<p class="verse-fr">{verse_text}</p>'
                continue
            verses_html += f'<p class="verse-fr" id="v{verse_num}"><sup>{verse_num}</sup>{verse_text}</p>'

        introduction_html = ''
        if chapter['introduction']:
            intro_text = wrap_tah_words(chapter["introduction"]["tahitien"])
            introduction_html = f'<p class="verse-fr introduction">{intro_text}</p>'

        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='ty', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="verses-tah" data-volume-key="tahitian" data-volume-title="Livre de Mormon (tahitien)">'
        html += verses_html + introduction_html
        html += '</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../index.html')
        html += PAGE_TAIL

        write(f'chapters-tah/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 6 : Livre de Mormon anglais seul, tap-to-translate vers en_dict --

for book_idx, book in enumerate(bom_en_book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        verses_html = ''
        for verse_num, verse_text in chapter['verses']:
            verse_text = wrap_en_words(verse_text)
            id_attr = f' id="v{verse_num}"' if verse_num is not None else ''
            sup = f'<sup>{verse_num}</sup>' if verse_num is not None else ''
            verses_html += f'<p class="verse-fr"{id_attr}>{sup}{verse_text}</p>'

        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="verses-fr" data-volume-key="english" data-volume-title="Livre de Mormon (anglais)">'
        html += verses_html
        html += '</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../index.html')
        html += PAGE_TAIL

        write(f'chapters-en/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 4 : Book of Mormon Study Guide ----------------------------------

for n, item in enumerate(guide_intro_items, 1):
    content_html = guide_section_content_html(item['section'])
    prev_link = f'<a href="intro_{n-1}.html">Page precedente</a> | ' if n > 1 else ''
    next_link = f'<a href="intro_{n+1}.html">Page suivante</a> | ' if n < len(guide_intro_items) else ''

    html = PAGE_HEAD.format(title=item['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
    html += f'    <h1>Introductory Pages</h1>\n    <h2>{item["title"]}</h2>\n'
    html += f'<div class="guide-content" data-volume-key="guide" data-volume-title="Book of Mormon Study Guide">{content_html}</div>'
    html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
    html += PAGE_TAIL

    write(f'guide/chapters/intro_{n}.html', html)

for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_chapters = guide_chapters_by_bom_idx[book_idx]
    chapter_nums = sorted(guide_chapters.keys())
    for chap_idx in chapter_nums:
        chapter = guide_chapters[chap_idx]

        for entry in chapter['section'].find_all('div', class_='guide-entry'):
            vstart = entry.get('data-verse-start')
            vend = entry.get('data-verse-end')
            if vstart is None:
                continue
            vstart, vend = int(vstart), int(vend)
            pieces = []
            for v in range(vstart, vend + 1):
                verse_text = french_verse_text.get((book_idx, chap_idx, v))
                if verse_text:
                    pieces.append(f'{to_superscript(v)}{verse_text}')
                else:
                    print(f"ATTENTION: verset francais introuvable pour {bom_book['book_title']} {chap_idx}:{v} "
                          f"(entree guide {vstart}-{vend}) - Copier/Partager n'inclura pas ce verset.")
            if pieces:
                ref = f'{chap_idx}:{vstart}' if vstart == vend else f'{chap_idx}:{vstart}-{vend}'
                entry['data-verse-ref'] = f'{bom_book["book_title"]} {ref}'
                entry['data-verse-text'] = ' '.join(pieces)

        content_html = guide_section_content_html(chapter['section'])
        has_prev = chapter_nums.index(chap_idx) > 0
        has_next = chapter_nums.index(chap_idx) < len(chapter_nums) - 1
        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if has_prev else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if has_next else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{bom_book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="guide-content" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}" data-volume-key="guide" data-volume-title="Book of Mormon Study Guide">{content_html}</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
        html += PAGE_TAIL

        write(f'guide/chapters/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 5 : General Conference -------------------------------------------

for issue in conference_issues:
    folder = issue['folder']
    talks = issue['chapters']
    for idx, talk in enumerate(talks, 1):
        prev_link = f'<a href="talk_{idx-1}.html">Discours precedent</a> | ' if idx > 1 else ''
        next_link = f'<a href="talk_{idx+1}.html">Discours suivant</a> | ' if idx < len(talks) else ''

        html = PAGE_HEAD.format(title=talk['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{issue["book_title"]}</h1>\n'
        if talk['session']:
            html += f'    <p class="conf-session">{talk["session"]}</p>\n'
        html += f'    <h2>{talk["title"]}</h2>\n'
        if talk['speaker']:
            html += f'    <p class="conf-speaker">{talk["speaker"]}</p>\n'
        html += (f'<div class="guide-content" data-volume-key="conference-{folder}" '
                  f'data-volume-title="{issue["book_title"]}">{talk["content_html"]}</div>')
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
        html += PAGE_TAIL

        write(f'conference/{folder}/talk_{idx}.html', html)

conference_talk_count = sum(len(issue['chapters']) for issue in conference_issues)
print(f'{len(conference_issues)} numeros de conference, {conference_talk_count} discours.')

guide_chapter_count = sum(len(c) for c in guide_chapters_by_bom_idx.values())
print(f'{sum(len(b["chapters"]) for b in bom_book_data)} chapitres LoM, '
      f'{guide_chapter_count} chapitres guide, '
      f'{len(guide_intro_items)} pages intro, '
      f'{len(guide_verse_index)} versets avec signet.')

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

css_content = '''
:root {
    color-scheme: light dark;
    --bg: #f5f6f8;
    --surface: #ffffff;
    --border: #e2e5ea;
    --text: #1c1e21;
    --text-muted: #5b6270;
    --text-faint: #8a8f99;
    --accent: #1b4d89;
    --accent-hover: #163d6d;
    --hover-bg: #eef1f5;
    --intro-bg: #f9f9f9;
    --reading-font-size: 16px;
}

:root[data-text-size="xsmall"] {
    --reading-font-size: 12px;
}

:root[data-text-size="small"] {
    --reading-font-size: 14px;
}

:root[data-text-size="large"] {
    --reading-font-size: 19px;
}

:root[data-text-size="xlarge"] {
    --reading-font-size: 22px;
}

:root[data-text-size="xxlarge"] {
    --reading-font-size: 25px;
}

@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
        --bg: #15171c;
        --surface: #1c1f26;
        --border: #2c313a;
        --text: #e8e9ec;
        --text-muted: #9aa1ac;
        --text-faint: #7a8190;
        --accent: #5b9bdb;
        --accent-hover: #7fb3e8;
        --hover-bg: #242832;
        --intro-bg: #20242c;
    }
}

:root[data-theme="light"] {
    color-scheme: light;
}

:root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #15171c;
    --surface: #1c1f26;
    --border: #2c313a;
    --text: #e8e9ec;
    --text-muted: #9aa1ac;
    --text-faint: #7a8190;
    --accent: #5b9bdb;
    --accent-hover: #7fb3e8;
    --hover-bg: #242832;
    --intro-bg: #20242c;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
}

h1, h2 {
    color: var(--text);
}

.page {
    max-width: 720px;
    margin: 0 auto;
    padding: 32px 20px 80px;
    position: relative;
}

h1 {
    margin: 0 0 16px;
    padding-right: 100px;
    font-size: 22px;
}

.page-controls {
    position: absolute;
    top: 32px;
    right: 20px;
    display: flex;
    gap: 8px;
}

.theme-toggle,
.text-size-toggle {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
}

.theme-toggle:hover,
.text-size-toggle:hover {
    background: var(--hover-bg);
}

.text-size-control {
    position: relative;
}

.text-size-popover {
    position: absolute;
    right: 0;
    top: calc(100% + 8px);
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 6px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    z-index: 2000;
}

.text-size-popover[hidden] {
    display: none;
}

.text-size-step {
    width: 44px;
    height: 44px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    border-radius: 8px;
    color: var(--text);
    cursor: pointer;
}

.text-size-step:hover:not(:disabled) {
    background: var(--hover-bg);
}

.text-size-step:disabled {
    opacity: 0.3;
    cursor: default;
}

.ts-glyph {
    font-weight: 600;
    line-height: 1;
}

.ts-small {
    font-size: 12px;
}

.ts-large {
    font-size: 22px;
}

.continue-reading {
    display: block;
    margin: 0 0 20px;
    padding: 14px 16px;
    background: var(--accent);
    color: #ffffff;
    text-decoration: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 500;
}

.continue-reading:hover {
    background: var(--accent-hover);
}

.volume {
    margin-bottom: 14px;
}

.volume-toggle,
.accordion-button {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    background: var(--surface);
    color: var(--text);
    cursor: pointer;
    text-align: left;
    font: inherit;
    border: 1px solid var(--border);
    border-radius: 8px;
    outline: none;
}

.volume-toggle {
    padding: 14px 16px;
    font-size: 19px;
    font-weight: 600;
}

.accordion-button {
    padding: 12px 16px;
    font-size: 15px;
}

.volume-toggle:hover,
.accordion-button:hover {
    background: var(--hover-bg);
}

.chevron {
    flex-shrink: 0;
    display: inline-block;
    width: 9px;
    height: 9px;
    border-right: 2px solid var(--text-muted);
    border-bottom: 2px solid var(--text-muted);
    transform: rotate(-45deg);
    transition: transform 0.15s ease;
}

.volume-toggle[aria-expanded="true"] .chevron,
.accordion-button[aria-expanded="true"] .chevron {
    transform: rotate(45deg);
}

.volume-content {
    display: none;
    margin-top: 10px;
}

.volume-content.show {
    display: block;
}

.accordion {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.accordion-content {
    display: none;
    margin-top: -4px;
    padding: 14px 16px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 8px 8px;
}

.accordion-content.show {
    display: block;
}

.chapter-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(44px, 1fr));
    gap: 8px;
}

.chapter-link {
    display: flex;
    align-items: center;
    justify-content: center;
    aspect-ratio: 1;
    border-radius: 6px;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--accent);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
}

.chapter-link:hover,
.chapter-link:focus-visible {
    background: var(--accent);
    color: #ffffff;
    border-color: var(--accent);
}

.verse-container {
    display: flex;
    gap: 16px;
    justify-content: space-between;
    margin-bottom: 10px;
}

.verse-container.introduction {
    background-color: var(--intro-bg);
    font-style: italic;
}

.tahitien, .francais {
    width: 48%;
    font-size: var(--reading-font-size);
}

.verse-fr {
    margin: 0 0 16px;
    line-height: 1.65;
    font-size: var(--reading-font-size);
}

.verse-fr.introduction {
    background-color: var(--intro-bg);
    font-style: italic;
    padding: 10px;
    border-radius: 6px;
}

.verse-fr sup {
    color: var(--text-faint);
    font-weight: 600;
    font-size: 0.65em;
    margin-right: 2px;
}

.tah-word,
.en-word {
    cursor: pointer;
    border-bottom: 1px dotted var(--accent);
}

.tah-word:hover,
.tah-word.active,
.en-word:hover,
.en-word.active {
    background: var(--hover-bg);
}

.tah-popup {
    position: fixed;
    max-width: 280px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
    font-size: 14px;
    line-height: 1.4;
    color: var(--text);
    z-index: 3000;
}

.bookmark {
    text-decoration: none;
    font-size: 15px;
    opacity: 0.55;
}

.bookmark:hover,
.bookmark:focus-visible {
    opacity: 1;
}

.guide-content {
    overflow-wrap: break-word;
    word-break: break-word;
}

.conf-session {
    margin: 0 0 4px;
    font-size: 13px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.conf-speaker {
    margin: 0 0 16px;
    font-size: 15px;
    color: var(--text-muted);
}

.guide-content.isolated .guide-entry {
    display: none;
}

.guide-content.isolated .guide-entry.target {
    display: block;
}

.entry-card-controls {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin: 16px 0 24px;
}

.entry-card-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
}

.entry-card-counter {
    font-size: 13px;
    color: var(--text-muted);
}

.entry-card-actions {
    display: flex;
    gap: 8px;
}

.entry-card-nav button,
.entry-card-actions button {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--accent);
    font: inherit;
    font-size: 18px;
    line-height: 1;
    cursor: pointer;
}

.entry-card-nav button:hover,
.entry-card-actions button:hover {
    background: var(--hover-bg);
}

.entry-card-actions button.copied {
    color: #4ade80;
    border-color: #4ade80;
}

.entry-card-nav button:disabled {
    opacity: 0.4;
    cursor: default;
}

.toast {
    position: fixed;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    background: #1c1e21;
    color: #ffffff;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 14px;
    opacity: 0;
    transition: opacity 0.2s ease;
    pointer-events: none;
    z-index: 1000;
}

.toast.show {
    opacity: 1;
}

.guide-content h4,
.guide-content h3.conf-subhead {
    margin: 1.4em 0 0.4em;
    font-size: 15px;
    color: var(--accent);
}

.guide-content p {
    margin: 0.7em 0;
    line-height: 1.6;
    font-size: var(--reading-font-size);
}

.guide-content p.Indent1,
.guide-content [style*="margin-left"] {
    margin-left: 0 !important;
    padding-left: 1em;
    border-left: 3px solid var(--border);
}

.guide-content ol, .guide-content ul {
    padding-left: 1.4em;
}

.guide-content a {
    color: var(--accent);
    overflow-wrap: break-word;
}

.guide-content table {
    width: 100%;
    border-collapse: collapse;
    display: block;
    overflow-x: auto;
    margin: 1em 0;
}

.guide-content th, .guide-content td {
    border: 1px solid var(--border);
    padding: 6px 8px;
    text-align: left;
}

@media (max-width: 640px) {
    .page {
        padding: 20px 10px 60px;
    }

    .page-controls {
        top: 20px;
        right: 10px;
    }

    .volume-toggle {
        font-size: 17px;
        padding: 12px 14px;
    }

    .chapter-grid {
        grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
    }

    .verse-container {
        gap: 8px;
        font-size: 14px;
    }
}
'''

write('styles.css', css_content)

# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------

js_content = '''
(function() {
    var stored = localStorage.getItem('bukaAMoromona:theme');
    if (stored === 'light' || stored === 'dark') {
        document.documentElement.setAttribute('data-theme', stored);
    }
    var storedSize = localStorage.getItem('bukaAMoromona:textSize');
    var validSizes = ['xsmall', 'small', 'large', 'xlarge', 'xxlarge'];
    if (validSizes.indexOf(storedSize) !== -1) {
        document.documentElement.setAttribute('data-text-size', storedSize);
    }
})();

document.addEventListener('DOMContentLoaded', function() {
    var themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        var currentTheme = function() {
            var stored = localStorage.getItem('bukaAMoromona:theme');
            if (stored === 'light' || stored === 'dark') return stored;
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        };
        var updateIcon = function() {
            themeToggle.textContent = currentTheme() === 'dark' ? '☀️' : '\U0001F319';
        };
        updateIcon();
        themeToggle.addEventListener('click', function() {
            var next = currentTheme() === 'dark' ? 'light' : 'dark';
            localStorage.setItem('bukaAMoromona:theme', next);
            document.documentElement.setAttribute('data-theme', next);
            updateIcon();
        });
    }

    var textSizeToggle = document.querySelector('.text-size-toggle');
    var textSizePopover = document.getElementById('text-size-popover');
    if (textSizeToggle && textSizePopover) {
        var sizes = ['xsmall', 'small', 'normal', 'large', 'xlarge', 'xxlarge'];
        var steps = [].slice.call(textSizePopover.querySelectorAll('.text-size-step'));
        var shrinkBtn = steps[0];
        var growBtn = steps[1];

        var currentIndex = function() {
            var attr = document.documentElement.getAttribute('data-text-size');
            var i = sizes.indexOf(attr);
            return i === -1 ? sizes.indexOf('normal') : i;
        };
        var updateButtons = function() {
            var i = currentIndex();
            shrinkBtn.disabled = i === 0;
            growBtn.disabled = i === sizes.length - 1;
        };
        var applySize = function(size) {
            if (size === 'normal') {
                localStorage.removeItem('bukaAMoromona:textSize');
                document.documentElement.removeAttribute('data-text-size');
            } else {
                localStorage.setItem('bukaAMoromona:textSize', size);
                document.documentElement.setAttribute('data-text-size', size);
            }
            updateButtons();
        };

        updateButtons();
        textSizeToggle.addEventListener('click', function(event) {
            event.stopPropagation();
            updateButtons();
            textSizePopover.hidden = !textSizePopover.hidden;
        });
        document.addEventListener('click', function(event) {
            if (!textSizePopover.hidden && !textSizePopover.contains(event.target) && event.target !== textSizeToggle) {
                textSizePopover.hidden = true;
            }
        });
        steps.forEach(function(step) {
            step.addEventListener('click', function() {
                var dir = parseInt(step.getAttribute('data-dir'), 10);
                var next = currentIndex() + dir;
                if (next >= 0 && next < sizes.length) applySize(sizes[next]);
            });
        });
    }

    function wireToggle(button, content) {
        button.addEventListener('click', function() {
            const isOpen = content.classList.toggle('show');
            button.setAttribute('aria-expanded', String(isOpen));
        });
    }

    document.querySelectorAll('.volume-toggle, .accordion-button').forEach(function(button) {
        wireToggle(button, button.nextElementSibling);
    });

    // Arrivee via un signet (#vN) sur une page de guide : isole la ou les
    // entrees du meme verset (un verset peut avoir plusieurs entrees de
    // commentaire : vN, vN-2, vN-3...). Une seule entree est visible a la
    // fois, avec Precedent/Suivant pour naviguer entre elles, et
    // Copier/Partager sur l'entree affichee. Un lien "Retour au verset"
    // est ajoute dans la nav du bas pour revenir au verset francais.
    var guideContent = document.querySelector('.guide-content');
    if (guideContent && location.hash) {
        var targetId = location.hash.slice(1);
        var baseId = targetId.split('-')[0];
        var matches = [].slice.call(guideContent.querySelectorAll('.guide-entry')).filter(function(el) {
            return el.id === baseId || el.id.indexOf(baseId + '-') === 0;
        });
        if (matches.length) {
            guideContent.classList.add('isolated');
            var current = 0;
            var counterEl = null;
            var prevBtn = null;
            var nextBtn = null;

            function showEntry(i) {
                matches.forEach(function(el) { el.classList.remove('target'); });
                matches[i].classList.add('target');
                current = i;
                if (counterEl) counterEl.textContent = (i + 1) + ' / ' + matches.length;
                if (prevBtn) prevBtn.disabled = i === 0;
                if (nextBtn) nextBtn.disabled = i === matches.length - 1;
            }

            function goToEntry(i) {
                showEntry(i);
                guideContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }

            function entryParts(entry) {
                var h4 = entry.querySelector('h4');
                var title = h4 ? h4.textContent.trim() : '';
                var bodyParts = [];
                [].slice.call(entry.children).forEach(function(child) {
                    if (child !== h4) {
                        var t = child.textContent.trim();
                        if (t) bodyParts.push(t);
                    }
                });
                var guideText = bodyParts.length ? title + '\\n\\n' + bodyParts.join('\\n\\n') : title;
                return {
                    verseRef: entry.getAttribute('data-verse-ref'),
                    verseText: entry.getAttribute('data-verse-text'),
                    guideText: guideText
                };
            }

            function todayLong() {
                var d = new Date();
                var text = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
                return text.charAt(0).toUpperCase() + text.slice(1);
            }

            function entryText(entry) {
                var p = entryParts(entry);
                var datePrefix = todayLong() + '\\n\\n';
                if (p.verseRef && p.verseText) {
                    return datePrefix + p.verseRef + '\\n\\n' + p.verseText + '\\n\\nNotes du guide\\n\\n' + p.guideText;
                }
                return datePrefix + p.guideText;
            }

            function showToast(message) {
                var toast = document.createElement('div');
                toast.className = 'toast';
                toast.textContent = message;
                document.body.appendChild(toast);
                requestAnimationFrame(function() { toast.classList.add('show'); });
                setTimeout(function() {
                    toast.classList.remove('show');
                    setTimeout(function() { toast.remove(); }, 300);
                }, 2000);
            }

            var controls = document.createElement('div');
            controls.className = 'entry-card-controls';

            if (matches.length > 1) {
                var navRow = document.createElement('div');
                navRow.className = 'entry-card-nav';

                prevBtn = document.createElement('button');
                prevBtn.type = 'button';
                prevBtn.textContent = '‹';
                prevBtn.setAttribute('aria-label', 'Entree precedente');
                prevBtn.addEventListener('click', function() {
                    if (current > 0) goToEntry(current - 1);
                });

                counterEl = document.createElement('span');
                counterEl.className = 'entry-card-counter';

                nextBtn = document.createElement('button');
                nextBtn.type = 'button';
                nextBtn.textContent = '›';
                nextBtn.setAttribute('aria-label', 'Entree suivante');
                nextBtn.addEventListener('click', function() {
                    if (current < matches.length - 1) goToEntry(current + 1);
                });

                navRow.appendChild(prevBtn);
                navRow.appendChild(counterEl);
                navRow.appendChild(nextBtn);
                controls.appendChild(navRow);
            }

            var actionsRow = document.createElement('div');
            actionsRow.className = 'entry-card-actions';

            var ICON_COPY = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path></svg>';
            var ICON_CHECK = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"></path></svg>';
            var ICON_SHARE = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"></line><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"></line></svg>';

            var copyBtn = document.createElement('button');
            copyBtn.type = 'button';
            copyBtn.innerHTML = ICON_COPY;
            copyBtn.setAttribute('aria-label', 'Copier');
            copyBtn.title = 'Copier';
            copyBtn.addEventListener('click', function() {
                navigator.clipboard.writeText(entryText(matches[current])).then(function() {
                    showToast('Copie dans le presse-papier');
                    copyBtn.innerHTML = ICON_CHECK;
                    copyBtn.classList.add('copied');
                    setTimeout(function() {
                        copyBtn.innerHTML = ICON_COPY;
                        copyBtn.classList.remove('copied');
                    }, 2000);
                }, function() {
                    showToast('Impossible de copier');
                });
            });

            var shareBtn = document.createElement('button');
            shareBtn.type = 'button';
            shareBtn.innerHTML = ICON_SHARE;
            shareBtn.setAttribute('aria-label', 'Partager');
            shareBtn.title = 'Partager';
            shareBtn.addEventListener('click', function() {
                var text = entryText(matches[current]);
                var shareData = { text: text };
                if (navigator.share) {
                    navigator.share(shareData).catch(function() {});
                } else {
                    navigator.clipboard.writeText(text).then(function() {
                        showToast('Copie dans le presse-papier');
                    }, function() {
                        showToast('Impossible de copier');
                    });
                }
            });

            actionsRow.appendChild(copyBtn);
            actionsRow.appendChild(shareBtn);
            controls.appendChild(actionsRow);

            guideContent.parentNode.insertBefore(controls, guideContent.nextSibling);
            showEntry(0);

            var bookIdx = guideContent.getAttribute('data-book-idx');
            var chapterIdx = guideContent.getAttribute('data-chapter-idx');
            var nav = document.querySelector('nav');
            if (bookIdx && chapterIdx && nav) {
                var backLink = document.createElement('a');
                backLink.href = '../../chapters-fr/chapter_' + bookIdx + '_' + chapterIdx + '.html#' + baseId;
                backLink.textContent = 'Retour au verset';
                nav.insertBefore(document.createTextNode(' | '), nav.firstChild);
                nav.insertBefore(backLink, nav.firstChild);
            }
        }
    }

    // Glossaire au tap (tahitien pour le volume "Livre de Mormon (tahitien)",
    // anglais pour "General Conference") : chaque mot ayant une entree dans
    // le glossaire est tague <span class="tah-word"|"en-word"> au moment de
    // la generation - au tap, on charge le glossaire une seule fois (fetch +
    // cache memoire) et on affiche la glose dans une bulle sous le mot.
    // Meme mecanique pour les deux glossaires, juste selecteur/URL differents.
    function setupTapToTranslate(selector, dictUrl) {
        var words = document.querySelectorAll(selector);
        if (!words.length) return;
        var dictPromise = null;
        var popup = null;
        var activeWord = null;

        function loadDict() {
            if (!dictPromise) {
                dictPromise = fetch(dictUrl).then(function(r) { return r.json(); }).catch(function() { return {}; });
            }
            return dictPromise;
        }

        function closePopup() {
            if (popup) { popup.remove(); popup = null; }
            if (activeWord) { activeWord.classList.remove('active'); activeWord = null; }
        }

        function showPopup(el, gloss) {
            closePopup();
            activeWord = el;
            el.classList.add('active');
            popup = document.createElement('div');
            popup.className = 'tah-popup';
            popup.textContent = gloss;
            popup.style.maxWidth = Math.min(280, window.innerWidth - 16) + 'px';
            document.body.appendChild(popup);
            var wordRect = el.getBoundingClientRect();
            var popupRect = popup.getBoundingClientRect();
            var left = Math.min(Math.max(8, wordRect.left), window.innerWidth - popupRect.width - 8);
            var top = wordRect.bottom + 6;
            if (top + popupRect.height > window.innerHeight - 8) {
                top = wordRect.top - popupRect.height - 6;
            }
            popup.style.left = left + 'px';
            popup.style.top = top + 'px';
        }

        words.forEach(function(el) {
            el.addEventListener('click', function(event) {
                event.stopPropagation();
                if (activeWord === el) { closePopup(); return; }
                loadDict().then(function(dict) {
                    var gloss = dict[el.getAttribute('data-w')];
                    if (gloss) showPopup(el, gloss);
                });
            });
        });
        document.addEventListener('click', closePopup);
        window.addEventListener('scroll', closePopup);
    }

    setupTapToTranslate('.tah-word', '../tah_dict.json');
    setupTapToTranslate('.en-word', '../../en_dict.json');

    // Suivi de la position de lecture, generique pour tout volume : sauve en
    // localStorage le verset/entree actuellement en haut de l'ecran, une
    // position independante par volume (clef = data-volume-key). Un futur
    // volume n'a qu'a poser data-volume-key/data-volume-title sur son
    // conteneur de page pour heriter automatiquement de "Continuer la
    // lecture" - aucun code specifique a ajouter ici.
    var READING_STORAGE_KEY = 'bukaAMoromona:reading';
    var readingTrack = document.querySelector('[data-volume-key]');
    if (readingTrack) {
        var volumeKey = readingTrack.getAttribute('data-volume-key');
        var volumeTitle = readingTrack.getAttribute('data-volume-title');
        var saveTimer = null;
        function saveReadingPosition() {
            var items = readingTrack.querySelectorAll('[id]');
            var current = null;
            for (var i = 0; i < items.length; i++) {
                if (items[i].getBoundingClientRect().bottom > 80) {
                    current = items[i];
                    break;
                }
            }
            var h2 = document.querySelector('h2');
            var h1 = document.querySelector('h1');
            var all = {};
            try { all = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {}; } catch (e) {}
            all[volumeKey] = {
                volumeTitle: volumeTitle,
                href: location.pathname + (current ? '#' + current.id : ''),
                chapterTitle: h2 ? h2.textContent.trim() : (h1 ? h1.textContent.trim() : ''),
                itemId: current ? current.id : null
            };
            localStorage.setItem(READING_STORAGE_KEY, JSON.stringify(all));
        }
        window.addEventListener('scroll', function() {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(saveReadingPosition, 400);
        });
        window.addEventListener('pagehide', saveReadingPosition);
        saveReadingPosition();
    }

    // Page d'accueil : une ligne "Continuer la lecture" par volume ayant une
    // position enregistree.
    var continueSlot = document.getElementById('continue-reading-slot');
    if (continueSlot) {
        var savedAll = {};
        try { savedAll = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {}; } catch (e) {}
        Object.keys(savedAll).forEach(function(key) {
            var saved = savedAll[key];
            if (!saved || !saved.href) return;
            var link = document.createElement('a');
            link.className = 'continue-reading';
            link.href = saved.href;
            var verseMatch = /^v(\\d+)$/.exec(saved.itemId || '');
            var suffix = verseMatch ? (', verset ' + verseMatch[1]) : '';
            link.textContent = 'Continuer — ' + saved.volumeTitle + ' : ' + saved.chapterTitle + suffix;
            continueSlot.appendChild(link);
        });
    }
});
'''

write('script.js', js_content)

# Cache-busting : sans ca, le navigateur (et le CDN de GitHub Pages) peut
# continuer a servir un ancien script.js en cache apres un deploy, donnant
# l'impression qu'un fix ne "marche pas" alors qu'il est bien en ligne.
# Version = hash du contenu, ajoutee en ?v= sur toutes les pages generees.
import hashlib
script_version = hashlib.md5(js_content.encode('utf-8')).hexdigest()[:8]
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d != '.git']
    for fname in files:
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content.replace('script.js"', f'script.js?v={script_version}"')
        if new_content != content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
