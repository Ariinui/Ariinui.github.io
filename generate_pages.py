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
    return section_tag.decode_contents()


# ---------------------------------------------------------------------------
# Volume 6 source : 2e Study Guide, "Start to Finish" (meme auteur Valletta,
# edition differente/plus complete que le volume 3 ci-dessus - structure HTML
# radicalement differente : export InDesign, <section id="chapitre-N">
# generique en ordre de lecture (rien a voir avec les vrais numeros de
# chapitre BdM), un seul <p class="Chapter-Number"> par section donnant
# "1 Nephi 1" etc., et le decoupage en entrees se fait via
# <p class="commentary-subhead"> ("1 Nephi 1:1-3. Nephi Begins His Record")
# plutot que via des <h4> comme le volume 3. Source deja nettoyee des <img>
# avant d'etre commitee (fichier source brut = 18 Mo d'images en base64,
# exigence utilisateur "sans les images").
# ---------------------------------------------------------------------------

GUIDE2_DASH_RE = re.compile('[‐-―]')


def parse_guide2_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    books_by_name = {}  # nom complet (meme convention que BOOK_NAME_MAP) -> {chapter_num: {'title','section'}}
    for sec in soup.find_all('section', id=True):
        chap_p = sec.find('p', class_='Chapter-Number')
        if not chap_p:
            continue  # page de garde/TOC/copyright, pas un chapitre de commentaire
        title = chap_p.get_text(' ', strip=True)
        tokens = title.split()
        if not tokens or not tokens[-1].isdigit():
            continue
        chapter_num = int(tokens[-1])
        book_name = ' '.join(tokens[:-1])
        books_by_name.setdefault(book_name, {})[chapter_num] = {'title': title, 'section': sec}

    # Meme principe que parse_guide_source() (un <div class="guide-entry"
    # id="vN"> isolable par question), mais keye sur CHAQUE QUESTION
    # individuelle (span.commentary-head) plutot que sur le
    # commentary-subhead qui couvre toute une plage de versets - chaque
    # question porte sa propre citation "(chap:verset)" (ex. "What does
    # goodly mean? (1:1)"), donc plusieurs questions peuvent cibler le meme
    # verset -> meme pager "1/N" que le guide Gospel Doctrine quand on
    # arrive dessus par le signet. Une question stylee (ex. mot en italique)
    # peut se retrouver coupee en plusieurs <span class="commentary-head">
    # consecutifs - la citation atterrit alors dans le DERNIER span, celui
    # qui matche VERSE_REF_RE ; les spans precedents (sans match) sont
    # simplement ignores puisque le paragraphe <p class="commentary"> parent
    # est de toute facon englouti par le span qui matche (aucune perte).
    verse_index_by_name = {}
    for book_name, chapters in books_by_name.items():
        for chap_num, chapter in chapters.items():
            seen = {}
            for head_span in chapter['section'].find_all('span', class_='commentary-head'):
                commentary_p = head_span.find_parent('p', class_='commentary')
                if commentary_p is None:
                    continue
                text = GUIDE2_DASH_RE.sub('-', head_span.get_text(' ', strip=True))
                m = VERSE_REF_RE.search(text)
                if not m:
                    continue
                v_start = int(m.group(2))
                seen[v_start] = seen.get(v_start, 0) + 1
                n = seen[v_start]
                anchor_id = f'v{v_start}' if n == 1 else f'v{v_start}-{n}'

                wrapper = soup.new_tag('div')
                wrapper['class'] = 'guide-entry'
                wrapper['id'] = anchor_id
                wrapper['data-verse-start'] = str(v_start)
                wrapper['data-verse-end'] = str(v_start)
                commentary_p.insert_before(wrapper)
                node = commentary_p
                while node is not None and not (
                    node is not commentary_p and getattr(node, 'name', None) == 'p'
                    and node.get('class') and (
                        'commentary' in node.get('class') or 'commentary-subhead' in node.get('class')
                    )
                ):
                    nxt = node.next_sibling
                    wrapper.append(node.extract())
                    node = nxt

                key = (book_name, chap_num, v_start)
                if key not in verse_index_by_name:
                    verse_index_by_name[key] = anchor_id

    return books_by_name, verse_index_by_name


def guide2_section_content_html(section_tag):
    """HTML interne d'une section guide2 : uniquement les paires
    question/reponse (une par <div class="guide-entry">, deja decoupees par
    parse_guide2_source), meme principe editorial que le guide Gospel
    Doctrine - jamais de texte de verset duplique (deja affiche cote Livre
    de Mormon), jamais de resume de chapitre ni de sous-titre de plage de
    versets, jamais de citation etendue (Extended_Content_1). Le numero de
    chapitre est aussi retire, deja rendu par notre propre <h1>/<h2> de
    page."""
    chap_p = section_tag.find('p', class_='Chapter-Number')
    if chap_p:
        chap_p.decompose()
    for tag in section_tag.find_all(
        ['p', 'div'],
        class_=['verse', 'studySummary', 'Extended_Content_1', 'frame-3', 'commentary-subhead']
    ):
        tag.decompose()
    # Paragraphes de question/reponse restes orphelins (hors de tout
    # guide-entry) : le texte d'introduction avant la toute premiere
    # question d'un chapitre, ou une question dont la citation verset n'a
    # jamais matche (aucun span.commentary-head du paragraphe).
    for cls in ('commentary', 'commentary-second-para'):
        for stray in section_tag.find_all('p', class_=cls):
            if stray.find_parent('div', class_='guide-entry') is None:
                stray.decompose()
    return section_tag.decode_contents()


# ---------------------------------------------------------------------------
# Volume 7 source : Verse by Verse Book of Mormon (D. Kelly Ogden) - export
# Calibre generique (comme le Livre de Mormon anglais), aucune balise
# semantique (section/hN) : tout repose sur des classes calibre_N decouvertes
# par inspection structurelle du fichier source :
#   - p.calibre_9  : titre de livre (19x - les 15 vrais livres + avant-propos
#     "Preface"/"Introduction"/"Sources"... hors scope, ignores)
#   - p.calibre_10 : en-tetes de reference, granularite MIXTE - soit un
#     survol de chapitre/plage sans verset precis ("1 Nephi 8",
#     "2 Nephi 1-4"), soit une citation verset precise ("1 Nephi 1:1-3"),
#     parfois suivie d'une parenthese de renvoi Isaie ("(Isaiah 48)") - aussi
#     un doublon du titre de livre en toutes lettres (ignore, deja notre
#     <h1>). Meme piege de tiret Unicode que guide2 (GUIDE2_DASH_RE reutilise
#     ici), plus un espace insecable (\xa0) trouve entre certains numeros de
#     livre et leur nom ("3\xa0Nephi").
#   - p.calibre_11 : en-tete "Note"/"Notes" (systeme de notes de bas de page
#     numerotees, liens <a href="#calibre_link-N"> vers une ancre vide plus
#     loin dans le document) - fusionnees dans l'entree courante comme un
#     paragraphe de continuation plutot que gardees comme un renvoi separe
#     (decision utilisateur - le contenu de la note est garde, pas le lien).
# Les autres classes de <p> (calibre_5/6/7/15/17...) sont du texte de
# commentaire ordinaire. Un simple soup.find_all('p') suffit a lire le
# document dans l'ordre de lecture - les <div class="calibre"/"mbp_pagebreak">
# englobants ne sont que du decoupage de page Calibre, pas une hierarchie
# semantique (verifie : le flux de <p> reste coherent sans jamais consulter
# ces div).
# Les 63 en-tetes de survol (chapitre seul ou plage) n'ont pas de verset
# precis -> pas de signet, juste un bloc affiche en tete de la page du
# PREMIER chapitre de la plage (decision utilisateur).
# ---------------------------------------------------------------------------

VV_BOOK_TITLE_MAP = {
    'The First Book of Nephi': '1 Nephi', 'The Second Book of Nephi': '2 Nephi',
    'The Book of Jacob': 'Jacob', 'The Book of Enos': 'Enos', 'The Book of Jarom': 'Jarom',
    'The Book of Omni': 'Omni', 'The Words of Mormon': 'Words of Mormon',
    'The Book of Mosiah': 'Mosiah', 'The Book of Alma': 'Alma', 'The Book of Helaman': 'Helaman',
    'The Third Book of Nephi': '3 Nephi', 'The Fourth Book of Nephi': '4 Nephi',
    'The Book of Mormon': 'Mormon', 'The Book of Ether': 'Ether', 'The Book of Moroni': 'Moroni',
}

VV_BOOK_PREFIX_RE = re.compile(
    r'^(' + '|'.join(re.escape(b) for b in sorted(VV_BOOK_TITLE_MAP.values(), key=len, reverse=True)) + r')\s+(.+)$'
)
VV_TRAILING_PAREN_RE = re.compile(r'\s*\(([^()]*)\)\s*$')
VV_CHAPTER_ONLY_RE = re.compile(r'^(\d+)(?:\s*-\s*(\d+))?$')


def parse_vv_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    books_by_name = {}  # nom court -> {chapter_num: {'title', 'section' (Tag synthetique)}}
    verse_index_by_name = {}  # (book_name, chap_num, verse_num) -> anchor_id
    seen_by_book_chapter = {}  # (book_name, chap_num) -> {verse_start: count}

    def get_chapter_section(book_name, chap_num):
        chapters = books_by_name.setdefault(book_name, {})
        if chap_num not in chapters:
            chapters[chap_num] = {'title': f'{book_name} {chap_num}', 'section': soup.new_tag('div')}
        return chapters[chap_num]['section']

    state = {'current_entry': None}

    for p in soup.find_all('p'):
        cls = p.get('class') or []
        text = p.get_text(' ', strip=True).replace('\xa0', ' ')

        if 'calibre_9' in cls:
            state['current_entry'] = None
            continue

        if 'calibre_10' in cls:
            if text in VV_BOOK_TITLE_MAP:
                continue  # doublon du titre de livre, deja notre <h1>
            m = VV_BOOK_PREFIX_RE.match(text)
            if not m:
                state['current_entry'] = None
                continue  # legende d'image, "Introduction to Isaiah"... ignore
            book_name, remainder = m.group(1), m.group(2)
            pm = VV_TRAILING_PAREN_RE.search(remainder)
            ref_extra = None
            if pm:
                ref_extra = pm.group(1)
                remainder = remainder[:pm.start()].strip()
            remainder = GUIDE2_DASH_RE.sub('-', remainder)

            if ':' in remainder:
                vm = VERSE_REF_RE.search(remainder)
                if not vm:
                    state['current_entry'] = None
                    continue
                chap_num = int(vm.group(1))
                v_start = int(vm.group(2))
                v_end = int(vm.group(3)) if vm.group(3) else v_start
                section = get_chapter_section(book_name, chap_num)
                key = (book_name, chap_num)
                seen = seen_by_book_chapter.setdefault(key, {})
                seen[v_start] = seen.get(v_start, 0) + 1
                n = seen[v_start]
                anchor_id = f'v{v_start}' if n == 1 else f'v{v_start}-{n}'
                wrapper = soup.new_tag('div')
                wrapper['class'] = 'guide-entry'
                wrapper['id'] = anchor_id
                wrapper['data-verse-start'] = str(v_start)
                wrapper['data-verse-end'] = str(v_end)
                section.append(wrapper)
                state['current_entry'] = wrapper
                idx_key = (book_name, chap_num, v_start)
                if idx_key not in verse_index_by_name:
                    verse_index_by_name[idx_key] = anchor_id
            else:
                cm = VV_CHAPTER_ONLY_RE.match(remainder)
                if not cm:
                    state['current_entry'] = None
                    continue
                chap_start = int(cm.group(1))
                section = get_chapter_section(book_name, chap_start)
                wrapper = soup.new_tag('div')
                wrapper['class'] = 'vv-overview'
                label = soup.new_tag('p')
                label['class'] = 'vv-overview-label'
                label.string = f'{book_name} {remainder}' + (f' ({ref_extra})' if ref_extra else '')
                wrapper.append(label)
                section.append(wrapper)
                state['current_entry'] = wrapper
            continue

        if 'calibre_11' in cls:
            if state['current_entry'] is not None and text in ('Note', 'Notes'):
                label = soup.new_tag('p')
                label['class'] = 'vv-note-label'
                label.string = text
                state['current_entry'].append(label)
            continue

        # Paragraphe de corps ordinaire (commentaire ou texte de note fusionne).
        if state['current_entry'] is None:
            continue
        node = p.extract()
        for a in node.find_all('a'):
            a.unwrap()
        for img in node.find_all('img'):
            img.decompose()
        state['current_entry'].append(node)

    return books_by_name, verse_index_by_name


def vv_section_content_html(section_tag):
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

# Icone de signet partagee par les liens de signet (colores par type via
# CSS, cf. .bookmark-guide/.bookmark-guide2) et leur controle
# activer/desactiver - un futur type de signet (nouveau volume) reutilise
# ces memes fonctions, juste une nouvelle couleur CSS et une ligne ajoutee a
# BOOKMARK_FILTER_ROWS ci-dessous. Regroupes derriere UN SEUL bouton
# d'entete avec un popover (meme mecanisme que .text-size-control) plutot
# qu'un bouton par couleur affiche en permanence - evite tout chevauchement
# avec le titre au fil des futurs ajouts, l'entete ne grossit jamais.
ICON_BOOKMARK = ('<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" '
                  'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                  'stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z">'
                  '</path></svg>')


def bookmark_link(href, type_key, label):
    return (f' <a class="bookmark bookmark-{type_key}" href="{href}" '
            f'title="{label}" aria-label="{label}">{ICON_BOOKMARK}</a>')


def bookmark_filter_row(type_key, label):
    return (f'<button type="button" class="bookmark-filter-row" data-bookmark-key="{type_key}" '
            f'role="menuitemcheckbox" aria-checked="true">'
            f'<span class="bookmark-filter-icon bookmark-{type_key}">{ICON_BOOKMARK}</span>'
            f'<span class="bookmark-filter-label">{label}</span>'
            f'<span class="bookmark-filter-switch" aria-hidden="true"></span>'
            f'</button>')


BOOKMARK_FILTER_ROWS = (
    bookmark_filter_row('guide', "Gospel Doctrine")
    + bookmark_filter_row('guide2', "Start to Finish")
    + bookmark_filter_row('guide3', "Verse by Verse")
)

BOOKMARK_FILTER_CONTROL = f'''
            <div class="bookmark-filter-control">
                <button class="bookmark-filter-toggle" type="button" aria-label="Signets" title="Signets" aria-haspopup="true" aria-expanded="false">{ICON_BOOKMARK}</button>
                <div class="bookmark-filter-popover" id="bookmark-filter-popover" role="menu" hidden>
                    {BOOKMARK_FILTER_ROWS}
                </div>
            </div>
'''

CHAPTER_NAV = '''
    <nav>
        {prev_link}
        {next_link}
    </nav>
    <script>
    (function() {{
        if (!window.history || !window.history.pushState) return;
        // Empeche le navigateur de restaurer nativement le scroll (souvent
        // remis a 0) quand on revient sur l'entree d'historique ci-dessous -
        // sinon la sauvegarde de position (pagehide) lit "haut de page" au
        // moment du swipe-retour et ecrase la vraie position de lecture.
        if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
        history.pushState({{backToToc: true}}, '', location.href);
        window.addEventListener('popstate', function() {{
            location.replace('{index_href}');
        }});
    }})();
    </script>
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
guide2_books_by_name, guide2_verse_index_by_name = parse_guide2_source(
    'book-of-mormon-study-guide-2/index.html'
)
guide3_books_by_name, guide3_verse_index_by_name = parse_vv_source(
    'verse-by-verse-book-of-mormon/index.html'
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

# guide2 : meme mapping de noms (guide_name_to_bom_idx) que le guide 3, les
# deux sources Valletta nomment leurs livres pareil ("1 Nephi", "Words of
# Mormon", ...) - verifie sur les 15 livres avant d'ecrire ce code.
guide2_chapters_by_bom_idx = {}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide2_chapters = guide2_books_by_name.get(guide_name, {})
    guide2_chapters_by_bom_idx[book_idx] = guide2_chapters
    if not guide2_chapters:
        print(f"INFO: pas de contenu guide2 pour {bom_book['book_title']!r} ({guide_name!r}).")
    elif set(guide2_chapters.keys()) != set(range(1, len(bom_book['chapters']) + 1)):
        print(f"ATTENTION guide2: {bom_book['book_title']!r} a {len(bom_book['chapters'])} chapitres LoM "
              f"mais guide2 a les chapitres {sorted(guide2_chapters.keys())}.")

guide2_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide2_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide2_verse_index[(book_idx, chap_num, verse_num)] = anchor

# guide3 (Verse by Verse) : meme mapping de noms que guide/guide2, ses en-tetes
# utilisent deja directement le nom court anglais ("1 Nephi", "Words of
# Mormon"...), identique a BOOK_NAME_MAP.values().
guide3_chapters_by_bom_idx = {}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide3_chapters = guide3_books_by_name.get(guide_name, {})
    guide3_chapters_by_bom_idx[book_idx] = guide3_chapters
    if not guide3_chapters:
        print(f"INFO: pas de contenu guide3 pour {bom_book['book_title']!r} ({guide_name!r}).")
    elif set(guide3_chapters.keys()) != set(range(1, len(bom_book['chapters']) + 1)):
        print(f"ATTENTION guide3: {bom_book['book_title']!r} a {len(bom_book['chapters'])} chapitres LoM "
              f"mais guide3 a les chapitres {sorted(guide3_chapters.keys())}.")

guide3_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide3_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide3_verse_index[(book_idx, chap_num, verse_num)] = anchor

# Repart de zero a chaque generation : les numeros de chapitre du guide ont
# des trous (livres/chapitres absents de la source), donc une ancienne
# execution peut laisser des fichiers a un chemin qui n'est plus le bon.
for d in ('chapters', 'chapters-fr', 'chapters-tah', 'chapters-en', 'guide', 'guide2', 'guide3', 'conference'):
    shutil.rmtree(d, ignore_errors=True)
os.makedirs('chapters', exist_ok=True)
os.makedirs('chapters-fr', exist_ok=True)
os.makedirs('chapters-tah', exist_ok=True)
os.makedirs('chapters-en', exist_ok=True)
os.makedirs('guide/chapters', exist_ok=True)
os.makedirs('guide2/chapters', exist_ok=True)
os.makedirs('guide3/chapters', exist_ok=True)
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

toc_html += render_volume_block('Book of Mormon Study Guide (Gospel Doctrine)', guide_all_books, guide_href)

guide2_all_books = []
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide2_chapters = guide2_chapters_by_bom_idx[book_idx]
    if not guide2_chapters:
        continue
    guide2_all_books.append({
        'book_title': bom_book['book_title'],
        'book_idx': book_idx,
        'chapters': [dict(guide2_chapters[n], chapter_num=n) for n in sorted(guide2_chapters.keys())]
    })

def guide2_href(bi, ci, ch):
    real_book = guide2_all_books[bi - 1]
    return f'guide2/chapters/chapter_{real_book["book_idx"]}_{ci}.html'

toc_html += render_volume_block('Book of Mormon Study Guide (Start to Finish)', guide2_all_books, guide2_href)

guide3_all_books = []
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide3_chapters = guide3_chapters_by_bom_idx[book_idx]
    if not guide3_chapters:
        continue
    guide3_all_books.append({
        'book_title': bom_book['book_title'],
        'book_idx': book_idx,
        'chapters': [dict(guide3_chapters[n], chapter_num=n) for n in sorted(guide3_chapters.keys())]
    })

def guide3_href(bi, ci, ch):
    real_book = guide3_all_books[bi - 1]
    return f'guide3/chapters/chapter_{real_book["book_idx"]}_{ci}.html'

toc_html += render_volume_block('Verse by Verse Book of Mormon', guide3_all_books, guide3_href)

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
            verses_html += f'<p class="verse-fr" id="v{verse_num}">'
            verses_html += f'<sup>{verse_num}</sup>{verse_text}'
            anchor = guide_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor:
                guide_link = f'../guide/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor}'
                verses_html += bookmark_link(guide_link, 'guide', "Voir le commentaire du guide d'etude (Gospel Doctrine)")
            anchor2 = guide2_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor2:
                guide2_link = f'../guide2/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor2}'
                verses_html += bookmark_link(guide2_link, 'guide2', "Voir le commentaire du guide d'etude (Start to Finish)")
            anchor3 = guide3_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor3:
                guide3_link = f'../guide3/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor3}'
                verses_html += bookmark_link(guide3_link, 'guide3', "Voir le commentaire Verse by Verse")
            verses_html += '</p>'

        introduction_html = ''
        if chapter['introduction']:
            introduction_html = f'<p class="verse-fr introduction">{chapter["introduction"]["francais"]}</p>'

        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL + BOOKMARK_FILTER_CONTROL)
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
                # Nom complet ("1 Nephi") plutot que l'abreviation francaise
                # source ("1 Ne") au Copier/Partager - meme demande que pour
                # Start to Finish ci-dessous.
                full_book_name = BOOK_NAME_MAP.get(bom_book['book_title'], bom_book['book_title'])
                entry['data-verse-ref'] = f'{full_book_name} {ref}'
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

# --- Volume 6 : Book of Mormon Study Guide (Start to Finish) ----------------

for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide2_chapters = guide2_chapters_by_bom_idx[book_idx]
    chapter_nums = sorted(guide2_chapters.keys())
    for chap_idx in chapter_nums:
        chapter = guide2_chapters[chap_idx]

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
                          f"(entree guide2 {vstart}-{vend}) - Copier/Partager n'inclura pas ce verset.")
            if pieces:
                ref = f'{chap_idx}:{vstart}' if vstart == vend else f'{chap_idx}:{vstart}-{vend}'
                # Nom complet ("1 Nephi") plutot que l'abreviation francaise
                # source ("1 Ne") - uniquement pour Start to Finish, sur
                # demande explicite ; Gospel Doctrine garde l'abreviation.
                full_book_name = BOOK_NAME_MAP.get(bom_book['book_title'], bom_book['book_title'])
                entry['data-verse-ref'] = f'{full_book_name} {ref}'
                entry['data-verse-text'] = ' '.join(pieces)

        content_html = guide2_section_content_html(chapter['section'])
        has_prev = chapter_nums.index(chap_idx) > 0
        has_next = chapter_nums.index(chap_idx) < len(chapter_nums) - 1
        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if has_prev else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if has_next else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{bom_book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="guide-content" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}" data-volume-key="guide2" data-volume-title="Book of Mormon Study Guide (Start to Finish)">{content_html}</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
        html += PAGE_TAIL

        write(f'guide2/chapters/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 7 : Verse by Verse Book of Mormon --------------------------------

for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide3_chapters = guide3_chapters_by_bom_idx[book_idx]
    chapter_nums = sorted(guide3_chapters.keys())
    for chap_idx in chapter_nums:
        chapter = guide3_chapters[chap_idx]

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
                          f"(entree guide3 {vstart}-{vend}) - Copier/Partager n'inclura pas ce verset.")
            if pieces:
                ref = f'{chap_idx}:{vstart}' if vstart == vend else f'{chap_idx}:{vstart}-{vend}'
                full_book_name = BOOK_NAME_MAP.get(bom_book['book_title'], bom_book['book_title'])
                entry['data-verse-ref'] = f'{full_book_name} {ref}'
                entry['data-verse-text'] = ' '.join(pieces)

        content_html = vv_section_content_html(chapter['section'])
        has_prev = chapter_nums.index(chap_idx) > 0
        has_next = chapter_nums.index(chap_idx) < len(chapter_nums) - 1
        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if has_prev else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if has_next else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h1>{bom_book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="guide-content" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}" data-volume-key="guide3" data-volume-title="Verse by Verse Book of Mormon">{content_html}</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
        html += PAGE_TAIL

        write(f'guide3/chapters/chapter_{book_idx}_{chap_idx}.html', html)

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
guide2_chapter_count = sum(len(c) for c in guide2_chapters_by_bom_idx.values())
guide3_chapter_count = sum(len(c) for c in guide3_chapters_by_bom_idx.values())
print(f'{sum(len(b["chapters"]) for b in bom_book_data)} chapitres LoM, '
      f'{guide_chapter_count} chapitres guide, '
      f'{len(guide_intro_items)} pages intro, '
      f'{len(guide_verse_index)} versets avec signet guide. '
      f'{guide2_chapter_count} chapitres guide2, '
      f'{len(guide2_verse_index)} versets avec signet guide2. '
      f'{guide3_chapter_count} chapitres guide3, '
      f'{len(guide3_verse_index)} versets avec signet guide3.')

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
    opacity: 0.55;
    display: inline-flex;
    vertical-align: middle;
}

.bookmark:hover,
.bookmark:focus-visible {
    opacity: 1;
}

/* Chaque type de signet a sa propre couleur - un futur volume n'a qu'a
   ajouter une regle .bookmark-<cle> ici + une ligne dans BOOKMARK_FILTER_ROWS
   (cote Python), le reste (popover, persistance, isolation) est deja
   generique. */
.bookmark-guide { color: #d4a017; }
.bookmark-guide2 { color: #b22222; }
.bookmark-guide3 { color: #1e6fd9; }

html[data-hide-bookmark-guide] .bookmark-guide { display: none; }
html[data-hide-bookmark-guide2] .bookmark-guide2 { display: none; }
html[data-hide-bookmark-guide3] .bookmark-guide3 { display: none; }

/* Volume 7 (Verse by Verse) : survol de chapitre/plage sans verset precis
   (pas de signet dessus) et libelle "Note"/"Notes" fusionne dans l'entree -
   juste une distinction visuelle legere, le reste vient du style generique
   .guide-content p. */
.vv-overview {
    margin-bottom: 1em;
    padding-bottom: 1em;
    border-bottom: 1px solid var(--border);
}
.vv-overview-label {
    font-style: italic;
    opacity: 0.75;
}
.vv-note-label {
    font-weight: 600;
    opacity: 0.7;
    margin-top: 0.75em;
}

/* Un seul bouton d'entete pour tous les signets, avec un popover listant un
   toggle par type - ne grossit jamais dans l'entete quel que soit le nombre
   de types de signets ajoutes au fil du temps. */
.bookmark-filter-toggle {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    cursor: pointer;
}

.bookmark-filter-toggle:hover {
    background: var(--hover-bg);
}


.bookmark-filter-popover {
    /* Ancre sur .page-controls (deja position:absolute, donc bloc
       englobant valide) plutot que sur .bookmark-filter-control lui-meme -
       ce bouton n'est pas le plus a droite de la rangee (theme-toggle le
       suit), un ancrage sur lui-meme faisait deborder le popover a gauche
       de l'ecran sur mobile etroit. */
    position: absolute;
    right: 0;
    top: calc(100% + 8px);
    display: flex;
    flex-direction: column;
    width: min(190px, calc(100vw - 32px));
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    z-index: 2000;
}

.bookmark-filter-popover[hidden] {
    display: none;
}

.bookmark-filter-row {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 8px;
    background: none;
    border: none;
    border-radius: 7px;
    color: var(--text);
    font-size: 13px;
    font-family: inherit;
    text-align: left;
    cursor: pointer;
    white-space: nowrap;
}

.bookmark-filter-row:hover {
    background: var(--hover-bg);
}

.bookmark-filter-icon {
    display: flex;
    flex-shrink: 0;
}

.bookmark-filter-icon svg {
    width: 13px;
    height: 13px;
}

.bookmark-filter-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
}

.bookmark-filter-switch {
    position: relative;
    width: 26px;
    height: 15px;
    flex-shrink: 0;
    border-radius: 999px;
    background: var(--border);
    transition: background 0.15s ease;
}

.bookmark-filter-switch::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: #fff;
    transition: transform 0.15s ease;
}

.bookmark-filter-row[aria-checked="false"] .bookmark-filter-switch {
    background: var(--border);
}

.bookmark-filter-row[aria-checked="true"] .bookmark-filter-switch {
    background: #22c55e;
}

.bookmark-filter-row[aria-checked="true"] .bookmark-filter-switch::after {
    transform: translateX(11px);
}

.guide-content {
    overflow-wrap: break-word;
    word-break: break-word;
}

/* Question du guide Start to Finish - meme rouge que les citations
   surlignees du guide Gospel Doctrine (voir .bookmark-guide2). */
.commentary-head {
    color: #b22222;
    font-weight: bold;
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
    // Etat cache/affiche de chaque type de signet, generique : un futur type
    // de signet (nouveau volume, nouvelle couleur) n'a besoin d'aucun ajout
    // ici, seule sa cle localStorage suffit a le faire reconnaitre.
    for (var bmI = 0; bmI < localStorage.length; bmI++) {
        var bmK = localStorage.key(bmI);
        if (bmK && bmK.indexOf('bukaAMoromona:hideBookmark:') === 0) {
            if (localStorage.getItem(bmK) === '1') {
                document.documentElement.setAttribute('data-hide-bookmark-' + bmK.slice('bukaAMoromona:hideBookmark:'.length), '');
            }
        }
    }
})();

document.addEventListener('DOMContentLoaded', function() {
    var bookmarkFilterToggle = document.querySelector('.bookmark-filter-toggle');
    var bookmarkFilterPopover = document.getElementById('bookmark-filter-popover');
    if (bookmarkFilterToggle && bookmarkFilterPopover) {
        bookmarkFilterToggle.addEventListener('click', function(event) {
            event.stopPropagation();
            bookmarkFilterPopover.hidden = !bookmarkFilterPopover.hidden;
            bookmarkFilterToggle.setAttribute('aria-expanded', bookmarkFilterPopover.hidden ? 'false' : 'true');
        });
        document.addEventListener('click', function(event) {
            if (!bookmarkFilterPopover.hidden && !bookmarkFilterPopover.contains(event.target) && event.target !== bookmarkFilterToggle) {
                bookmarkFilterPopover.hidden = true;
                bookmarkFilterToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    [].slice.call(document.querySelectorAll('.bookmark-filter-row')).forEach(function(row) {
        var key = row.getAttribute('data-bookmark-key');
        var storageKey = 'bukaAMoromona:hideBookmark:' + key;
        var attr = 'data-hide-bookmark-' + key;
        var sync = function() {
            row.setAttribute('aria-checked', localStorage.getItem(storageKey) === '1' ? 'false' : 'true');
        };
        sync();
        row.addEventListener('click', function() {
            if (localStorage.getItem(storageKey) === '1') {
                localStorage.removeItem(storageKey);
                document.documentElement.removeAttribute(attr);
            } else {
                localStorage.setItem(storageKey, '1');
                document.documentElement.setAttribute(attr, '');
            }
            sync();
        });
    });

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
            var partIndex = 0;
            var counterEl = null;
            var prevBtn = null;
            var nextBtn = null;

            function showEntry(i) {
                matches.forEach(function(el) { el.classList.remove('target'); });
                matches[i].classList.add('target');
                current = i;
                partIndex = 0;
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
                    if (child === h4) return;
                    var head = child.querySelector('.commentary-head');
                    var t;
                    if (head) {
                        // Start to Finish : question et reponse sont dans le
                        // meme <p>, sans separation - on isole la question
                        // (span.commentary-head) du reste pour les afficher
                        // sur des lignes distinctes au Copier/Partager.
                        var clone = child.cloneNode(true);
                        var cloneHead = clone.querySelector('.commentary-head');
                        var question = cloneHead.textContent.trim();
                        cloneHead.parentNode.removeChild(cloneHead);
                        var answer = clone.textContent.trim();
                        t = answer ? question + '\\n\\n' + answer : question;
                    } else {
                        t = child.textContent.trim();
                    }
                    if (t) bodyParts.push(t);
                });
                return {
                    verseRef: entry.getAttribute('data-verse-ref'),
                    verseText: entry.getAttribute('data-verse-text'),
                    title: title,
                    bodyParts: bodyParts
                };
            }

            function todayLong() {
                var d = new Date();
                var text = d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
                return text.charAt(0).toUpperCase() + text.slice(1);
            }

            function underline(str) {
                return str.split('').map(function(c) { return c + '\\u0332'; }).join('');
            }

            // Un message Messenger au-dela d'un certain nombre de caracteres
            // est coupe automatiquement par Messenger (limite non documentee
            // de facon fiable, valeur prudente retenue ici) - le texte est
            // donc decoupe en plusieurs messages a envoyer a la suite plutot
            // que risquer une troncature silencieuse.
            var MESSENGER_CHUNK_MAX = 1800;

            function splitLongBlock(text, maxLen) {
                // Secours si un seul paragraphe depasse a lui seul la limite :
                // coupe au dernier espace avant la limite, jamais en plein mot.
                var parts = [];
                while (text.length > maxLen) {
                    var cut = text.lastIndexOf(' ', maxLen);
                    if (cut <= 0) cut = maxLen;
                    parts.push(text.slice(0, cut));
                    text = text.slice(cut).trim();
                }
                parts.push(text);
                return parts;
            }

            function entryTextParts(entry, underlineNotesLabel) {
                var p = entryParts(entry);
                var notesLabel = underlineNotesLabel ? underline('Notes du guide') : 'Notes du guide';

                var blocks = [todayLong()];
                if (p.verseRef && p.verseText) {
                    blocks.push(p.verseRef);
                    blocks.push(p.verseText);
                    blocks.push(notesLabel);
                }
                blocks = blocks.concat(p.bodyParts);

                var safeBlocks = [];
                blocks.forEach(function(b) {
                    if (b.length > MESSENGER_CHUNK_MAX) {
                        safeBlocks = safeBlocks.concat(splitLongBlock(b, MESSENGER_CHUNK_MAX));
                    } else {
                        safeBlocks.push(b);
                    }
                });

                var chunks = [];
                var chunkCur = '';
                safeBlocks.forEach(function(b) {
                    var candidate = chunkCur ? chunkCur + '\\n\\n' + b : b;
                    if (candidate.length > MESSENGER_CHUNK_MAX && chunkCur) {
                        chunks.push(chunkCur);
                        chunkCur = b;
                    } else {
                        chunkCur = candidate;
                    }
                });
                if (chunkCur) chunks.push(chunkCur);

                if (chunks.length > 1) {
                    chunks = chunks.map(function(c, i) {
                        return '(' + (i + 1) + '/' + chunks.length + ')\\n' + c;
                    });
                }
                return chunks;
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
                var parts = entryTextParts(matches[current], true);
                var i = partIndex % parts.length;
                navigator.clipboard.writeText(parts[i]).then(function() {
                    showToast(parts.length > 1
                        ? 'Partie ' + (i + 1) + '/' + parts.length + ' copiee - colle-la, puis reclique pour la suite'
                        : 'Copie dans le presse-papier');
                    partIndex = (i + 1) % parts.length;
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
                var parts = entryTextParts(matches[current], false);
                var i = partIndex % parts.length;
                var text = parts[i];
                if (parts.length > 1) {
                    showToast('Partie ' + (i + 1) + '/' + parts.length + ' - partage-la, puis reclique pour la suite');
                }
                partIndex = (i + 1) % parts.length;
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
        // Delai pour laisser le navigateur finir son scroll natif vers
        // l'ancre #vN (ex. arrivee via "Continuer la lecture") avant de
        // capturer/ecraser la position - sinon on lit "haut de page" trop tot.
        setTimeout(saveReadingPosition, 150);
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
