from bs4 import BeautifulSoup
import html
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

# Nom complet francais affiche (accordeon d'accueil + <h1> de chaque page,
# guides inclus) - book_title (l'abrege ci-dessus) reste utilise tel quel
# comme cle interne (BOOK_NAME_MAP, guide_chapters_by_bom_idx...), jamais
# remplace directement, pour ne rien casser dans le matching guide<->BdM.
BOOK_TITLE_FR_FULL = {
    '1 Ne': '1 Néphi', '2 Ne': '2 Néphi', 'Jacob': 'Jacob', 'Enos': 'Énos',
    'Jarom': 'Jarom', 'Omni': 'Omni', 'W Of M': 'Paroles de Mormon',
    'Mosiah': 'Mosiah', 'Alma': 'Alma', 'Hel': 'Hélaman', '3 Ne': '3 Néphi',
    '4 Ne': '4 Néphi', 'Morm': 'Mormon', 'Ether': 'Éther', 'Moro': 'Moroni',
}


def book_display_title(title):
    return BOOK_TITLE_FR_FULL.get(title, title)


def chapter_display_title(book_title, raw_title):
    """raw_title est toujours '{book_title} Chapitre N' (source) - ne
    remplace que le prefixe abrege par le nom complet, garde le reste
    (numero de chapitre) tel quel plutot que de le reconstruire."""
    full = book_display_title(book_title)
    if full != book_title and raw_title.startswith(book_title + ' '):
        return full + raw_title[len(book_title):]
    return raw_title


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


# Le source du guide surligne des citations en rouge sous plusieurs
# notations incoherentes (annees d'edition manuelle differente) :
# <font color="#b22222">, style="color:#b22222"/"color: rgb(178, 34, 34)"
# (meme couleur, notations differentes), et des variantes de rouge/marron
# proches (maroon, #c00000, #990000, #a52a2a) - mesure sur tout le corpus
# avant de coder : l'ancienne regle CSS (font[color] uniquement) ne
# couvrait que 24 occurrences sur plus de 2900. Recolore directement les
# attributs ici plutot que d'empiler des selecteurs CSS pour chaque
# notation - une seule regle Python couvre toutes les variantes trouvees.
GUIDE_RED_FAMILY = {
    '#b22222', 'rgb(178, 34, 34)', 'rgb(178,34,34)', 'maroon',
    '#c00000', '#990000', '#a52a2a',
}
GUIDE_STYLE_COLOR_RE = re.compile(r'(?<!background-)color\s*:\s*([^;]+)', re.IGNORECASE)


def recolor_guide_citations(section_tag):
    for tag in section_tag.find_all(style=True):
        def repl(m):
            if m.group(1).strip().lower() in GUIDE_RED_FAMILY:
                return 'color: var(--guide1-color)'
            return m.group(0)
        new_style = GUIDE_STYLE_COLOR_RE.sub(repl, tag['style'])
        if new_style != tag['style']:
            tag['style'] = new_style
    for tag in section_tag.find_all('font', color=True):
        if tag['color'].strip().lower() in GUIDE_RED_FAMILY:
            del tag['color']
            existing = tag.get('style', '')
            tag['style'] = (existing + '; ' if existing else '') + 'color: var(--guide1-color)'


def guide_section_content_html(section_tag):
    """HTML interne d'une section de guide, sans son <h2> ni le lien 'back to top'."""
    h2 = section_tag.find('h2')
    if h2:
        h2.decompose()
    back_to_top = section_tag.find('a', class_='back-to-top')
    if back_to_top:
        back_to_top.decompose()
    recolor_guide_citations(section_tag)
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
# Volume "Book of Mormon Student Manual" (churchofjesuschrist.org, francais) -
# 56 pages scrapees dans book-of-mormon-student-manual/NN-slug.html (source
# publique de l'Eglise, commitee telle quelle comme les autres guides).
# Chaque entree verset est un <section><header><h2>Livre C:V . Titre</h2>
# </header><ul>...</ul></section> - le <h2> est parfois une citation seule
# sans titre, ou une citation multiple ("3:19-20 ; 5:11-14") dont seule la
# premiere est retenue comme ancre. Les sections sans citation reconnue
# (Introduction, Commentaire, Points a mediter, Idees de taches, preambule
# de livre) sont ignorees - pas de chapitre BdM unique auquel les rattacher
# proprement (un chapitre du manuel peut couvrir plusieurs chapitres/livres).
# ---------------------------------------------------------------------------

FR_TO_EN_BOOK = {BOOK_TITLE_FR_FULL[k]: v for k, v in BOOK_NAME_MAP.items()}
STUDENT_MANUAL_BOOK_ALT = '|'.join(re.escape(b) for b in sorted(FR_TO_EN_BOOK, key=len, reverse=True))
STUDENT_MANUAL_CITATION_RE = re.compile(
    rf'^({STUDENT_MANUAL_BOOK_ALT})\s+(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?'
)


def parse_student_manual_source(folder):
    soup_factory = BeautifulSoup('', 'html.parser')
    books_by_name = {}
    verse_index_by_name = {}
    seen_by_book_chapter = {}

    def get_chapter_section(book_name, chap_num):
        chapters = books_by_name.setdefault(book_name, {})
        if chap_num not in chapters:
            chapters[chap_num] = {'title': f'{book_name} {chap_num}', 'section': soup_factory.new_tag('div')}
        return chapters[chap_num]['section']

    for fname in sorted(os.listdir(folder)):
        if not fname.endswith('.html'):
            continue
        with open(os.path.join(folder, fname), 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        article = soup.find('article') or soup

        for sec in article.find_all('section'):
            header = sec.find('header', recursive=False)
            if not header:
                continue
            h2 = header.find('h2')
            if not h2:
                continue
            text = h2.get_text(' ', strip=True).replace('\xa0', ' ')
            m = STUDENT_MANUAL_CITATION_RE.match(text)
            if not m:
                continue

            book_name = FR_TO_EN_BOOK[m.group(1)]
            chap_num = int(m.group(2))
            v_start = int(m.group(3))
            v_end = int(m.group(4)) if m.group(4) else v_start
            remainder = text[m.end():].strip()
            title = remainder.lstrip('. ').strip() if remainder.startswith('.') else None

            # Chaque <li> devient un <p> AU MEME NIVEAU que les autres
            # paragraphes (jamais un <ul> imbrique) - sinon Copier/Partager
            # (qui ne separe que les enfants directs de .guide-entry) fond
            # tous les elements de la liste en un seul bloc de texte.
            body_nodes = []
            for child in list(sec.children):
                if child is header or not getattr(child, 'name', None):
                    continue
                node = child.extract()
                if node.name in ('ul', 'ol'):
                    for li in node.find_all('li', recursive=False):
                        li.name = 'p'
                        body_nodes.append(li)
                else:
                    body_nodes.append(node)
            for node in body_nodes:
                for a in node.find_all('a'):
                    a.unwrap()
                for img in node.find_all('img'):
                    img.decompose()

            dst_section = get_chapter_section(book_name, chap_num)
            key = (book_name, chap_num)
            seen = seen_by_book_chapter.setdefault(key, {})
            seen[v_start] = seen.get(v_start, 0) + 1
            n = seen[v_start]
            anchor_id = f'v{v_start}' if n == 1 else f'v{v_start}-{n}'
            wrapper = soup_factory.new_tag('div')
            wrapper['class'] = 'guide-entry'
            wrapper['id'] = anchor_id
            wrapper['data-verse-start'] = str(v_start)
            wrapper['data-verse-end'] = str(v_end)
            if title:
                head = soup_factory.new_tag('h4')
                head['class'] = 'student-manual-head'
                head.string = title
                wrapper.append(head)
            for node in body_nodes:
                wrapper.append(node)
            dst_section.append(wrapper)
            idx_key = (book_name, chap_num, v_start)
            if idx_key not in verse_index_by_name:
                verse_index_by_name[idx_key] = anchor_id

    return books_by_name, verse_index_by_name


def student_manual_section_content_html(section_tag):
    return section_tag.decode_contents()


# ---------------------------------------------------------------------------
# Volume "JWW Notes" (John W. Welch) - export Calibre generique (jww-notes/,
# meme famille que le Livre de Mormon anglais et Verse by Verse), mais SANS
# meme la classe calibre_N discriminante de ces deux-la : tout est
# <p class="calibre1">, la seule information structurelle disponible est le
# gras (<b>) - un <p> ne contenant QUE du gras ("bold-only") est un en-tete
# candidat, tout le reste est du corps de texte.
#
# Un en-tete bold-only n'est retenu comme ancre de verset QUE s'il commence
# par un nom de livre BdM reconnu (BOOK_NAME_MAP.values(), meme convention
# que les autres guides) suivi de "chapitre:verset" - tout en-tete bold-only
# qui ne matche pas (titres de section, "Further Reading", en-tetes de
# tableau comparatif, sous-decoupages internes du genre "7:10-16" sans nom de
# livre repete...) reinitialise state['current_entry'] a None, ce qui a pour
# effet de bord d'exclure AUTOMATIQUEMENT les pages hors-scope (section 1
# "Introductory Pages" en tete du livre, section 14 "Celebrating the
# Restoration"/"Easter Reflections" p.307-376) sans code de detection de
# section dedie - verifie par script qu'aucun en-tete bold-only de ces deux
# sections ne matche accidentellement le motif livre:chapitre:verset.
# Piege trouve et normalise avant matching : espaces multiples internes
# ("1  Nephi  3:3", artefact Word/InDesign), tiret Unicode non-ASCII (meme
# GUIDE2_DASH_RE que guide2/guide3), variante "I Nephi" (chiffre romain, 2
# occurrences) mappee explicitement vers "1 Nephi".
# Limite connue acceptee (rare, non corrigee au cas par cas) : de tres rares
# en-tetes entre parentheses genre "(Jacob 7:1-25)" servent de legende de
# colonne dans un tableau comparatif (3 occurrences) plutot que d'ancre de
# commentaire reel - traites comme une entree normale, le contenu qui suit
# (une cellule de tableau) devient son "commentaire", imperfection mineure
# du meme ordre que les 77 spans non apparies de guide2.
# Notes de bas de page (paragraphe commencant par le numero de la note suivi
# du texte, sans lien retour depuis le corps) fusionnees comme continuation,
# meme principe que guide3 (Verse by Verse) - le contenu est garde, seul le
# lien precis note<->numero est perdu.
# ---------------------------------------------------------------------------

JWW_BOOK_NAMES = sorted(set(BOOK_NAME_MAP.values()), key=len, reverse=True)
JWW_BOOK_PREFIX_RE = re.compile(r'^(' + '|'.join(re.escape(b) for b in JWW_BOOK_NAMES) + r')\s+(.+)$')
JWW_WHITESPACE_RE = re.compile(r'\s+')

# Source = PDF converti en HTMLZ (pas un export Calibre depuis un ebook comme
# les autres volumes) - chaque page imprimee laisse un en-tete/pied de page
# comme paragraphe ORDINAIRE (pas bold-only, donc pas filtre par la logique
# de reconnaissance d'en-tete ci-dessus) : numero de page seul ("309"),
# "N John W. Welch Notes"/"John W. Welch Notes" seul, glyphe ornemental de
# debut de page (""), et l'intitule courant du chapitre/plage repete
# sur chaque page ("Alma 8-12", parfois prefixe "2: 1 Nephi 1-7"). Sans ce
# filtre, ce bruit s'intercale au milieu du texte d'une entree (verifie en
# navigateur : "...16 John W. Welch Notes As you read..." colle en pleine
# phrase). Un vrai paragraphe de commentaire n'est jamais REDUIT a un simple
# numero ou a "Livre plage" seul, donc filtrer ces formes exactes ne perd
# aucun contenu reel.
JWW_TERMINAL_RE = re.compile(r'[.!?…][\'"’”)\]]*$')
JWW_BOOK_ALT = '|'.join(re.escape(b) for b in JWW_BOOK_NAMES)
JWW_NOISE_RE = re.compile(
    r'^\d{1,4}$'
    r'|^(\d{1,4}\s+)?John W\. Welch Notes$'
    r'|^$'
    r'|^$'
    r'|^\(.*[Cc]ontinued.*\)$'
    r'|^(?:\d+:\s*)?(?:' + JWW_BOOK_ALT + r')\s+\d+(?:[-‐-―]\d+)?$'
    r'|^(?:' + JWW_BOOK_ALT + r')(?:\s+\d+)?[-‐-―](?:' + JWW_BOOK_ALT + r')(?:\s+\d+)?$',
    re.IGNORECASE
)

def parse_jww_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')

    books_by_name = {}  # nom court -> {chapter_num: {'title', 'section' (Tag synthetique)}}
    verse_index_by_name = {}
    seen_by_book_chapter = {}

    def get_chapter_section(book_name, chap_num):
        chapters = books_by_name.setdefault(book_name, {})
        if chap_num not in chapters:
            chapters[chap_num] = {'title': f'{book_name} {chap_num}', 'section': soup.new_tag('div')}
        return chapters[chap_num]['section']

    # Source = PDF converti en HTMLZ : chaque LIGNE imprimee devient son
    # propre <p>, pas chaque paragraphe (verifie : un paragraphe de plusieurs
    # lignes se decoupe en autant de <p> que de lignes, sans marqueur fiable
    # de fin de paragraphe - une <p> vide separatrice n'est PAS un signal
    # fiable, mesure sur le corpus). Le seul signal fiable est la ponctuation
    # terminale : une ligne qui ne se termine pas par .!?... est forcement la
    # continuation de la phrase en cours (coupure de mise en page, jamais de
    # vraie fin), donc bufferisee et fusionnee avec la ligne suivante jusqu'a
    # rencontrer une ponctuation terminale - sinon chaque ligne de ~15-20 mots
    # devient un <p> isole (illisible, surtout visible sur mobile ou le
    # rendu casse plus fort entre blocs qu'en desktop).
    state = {'current_entry': None, 'buffer': None}

    def flush_buffer():
        if state['buffer'] is not None and state['current_entry'] is not None:
            state['current_entry'].append(state['buffer'])
        state['buffer'] = None

    for p in soup.find_all('p'):
        children = [c for c in p.children if getattr(c, 'name', None) or (hasattr(c, 'strip') and c.strip())]
        is_bold_only = len(children) == 1 and getattr(children[0], 'name', None) == 'b'

        if is_bold_only:
            text = JWW_WHITESPACE_RE.sub(' ', children[0].get_text(' ', strip=True)).strip()
            if text.startswith('I Nephi '):
                text = '1 Nephi ' + text[len('I Nephi '):]
            if text.startswith('(') and text.endswith(')'):
                text = text[1:-1].strip()
            text = GUIDE2_DASH_RE.sub('-', text)

            m = JWW_BOOK_PREFIX_RE.match(text)
            vm = VERSE_REF_RE.search(m.group(2)) if m else None
            if not m or ':' not in m.group(2) or not vm:
                flush_buffer()
                state['current_entry'] = None
                continue

            book_name = m.group(1)
            chap_num = int(vm.group(1))
            v_start = int(vm.group(2))
            v_end = int(vm.group(3)) if vm.group(3) else v_start
            section = get_chapter_section(book_name, chap_num)
            key = (book_name, chap_num)
            seen = seen_by_book_chapter.setdefault(key, {})
            seen[v_start] = seen.get(v_start, 0) + 1
            n = seen[v_start]
            anchor_id = f'v{v_start}' if n == 1 else f'v{v_start}-{n}'
            flush_buffer()
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
            continue

        if state['current_entry'] is None:
            continue
        body_text = JWW_WHITESPACE_RE.sub(' ', p.get_text(' ', strip=True)).strip()
        if not body_text or JWW_NOISE_RE.match(body_text):
            continue
        node = p.extract()
        for a in node.find_all('a'):
            a.unwrap()
        for img in node.find_all('img'):
            img.decompose()
        if state['buffer'] is None:
            state['buffer'] = soup.new_tag('p')
        else:
            state['buffer'].append(' ')
        for child in list(node.children):
            state['buffer'].append(child.extract())
        if JWW_TERMINAL_RE.search(body_text):
            flush_buffer()

    flush_buffer()

    return books_by_name, verse_index_by_name


def jww_section_content_html(section_tag):
    return section_tag.decode_contents()


# ---------------------------------------------------------------------------
# Volume 11 source : Book of Mormon Evidence (scripturecentral.org, API JSON)
# ---------------------------------------------------------------------------
#
# Contrairement aux guides precedents (un fichier HTML local exporte d'un
# ebook), la source ici est book-of-mormon-evidence-source/evidences.json -
# 415 articles "Evidence" recuperes via l'API JSON de scripturecentral.org
# (voir fetch_evidence_source.py), filtres a la publication sur
# volumeReferences=Book of Mormon. Chaque article peut citer des versets
# disperses sur PLUSIEURS livres/chapitres a la fois (contrairement aux
# guides precedents, localises a un seul chapitre par entree) - une meme
# entree apparait donc dupliquee sur chaque verset qu'elle cite, meme
# principe que les guides existants pousse plus loin.

EVIDENCE_BOOK_ORDER = [
    '1 Nephi', '2 Nephi', 'Jacob', 'Enos', 'Jarom', 'Omni', 'Words of Mormon',
    'Mosiah', 'Alma', 'Helaman', '3 Nephi', '4 Nephi', 'Mormon', 'Ether', 'Moroni',
]
EVIDENCE_CANONICAL_BOOKS = set(EVIDENCE_BOOK_ORDER)

EVIDENCE_CLAUSE_RE = re.compile(r'^(.*?)\s+(\d.*)$')
EVIDENCE_VERSE_RE = re.compile(r'^(\d+)(?:\s*[-–]\s*(\d+))?$')


def parse_evidence_scripture_reference(ref_text):
    """'1 Nephi 13:29; Alma 41:14-16' -> [('1 Nephi', 13, 29, 29), ('Alma', 41, 14, 16)].
    Un chapitre entier sans verset precis (ex. 'Moroni 2') donne (book, chap,
    None, None) - garde comme contenu de page mais sans signet (aucun verset
    a accrocher), meme convention que les survols de chapitre du volume
    Verse by Verse (guide3). Les references hors Livre de Mormon (Bible,
    D&C...) sont ignorees ICI SEULEMENT pour le signet - le corps de
    l'article les cite normalement en texte/lien, decision actee avec
    l'utilisateur plutot que d'exclure l'article entier."""
    results = []
    if not ref_text:
        return results
    for clause in ref_text.split(';'):
        clause = clause.strip()
        m = EVIDENCE_CLAUSE_RE.match(clause)
        if not m:
            continue
        book_name, rest = m.group(1).strip(), m.group(2).strip()
        if book_name not in EVIDENCE_CANONICAL_BOOKS:
            continue
        current_chapter = None
        for piece in rest.split(','):
            piece = piece.strip()
            if ':' in piece:
                chap_str, verse_str = piece.split(':', 1)
                if not chap_str.strip().isdigit():
                    continue
                current_chapter = int(chap_str.strip())
                vm = EVIDENCE_VERSE_RE.match(verse_str.strip())
                if vm:
                    vstart = int(vm.group(1))
                    vend = int(vm.group(2)) if vm.group(2) else vstart
                    results.append((book_name, current_chapter, vstart, vend))
            else:
                vm = EVIDENCE_VERSE_RE.match(piece)
                if not vm:
                    continue
                if current_chapter is not None:
                    vstart = int(vm.group(1))
                    vend = int(vm.group(2)) if vm.group(2) else vstart
                    results.append((book_name, current_chapter, vstart, vend))
                else:
                    results.append((book_name, int(vm.group(1)), None, None))
    return results


EVIDENCE_FOOTNOTE_ID_RE = re.compile(r'^(footnote|footnoteref)(\d+)$')
EVIDENCE_EMPTY_ANCHOR_RE = re.compile(r'^p\d+$')


def clean_evidence_body(body_html, entry_uid):
    """Parse le HTML de l'article et retourne un fragment pret a inserer.
    Deux nettoyages necessaires (aucun des guides precedents n'en avait
    besoin, source differente) :
    1. Les sections internes (Further Reading / Relevant Scriptures /
       Endnotes) utilisent class="accordion"/"accordion-content" cote
       scripturecentral.org - collision directe avec les memes classes deja
       utilisees par l'accordeon volume>livre>chapitre de CE site (CSS
       max-height:0 par defaut, .show ajoute uniquement par le clic sur
       .accordion-button) : sans ce retrait, ces sections s'afficheraient
       repliees a zero hauteur en permanence.
    2. Les ancres de notes (id="footnoteN"/"footnoterefN") sont uniques par
       ARTICLE cote source, mais une meme page de chapitre peut afficher
       plusieurs entrees (articles differents, ou le meme article cite sur
       plusieurs plages du meme chapitre) - suffixees par entry_uid pour
       rester uniques sur la page assemblee.
    """
    frag = BeautifulSoup(body_html, 'html.parser')
    for tag in frag.find_all(class_='accordion'):
        del tag['class']
    for tag in frag.find_all(class_='accordion-content'):
        del tag['class']
    for a in frag.find_all('a', id=EVIDENCE_EMPTY_ANCHOR_RE):
        if not a.get_text(strip=True) and not a.get('href'):
            a.decompose()
    # Ancre orpheline vue sur au moins un article (Evidence #198) : un
    # <div id="edn1"></div> vide juste avant le vrai
    # <div id="edn1">...Endnotes...</div> - doublon d'id jamais reference
    # (aucun href="#edn1" nulle part), probable reliquat d'edition cote
    # source. Un <div> completement vide n'est jamais du contenu utile,
    # retire quel que soit son id.
    for div in frag.find_all('div', id=True):
        if not div.contents:
            div.decompose()
    # Certains articles source ont des id="" litteraux sur leurs <li> de
    # note (bug d'origine cote scripturecentral.org, ex. Evidence #187) -
    # retire plutot que de laisser plusieurs elements partager le meme id
    # vide sur la page assemblee (HTML invalide, sans impact fonctionnel
    # puisque rien ne pointe vers ces ancres, mais autant nettoyer).
    for tag in frag.find_all(id=''):
        del tag['id']
    # Un meme article peut citer la meme note deux fois dans son propre
    # texte (id="footnoterefN" duplique cote source, ex. Evidence #73) -
    # seule la PREMIERE occurrence garde l'id brut+prefixe (ce que le lien
    # "retour au texte" de la liste de notes cible naturellement) ; les
    # occurrences suivantes recoivent un suffixe pour rester uniques sur la
    # page assemblee - rien ne pointe specifiquement vers elles, aucune
    # perte fonctionnelle.
    seen_source_ids = {}
    for tag in frag.find_all(id=EVIDENCE_FOOTNOTE_ID_RE):
        m = EVIDENCE_FOOTNOTE_ID_RE.match(tag['id'])
        n = seen_source_ids[tag['id']] = seen_source_ids.get(tag['id'], 0) + 1
        suffix = '' if n == 1 else f'_dup{n}'
        tag['id'] = f'{m.group(1)}_{entry_uid}_{m.group(2)}{suffix}'
    for a in frag.find_all('a', href=re.compile(r'^#footnote')):
        m = EVIDENCE_FOOTNOTE_ID_RE.match(a['href'][1:])
        if m:
            a['href'] = f'#{m.group(1)}_{entry_uid}_{m.group(2)}'
    return frag


def parse_evidence_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        items = json.load(file)

    books_by_name = {}
    verse_index_by_name = {}
    seen_by_book_chapter = {}
    scratch_soup = BeautifulSoup('', 'html.parser')

    def get_chapter_section(book_name, chap_num):
        chapters = books_by_name.setdefault(book_name, {})
        if chap_num not in chapters:
            chapters[chap_num] = {'title': f'{book_name} {chap_num}', 'section': scratch_soup.new_tag('div')}
        return chapters[chap_num]['section']

    for item in items:
        refs = parse_evidence_scripture_reference(item.get('scriptureReference', ''))
        if not refs:
            continue

        # Un article peut citer des dizaines de versets a la fois - dupliquer
        # son corps complet (notes, Further Reading, Relevant Scriptures) sur
        # chacun gonflait certaines pages a plus d'1 Mo (mesure : 1 Ne 1 a
        # 1,36 Mo avant ce fix). Seule la PREMIERE occurrence (le premier
        # verset cite qui a un numero de verset precis - une citation de
        # chapitre entier n'a pas d'ancre a offrir en lien) affiche le
        # contenu integral ; les occurrences suivantes n'affichent que
        # titre+resume+un lien vers cette premiere occurrence.
        primary_idx = next((i for i, r in enumerate(refs) if r[2] is not None), 0)

        occurrence_anchors = []
        for book_name, chap_num, vstart, vend in refs:
            if vstart is None:
                occurrence_anchors.append(None)
                continue
            key = (book_name, chap_num)
            seen = seen_by_book_chapter.setdefault(key, {})
            seen[vstart] = seen.get(vstart, 0) + 1
            n = seen[vstart]
            anchor_id = f'v{vstart}' if n == 1 else f'v{vstart}-{n}'
            occurrence_anchors.append(anchor_id)
            idx_key = (book_name, chap_num, vstart)
            if idx_key not in verse_index_by_name:
                verse_index_by_name[idx_key] = anchor_id

        primary_book, primary_chap = refs[primary_idx][0], refs[primary_idx][1]
        primary_book_idx = EVIDENCE_BOOK_ORDER.index(primary_book) + 1
        primary_anchor = occurrence_anchors[primary_idx]
        primary_href = f'chapter_{primary_book_idx}_{primary_chap}.html'
        if primary_anchor is not None:
            primary_href += f'#{primary_anchor}'

        for occ, (book_name, chap_num, vstart, vend) in enumerate(refs):
            wrapper = scratch_soup.new_tag('div')
            wrapper['class'] = 'guide-entry'

            head = scratch_soup.new_tag('h4')
            head['class'] = 'evidence-head'
            head.string = f"Evidence #{item['number']}: {item['title']}"
            wrapper.append(head)

            if item.get('summary'):
                abstract = scratch_soup.new_tag('p')
                abstract['class'] = 'evidence-abstract'
                em = scratch_soup.new_tag('em')
                em.string = item['summary']
                abstract.append(em)
                wrapper.append(abstract)

            if occ == primary_idx:
                entry_uid = f"e{item['number']}"
                frag = clean_evidence_body(item['body'], entry_uid)
                for child in list(frag.contents):
                    wrapper.append(child.extract())
            else:
                link_p = scratch_soup.new_tag('p')
                link_a = scratch_soup.new_tag('a', href=primary_href)
                link_a.string = "Voir l'article complet (sources et notes) ->"
                link_a['class'] = 'evidence-see-full'
                link_p.append(link_a)
                wrapper.append(link_p)

            anchor_id = occurrence_anchors[occ]
            if anchor_id is not None:
                wrapper['id'] = anchor_id
                wrapper['data-verse-start'] = str(vstart)
                wrapper['data-verse-end'] = str(vend)

            get_chapter_section(book_name, chap_num).append(wrapper)

    return books_by_name, verse_index_by_name


def evidence_section_content_html(section_tag):
    return section_tag.decode_contents()


# ---------------------------------------------------------------------------
# Volume 12 source : Book of Mormon Minute (Brant A. Gardner, 4 volumes,
# scripturecentral.org API JSON) - book-of-mormon-minute-source/chapters.json
# ---------------------------------------------------------------------------
#
# Contrairement a Book of Mormon Evidence (volume precedent, citations
# dispersees sur plusieurs chapitres), ce commentaire est verset par verset
# et localise a UN SEUL chapitre par page source (comme guide/guide2/guide3)
# - aucun probleme de duplication/poids a gerer ici. Complication propre a
# cette source : les 4 volumes utilisent DEUX gabarits HTML differents
# (verifie avant de coder) - volume 1 marque chaque section par un <h2>
# "Episode N: 1 Nephi 1:1", volumes 2-4 par un <h3> de theme suivi d'un <h4>
# "Jacob 1:1-4" contenant la vraie reference. Plutot que coder un cas par
# gabarit, un seul mecanisme generique : n'importe quel titre (h1-h6) dont le
# texte contient une reference exploitable devient une frontiere de nouvelle
# entree ; tout titre qui n'en contient pas (titre de chapitre redondant,
# "Comments", theme de section) est conserve comme sous-titre visuel a
# l'interieur de l'entree courante plutot que rejete.

BOMM_DASH = '[-–—\xad]'
# Certains titres source concatenent un trait d'union invisible (&shy;,
# U+00AD - reste du copier-coller d'origine, jamais affiche) ET un vrai
# tiret cadratin l'un derriere l'autre ("7\xad-10") - + (au lieu de ?) pour
# avaler toute la sequence, sinon la fin de plage (vend) echoue et retombe
# sur vstart, faussant a la fois la plage retiree ci-dessous et le texte
# francais complet inclus au Copier/Partager.
BOMM_FULL_REF_RE = re.compile(
    r'(' + '|'.join(re.escape(b) for b in EVIDENCE_BOOK_ORDER) + r')\s+(\d+)\s*:\s*(\d+)\s*' + BOMM_DASH + r'*\s*(\d+)?'
)
BOMM_BARE_COLON_RE = re.compile(r'(?<!\d)(\d+)\s*:\s*(\d+)\s*' + BOMM_DASH + r'*\s*(\d+)?')
BOMM_BARE_NUM_RE = re.compile(r'^\s*(\d+)\s*' + BOMM_DASH + r'*\s*(\d+)?\s*(?:Part\s*\d+)?\s*$', re.IGNORECASE)
BOMM_EPISODE_PREFIX_RE = re.compile(r'^Episode\s+\d+\s*:\s*', re.IGNORECASE)
BOMM_HEADING_RE = re.compile(r'^h[1-6]$')
BOMM_VERSE_LEAD_RE = re.compile(r'^(\d+)\s+[A-Z]')


def parse_bomm_title_book_chapter(title):
    """'1 Nephi 4' -> ('1 Nephi', 4) - donne le livre/chapitre par defaut
    d'une page, utilise quand un titre de section ne cite qu'un numero de
    verset nu, sans repeter le livre/chapitre (rare, verifie : 1 seul cas
    sur tout le corpus, 'Episode 41: 35-38' dans 1 Nephi 4)."""
    for book in EVIDENCE_BOOK_ORDER:
        if title.startswith(book + ' '):
            tail = title[len(book):].strip()
            if tail.isdigit():
                return book, int(tail)
    return None, None


def parse_bomm_heading_ref(text, page_book, page_chap):
    core = BOMM_EPISODE_PREFIX_RE.sub('', text).strip()
    m = BOMM_FULL_REF_RE.search(core)
    if m:
        vstart = int(m.group(3))
        vend = int(m.group(4)) if m.group(4) else vstart
        return m.group(1), int(m.group(2)), vstart, vend
    m = BOMM_BARE_COLON_RE.search(core)
    if m:
        vstart = int(m.group(2))
        vend = int(m.group(3)) if m.group(3) else vstart
        return page_book, int(m.group(1)), vstart, vend
    m = BOMM_BARE_NUM_RE.match(core)
    if m:
        vstart = int(m.group(1))
        vend = int(m.group(2)) if m.group(2) else vstart
        return page_book, page_chap, vstart, vend
    return None


def parse_bomm_source(path):
    with open(path, 'r', encoding='utf-8') as file:
        items = json.load(file)

    books_by_name = {}
    verse_index_by_name = {}
    seen_by_book_chapter = {}
    scratch_soup = BeautifulSoup('', 'html.parser')

    def get_chapter_section(book_name, chap_num):
        chapters = books_by_name.setdefault(book_name, {})
        if chap_num not in chapters:
            chapters[chap_num] = {'title': f'{book_name} {chap_num}', 'section': scratch_soup.new_tag('div')}
        return chapters[chap_num]['section']

    for item in items:
        page_book, page_chap = parse_bomm_title_book_chapter(item['title'])
        if page_book is None:
            continue
        frag = BeautifulSoup(item['additionalText'], 'html.parser')
        for empty_fn in frag.find_all('ul', class_='footnotes'):
            if not empty_fn.get_text(strip=True):
                empty_fn.decompose()
        # Chaque entree cite le(s) verset(s) en clair dans un <blockquote>
        # (texte anglais) - deja affiche en francais juste au-dessus via le
        # signet, ET re-prefixe en francais au Copier/Partager
        # (data-verse-text, mecanisme generique de write_guide_volume) :
        # sans ce retrait, le verset apparaissait deux fois dans le texte
        # partage. Meme raisonnement que le retrait de p.verse sur guide2.
        for bq in frag.find_all('blockquote'):
            bq.decompose()
        section = get_chapter_section(page_book, page_chap)

        state = {'entry': None, 'ref': None}

        def finalize():
            entry, ref = state['entry'], state['ref']
            if entry is None:
                return
            if not entry.contents:
                state['entry'] = None
                state['ref'] = None
                return
            if ref is not None:
                book, chap, vstart, vend = ref
                key = (book, chap)
                seen = seen_by_book_chapter.setdefault(key, {})
                seen[vstart] = seen.get(vstart, 0) + 1
                n = seen[vstart]
                anchor_id = f'v{vstart}' if n == 1 else f'v{vstart}-{n}'
                entry['id'] = anchor_id
                entry['data-verse-start'] = str(vstart)
                entry['data-verse-end'] = str(vend)
                idx_key = (book, chap, vstart)
                if idx_key not in verse_index_by_name:
                    verse_index_by_name[idx_key] = anchor_id
            section.append(entry)
            state['entry'] = None
            state['ref'] = None

        for el in list(frag.contents):
            is_heading = getattr(el, 'name', None) and BOMM_HEADING_RE.match(el.name)
            if is_heading:
                text = el.get_text(' ', strip=True)
                ref = parse_bomm_heading_ref(text, page_book, page_chap)
                if ref is not None:
                    finalize()
                    wrapper = scratch_soup.new_tag('div')
                    wrapper['class'] = 'guide-entry'
                    state['entry'] = wrapper
                    state['ref'] = ref
                    continue
                if text == item['title']:
                    continue
            if state['entry'] is None:
                wrapper = scratch_soup.new_tag('div')
                wrapper['class'] = 'guide-entry'
                state['entry'] = wrapper
                state['ref'] = None
            # Volume 1 (gabarit <h2> "Episode N:") ne met PAS le verset cite
            # dans un <blockquote> comme les volumes 2-4, mais dans un <p>
            # ordinaire commencant par son numero ("1 I, Nephi, having been
            # born...") - meme doublon avec le francais que les blockquote
            # deja retires ci-dessus. Retrait inconditionnel (pas de
            # verification contre vstart-vend de l'entree) : verifie sur le
            # corpus complet qu'un paragraphe de commentaire ne commence
            # jamais par un chiffre suivi d'une majuscule dans cette source,
            # et la plage declaree dans certains titres est elle-meme
            # incomplete (ex. "Episode 70: 1 Nephi 9:1" couvre en realite
            # les versets 1 ET 2) - se fier au numero de verset plutot qu'a
            # la plage annoncee evite ces faux negatifs.
            if getattr(el, 'name', None) == 'p':
                lead = BOMM_VERSE_LEAD_RE.match(el.get_text(' ', strip=True))
                if lead:
                    el.extract()
                    continue
            state['entry'].append(el.extract())

        finalize()

    return books_by_name, verse_index_by_name


def bomm_section_content_html(section_tag):
    return section_tag.decode_contents()


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
                            {book_display_title(book["book_title"])}
                        </button>
                        <div class="accordion-content">
                            <div class="chapter-grid">
'''
        for chap_idx, chapter in enumerate(book['chapters'], 1):
            chap_num = chapter.get('chapter_num', chap_idx)
            href = chapter_href(book_idx, chap_num, chapter)
            html += f'<a class="chapter-link" href="{href}" title="{chapter_display_title(book["book_title"], chapter["title"])}">{chap_num}</a>'
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
    + bookmark_filter_row('guide5', "Manuel de l'élève")
    + bookmark_filter_row('guide6', "ScripturePlus")
    + bookmark_filter_row('guide7', "BOM Evidence")
    + bookmark_filter_row('guide8', "BOM Minute")
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
guide_intro_items, guide_books_by_name, guide_verse_index_by_name = parse_guide_source(
    'The_Book_of_Mormon_Study_Guide/The_Book_of_Mormon_Study_Guide.html'
)
guide2_books_by_name, guide2_verse_index_by_name = parse_guide2_source(
    'book-of-mormon-study-guide-2/index.html'
)
guide3_books_by_name, guide3_verse_index_by_name = parse_vv_source(
    'verse-by-verse-book-of-mormon/index.html'
)
guide5_books_by_name, guide5_verse_index_by_name = parse_student_manual_source(
    'book-of-mormon-student-manual'
)
guide6_books_by_name, guide6_verse_index_by_name = parse_jww_source('jww-notes/index.html')
guide7_books_by_name, guide7_verse_index_by_name = parse_evidence_source('book-of-mormon-evidence-source/evidences.json')
guide8_books_by_name, guide8_verse_index_by_name = parse_bomm_source('book-of-mormon-minute-source/chapters.json')

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

# guide5 (Book of Mormon Student Manual) : meme mapping de noms que les
# autres guides - le parseur donne deja les noms courts anglais canoniques.
guide5_chapters_by_bom_idx = {}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide5_chapters_by_bom_idx[book_idx] = guide5_books_by_name.get(guide_name, {})

guide5_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide5_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide5_verse_index[(book_idx, chap_num, verse_num)] = anchor

# guide6 (JWW Notes) : meme mapping de noms que les autres guides - le
# parseur donne deja les noms courts anglais canoniques (BOOK_NAME_MAP.values()).
guide6_chapters_by_bom_idx = {}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide6_chapters_by_bom_idx[book_idx] = guide6_books_by_name.get(guide_name, {})

guide6_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide6_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide6_verse_index[(book_idx, chap_num, verse_num)] = anchor

# guide7 (Book of Mormon Evidence) : le parseur donne deja les noms courts
# anglais canoniques (BOOK_NAME_MAP.values()), meme mapping que les autres.
guide7_chapters_by_bom_idx = {}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide7_chapters_by_bom_idx[book_idx] = guide7_books_by_name.get(guide_name, {})

guide7_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide7_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide7_verse_index[(book_idx, chap_num, verse_num)] = anchor

# guide8 (Book of Mormon Minute) : meme mapping de noms que les autres.
guide8_chapters_by_bom_idx = {}
for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_name = BOOK_NAME_MAP.get(bom_book['book_title'])
    guide8_chapters_by_bom_idx[book_idx] = guide8_books_by_name.get(guide_name, {})

guide8_verse_index = {}  # (book_idx, chapter_num, verse_num) -> anchor_id
for (name, chap_num, verse_num), anchor in guide8_verse_index_by_name.items():
    book_idx = guide_name_to_bom_idx.get(name)
    if book_idx is not None:
        guide8_verse_index[(book_idx, chap_num, verse_num)] = anchor

# Repart de zero a chaque generation : les numeros de chapitre du guide ont
# des trous (livres/chapitres absents de la source), donc une ancienne
# execution peut laisser des fichiers a un chemin qui n'est plus le bon.
for d in ('chapters-fr', 'chapters-tah', 'guide', 'guide2', 'guide3', 'guide5', 'guide6', 'guide7', 'guide8'):
    shutil.rmtree(d, ignore_errors=True)
os.makedirs('chapters-fr', exist_ok=True)
os.makedirs('chapters-tah', exist_ok=True)
os.makedirs('guide/chapters', exist_ok=True)
os.makedirs('guide2/chapters', exist_ok=True)
os.makedirs('guide3/chapters', exist_ok=True)
os.makedirs('guide5/chapters', exist_ok=True)
os.makedirs('guide6/chapters', exist_ok=True)
os.makedirs('guide7/chapters', exist_ok=True)
os.makedirs('guide8/chapters', exist_ok=True)

# ---------------------------------------------------------------------------
# Cameos : section AUTONOME distincte des 8 guides verset-par-verset - fiches
# biographiques/thematiques (bookofmormonexplorer.org/cameos), pas de signet,
# pas de lien vers un verset precis. Accessible depuis l'accueil par un
# bouton dedie (icone ampoule), pas via l'accordeon volume>livre>chapitre.
# Source deja assemblee (cameos-source/cameos.json) : le site d'origine est
# une SPA React sans rendu serveur, mais tout le contenu (index + texte
# d'analyse) est integre statiquement dans son bundle JS - extrait par
# script plutot que par navigation page a page (voir memoire du projet).
# ---------------------------------------------------------------------------

CAMEO_CATEGORIES = (
    ('major_speakers', 'major-speakers', 'Major Speakers', "Ceux qui ont écrit l'essentiel du Livre de Mormon."),
    ('minor_speakers', 'minor-speakers', 'Minor Speakers', "Des voix plus brèves, mais marquantes."),
    ('concepts', 'concepts', 'Concepts', "Des thèmes et expressions récurrents à travers le texte."),
    ('influences', 'influences', 'Influences', "Des liens textuels entre les auteurs du Livre de Mormon."),
)


def cameo_clean_field(value):
    """Certains champs de la source (ex. le nom d'une entree) contiennent du
    HTML brut (un lien vers churchofjesuschrist.org) - reduit au texte seul
    pour rester simple (demande explicite), puis echappe pour reinsertion
    sans danger dans notre propre HTML."""
    if not value:
        return ''
    if '<' in value:
        value = BeautifulSoup(value, 'html.parser').get_text(' ', strip=True)
    return html.escape(value)


def cameo_render_paragraphs(text):
    """La description (contrairement au texte d'analyse, deja extrait en
    texte pur) peut contenir des liens HTML bruts vers churchofjesuschrist.org
    - reduits au texte seul comme les autres champs (demande explicite de
    contenu simplifie), sinon les balises s'affichaient echappees en clair."""
    if not text:
        return ''
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    cleaned = []
    for p in parts:
        if '<' in p:
            p = BeautifulSoup(p, 'html.parser').get_text(' ', strip=True)
            # get_text(' ', ...) insere un espace la ou une balise de lien
            # retiree se trouvait, laissant "( X )" au lieu de "(X)".
            p = re.sub(r'\(\s+', '(', p)
            p = re.sub(r'\s+\)', ')', p)
            p = re.sub(r' +([,.;:!?])', r'\1', p)
        cleaned.append(p)
    return ''.join(f'<p>{html.escape(p)}</p>' for p in cleaned)


def cameo_render_entry(entry):
    """Une entree top-level (personne/concept) peut avoir plusieurs
    sous-articles (entry['data']) - chacun devient une section, avec un
    sous-titre uniquement si son nom differe du titre principal (evite de
    repeter "Nephi, Son of Lehi" en sous-titre de sa propre bio)."""
    out = []
    for sub in entry['data']:
        name = cameo_clean_field(sub.get('name', ''))
        if name and name != cameo_clean_field(entry['name']):
            out.append(f'<h2 class="cameo-subheading">{name}</h2>')
        if sub.get('year'):
            out.append(f'<p class="cameo-meta">{html.escape(sub["year"])}</p>')
        if sub.get('description'):
            out.append(f'<div class="cameo-description">{cameo_render_paragraphs(sub["description"])}</div>')
        fact_1 = cameo_clean_field(sub.get('fact_1', ''))
        if fact_1:
            out.append(f'<p class="cameo-fact">💡 {fact_1}</p>')
        if sub.get('analysis_1'):
            out.append(f'<div class="cameo-analysis">{cameo_render_paragraphs(sub["analysis_1"])}</div>')
        # "fact_2" est parfois juste le libelle du bouton source ("Read
        # more...") plutot qu'un vrai fait - n'affiche le bandeau que si ce
        # n'est pas ce cas precis, mais garde toujours l'analyse qui suit.
        fact_2 = cameo_clean_field(sub.get('fact_2', ''))
        if fact_2 and fact_2 != 'Read more...':
            out.append(f'<p class="cameo-fact">💡 {fact_2}</p>')
        if sub.get('analysis_2'):
            out.append(f'<div class="cameo-analysis">{cameo_render_paragraphs(sub["analysis_2"])}</div>')
    return ''.join(out)


def write_cameos(source_path):
    with open(source_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    shutil.rmtree('cameos', ignore_errors=True)
    os.makedirs('cameos', exist_ok=True)

    category_tiles = ''
    for key, folder, label, blurb in CAMEO_CATEGORIES:
        os.makedirs(f'cameos/{folder}', exist_ok=True)
        entries = data[key]

        grid_tiles = ''
        for entry in entries:
            name = cameo_clean_field(entry['name'])
            grid_tiles += f'<a class="cameo-tile" href="{folder}/{entry["link"]}.html">{name}</a>'

        cat_html = PAGE_HEAD.format(title=label, styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL)
        cat_html += f'    <p class="cameo-back"><a href="../cameos.html">← Book of Mormon Voices</a></p>\n'
        cat_html += f'    <h1>{label}</h1>\n'
        cat_html += f'    <p class="cameo-intro">{blurb}</p>\n'
        cat_html += f'    <div class="cameo-grid">{grid_tiles}</div>\n'
        cat_html += PAGE_TAIL
        write(f'cameos/{folder}.html', cat_html)

        for entry in entries:
            detail_html = PAGE_HEAD.format(title=cameo_clean_field(entry['name']), styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls=TEXT_SIZE_CONTROL)
            detail_html += f'    <p class="cameo-back"><a href="../{folder}.html">← {label}</a></p>\n'
            detail_html += f'    <h1>{cameo_clean_field(entry["name"])}</h1>\n'
            detail_html += f'<div class="cameo-content">{cameo_render_entry(entry)}</div>'
            detail_html += PAGE_TAIL
            write(f'cameos/{folder}/{entry["link"]}.html', detail_html)

        category_tiles += (
            f'<a class="cameo-category-tile" href="cameos/{folder}.html">'
            f'<h3>{label}</h3><p>{blurb}</p></a>'
        )

    landing_html = PAGE_HEAD.format(title='Book of Mormon Voices', styles_href='styles.css', script_href='script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL)
    landing_html += '    <p class="cameo-back"><a href="index.html">← Bibliothèque</a></p>\n'
    landing_html += '    <h1>Book of Mormon Voices</h1>\n'
    landing_html += '    <p class="cameo-intro">Analyses stylométriques des personnages et des thèmes du Livre de Mormon.</p>\n'
    landing_html += f'    <div class="cameo-category-grid">{category_tiles}</div>\n'
    landing_html += PAGE_TAIL
    write('cameos.html', landing_html)

    total_entries = sum(len(data[key]) for key, _, _, _ in CAMEO_CATEGORIES)
    print(f'Cameos : {total_entries} fiches sur {len(CAMEO_CATEGORIES)} categories.')


write_cameos('cameos-source/cameos.json')

# --- index.html : bibliotheque -----------------------------------------
#
# N'affiche que le Livre de Mormon francais et tahitien - les 3 guides
# d'etude restent generes et pleinement fonctionnels (accessibles via les
# signets francais et par lien direct), seule leur entree dans cette liste
# a ete retiree sur demande explicite. Le bilingue/l'anglais/la Conference
# ont ete supprimes completement (plus de generation du tout, voir plus bas).

toc_html = PAGE_HEAD.format(title='Bibliotheque - Table des matieres', styles_href='styles.css', script_href='script.js', lang='fr', extra_controls='')
toc_html += '        <h1>Bibliotheque</h1>\n'
toc_html += '        <div id="continue-reading-slot"></div>\n'

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

toc_html += '''
        <a class="cameo-home-button" href="cameos.html">
            <span class="cameo-home-icon" aria-hidden="true">💡</span>
            <span>Book of Mormon Voices</span>
        </a>
'''

toc_html += PAGE_TAIL
write('index.html', toc_html)

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
            anchor5 = guide5_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor5:
                guide5_link = f'../guide5/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor5}'
                verses_html += bookmark_link(guide5_link, 'guide5', "Voir le commentaire du Manuel de l'eleve")
            anchor6 = guide6_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor6:
                guide6_link = f'../guide6/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor6}'
                verses_html += bookmark_link(guide6_link, 'guide6', "Voir le commentaire ScripturePlus")
            anchor7 = guide7_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor7:
                guide7_link = f'../guide7/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor7}'
                verses_html += bookmark_link(guide7_link, 'guide7', "Voir BOM Evidence")
            anchor8 = guide8_verse_index.get((book_idx, chap_idx, verse_num))
            if anchor8:
                guide8_link = f'../guide8/chapters/chapter_{book_idx}_{chap_idx}.html#{anchor8}'
                verses_html += bookmark_link(guide8_link, 'guide8', "Voir BOM Minute")
            verses_html += '</p>'

        introduction_html = ''
        if chapter['introduction']:
            introduction_html = f'<p class="verse-fr introduction">{chapter["introduction"]["francais"]}</p>'

        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''

        display_chapter_title = chapter_display_title(book['book_title'], chapter['title'])
        html = PAGE_HEAD.format(title=display_chapter_title, styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL + BOOKMARK_FILTER_CONTROL)
        html += f'    <h2 class="chapter-title">Chapitre {chap_idx}</h2>\n'
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

        display_chapter_title = chapter_display_title(book['book_title'], chapter['title'])
        html = PAGE_HEAD.format(title=display_chapter_title, styles_href='../styles.css', script_href='../script.js', lang='ty', extra_controls=TEXT_SIZE_CONTROL)
        html += f'    <h2 class="chapter-title">Chapitre {chap_idx}</h2>\n'
        html += f'<div class="verses-tah" data-volume-key="tahitian" data-volume-title="Livre de Mormon (tahitien)">'
        html += verses_html + introduction_html
        html += '</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../index.html')
        html += PAGE_TAIL

        write(f'chapters-tah/chapter_{book_idx}_{chap_idx}.html', html)

def write_guide_volume(chapters_by_bom_idx, folder, volume_key, volume_title, content_fn, lang='en'):
    """Genere les pages chapitre d'un volume de commentaire lie au Livre de
    Mormon chapitre par chapitre (guide/guide2/guide3, et tout futur volume du
    meme genre). Chapitre precedent/suivant navigue TOUJOURS sur le chapitre
    reel du Livre de Mormon (+1/-1) - y compris vers un chapitre sans
    commentaire dans CE volume (page generee quand meme, sans entree) -
    jamais vers "le prochain chapitre qui a du commentaire", qui restait
    coince a l'interieur du guide et ignorait le Livre de Mormon lui-meme.
    """
    for book_idx, bom_book in enumerate(bom_book_data, 1):
        chapters = chapters_by_bom_idx[book_idx]
        if not chapters:
            continue
        full_book_name = BOOK_NAME_MAP.get(bom_book['book_title'], bom_book['book_title'])
        total_chapters = len(bom_book['chapters'])
        for chap_idx in range(1, total_chapters + 1):
            chapter = chapters.get(chap_idx)
            if chapter is not None:
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
                                  f"(entree {volume_key} {vstart}-{vend}) - Copier/Partager n'inclura pas ce verset.")
                    if pieces:
                        ref = f'{chap_idx}:{vstart}' if vstart == vend else f'{chap_idx}:{vstart}-{vend}'
                        entry['data-verse-ref'] = f'{full_book_name} {ref}'
                        entry['data-verse-text'] = '\n\n'.join(pieces)
                content_html = content_fn(chapter['section'])
                title = chapter['title']
            else:
                content_html = '<p class="guide-empty">Aucun commentaire pour ce chapitre dans ce guide.</p>'
                title = f'{full_book_name} {chap_idx}'

            has_prev = chap_idx > 1
            has_next = chap_idx < total_chapters
            prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if has_prev else ''
            next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if has_next else ''

            html = PAGE_HEAD.format(title=title, styles_href='../../styles.css', script_href='../../script.js', lang=lang, extra_controls=TEXT_SIZE_CONTROL)
            html += f'    <h1>{book_display_title(bom_book["book_title"])}</h1>\n    <h2>{title}</h2>\n'
            html += f'<div class="guide-content" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}" data-volume-key="{volume_key}" data-volume-title="{volume_title}">{content_html}</div>'
            html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
            html += PAGE_TAIL

            write(f'{folder}/chapters/chapter_{book_idx}_{chap_idx}.html', html)

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

write_guide_volume(guide_chapters_by_bom_idx, 'guide', 'guide', 'Book of Mormon Study Guide', guide_section_content_html)

# --- Volume 6 : Book of Mormon Study Guide (Start to Finish) ----------------

write_guide_volume(guide2_chapters_by_bom_idx, 'guide2', 'guide2', 'Book of Mormon Study Guide (Start to Finish)', guide2_section_content_html)

# --- Volume 7 : Verse by Verse Book of Mormon --------------------------------

write_guide_volume(guide3_chapters_by_bom_idx, 'guide3', 'guide3', 'Verse by Verse Book of Mormon', vv_section_content_html)
write_guide_volume(guide5_chapters_by_bom_idx, 'guide5', 'guide5', "Book of Mormon Student Manual", student_manual_section_content_html, lang='fr')
write_guide_volume(guide6_chapters_by_bom_idx, 'guide6', 'guide6', 'ScripturePlus', jww_section_content_html)
write_guide_volume(guide7_chapters_by_bom_idx, 'guide7', 'guide7', 'BOM Evidence', evidence_section_content_html)
write_guide_volume(guide8_chapters_by_bom_idx, 'guide8', 'guide8', 'BOM Minute', bomm_section_content_html)

guide_chapter_count = sum(len(c) for c in guide_chapters_by_bom_idx.values())
guide2_chapter_count = sum(len(c) for c in guide2_chapters_by_bom_idx.values())
guide3_chapter_count = sum(len(c) for c in guide3_chapters_by_bom_idx.values())
guide5_chapter_count = sum(len(c) for c in guide5_chapters_by_bom_idx.values())
guide6_chapter_count = sum(len(c) for c in guide6_chapters_by_bom_idx.values())
guide7_chapter_count = sum(len(c) for c in guide7_chapters_by_bom_idx.values())
guide8_chapter_count = sum(len(c) for c in guide8_chapters_by_bom_idx.values())
print(f'{sum(len(b["chapters"]) for b in bom_book_data)} chapitres LoM, '
      f'{guide_chapter_count} chapitres guide, '
      f'{len(guide_intro_items)} pages intro, '
      f'{len(guide_verse_index)} versets avec signet guide. '
      f'{guide2_chapter_count} chapitres guide2, '
      f'{len(guide2_verse_index)} versets avec signet guide2. '
      f'{guide3_chapter_count} chapitres guide3, '
      f'{len(guide3_verse_index)} versets avec signet guide3. '
      f'{guide5_chapter_count} chapitres guide5, '
      f'{len(guide5_verse_index)} versets avec signet guide5. '
      f'{guide6_chapter_count} chapitres guide6, '
      f'{len(guide6_verse_index)} versets avec signet guide6. '
      f'{guide7_chapter_count} chapitres guide7, '
      f'{len(guide7_verse_index)} versets avec signet guide7. '
      f'{guide8_chapter_count} chapitres guide8, '
      f'{len(guide8_verse_index)} versets avec signet guide8.')

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
    --guide1-color: #d4a017;
    --guide2-color: #b22222;
    --guide3-color: #1e6fd9;
    --guide5-color: #2f9e44;
    --guide6-color: #7c3aed;
    --guide7-color: #f76707;
    --guide8-color: #0ca678;
    --cameo-accent: #b8860b;
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
        --guide1-color: #ffd43b;
        --guide2-color: #ff6b6b;
        --guide3-color: #4dabf7;
    --guide5-color: #51cf66;
    --guide6-color: #9775fa;
    --guide7-color: #ffa94d;
    --guide8-color: #20c997;
    --cameo-accent: #f0c454;
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
    --guide1-color: #ffd43b;
    --guide2-color: #ff6b6b;
    --guide3-color: #4dabf7;
    --guide5-color: #51cf66;
    --guide6-color: #9775fa;
    --guide7-color: #ffa94d;
    --guide8-color: #20c997;
    --cameo-accent: #f0c454;
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

/* Centre ("Chapitre N" seul, sans nom de livre) - un texte centre n'est pas
   protege par le padding-right de h1 (fonctionne seulement pour du texte
   aligne a gauche), donc une vraie marge haute degage la rangee de boutons
   .page-controls (position absolute, meme sommet du flux que ce titre). */
.chapter-title {
    margin: 52px 0 16px;
    font-size: 22px;
    text-align: center;
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

/* Cameos : section autonome, identite visuelle propre (pas les couleurs de
   signet des guides, qui n'ont pas de sens ici puisque rien n'est relie a
   un verset). Cartes/tuiles plutot que la lecture continue des guides. */
.cameo-home-button {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 24px;
    padding: 16px 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    text-decoration: none;
    color: var(--text);
    font-weight: 600;
    font-size: 16px;
    transition: border-color 0.15s, background 0.15s;
}

.cameo-home-button:hover,
.cameo-home-button:focus-visible {
    border-color: var(--cameo-accent);
    background: var(--hover-bg);
}

.cameo-home-icon {
    font-size: 22px;
    line-height: 1;
}

.cameo-back {
    margin-bottom: 1em;
}

.cameo-back a {
    color: var(--text-muted);
    text-decoration: none;
    font-size: 14px;
}

.cameo-back a:hover {
    color: var(--accent);
}

.cameo-intro {
    color: var(--text-muted);
    margin-bottom: 1.6em;
    max-width: 60ch;
}

.cameo-category-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
}

.cameo-category-tile {
    display: block;
    padding: 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    text-decoration: none;
    color: var(--text);
    transition: border-color 0.15s, transform 0.1s;
}

.cameo-category-tile:hover,
.cameo-category-tile:focus-visible {
    border-color: var(--cameo-accent);
}

.cameo-category-tile h3 {
    margin: 0 0 6px;
    color: var(--cameo-accent);
    font-size: 18px;
}

.cameo-category-tile p {
    margin: 0;
    color: var(--text-muted);
    font-size: 14px;
}

.cameo-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px;
}

.cameo-tile {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 14px 10px;
    min-height: 56px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    text-decoration: none;
    color: var(--text);
    font-size: 14px;
    font-weight: 500;
}

.cameo-tile:hover,
.cameo-tile:focus-visible {
    border-color: var(--cameo-accent);
    color: var(--cameo-accent);
}

.cameo-content {
    max-width: 68ch;
}

.cameo-content .cameo-subheading {
    margin: 1.8em 0 0.6em;
    padding-top: 1.2em;
    border-top: 1px solid var(--border);
    font-size: 19px;
    color: var(--text);
}

.cameo-content .cameo-subheading:first-child {
    margin-top: 0;
    padding-top: 0;
    border-top: none;
}

.cameo-meta {
    color: var(--text-muted);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 0.8em;
}

.cameo-description p,
.cameo-analysis p {
    margin: 0.7em 0;
    line-height: 1.65;
    font-size: var(--reading-font-size);
}

.cameo-fact {
    margin: 1em 0;
    padding: 12px 14px;
    background: var(--intro-bg);
    border-left: 3px solid var(--cameo-accent);
    border-radius: 0 8px 8px 0;
    font-size: var(--reading-font-size);
    line-height: 1.5;
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
.bookmark-guide { color: var(--guide1-color); }
.bookmark-guide2 { color: var(--guide2-color); }
.bookmark-guide3 { color: var(--guide3-color); }
.bookmark-guide5 { color: var(--guide5-color); }
.bookmark-guide6 { color: var(--guide6-color); }
.bookmark-guide7 { color: var(--guide7-color); }
.bookmark-guide8 { color: var(--guide8-color); }

html[data-hide-bookmark-guide] .bookmark-guide { display: none; }
html[data-hide-bookmark-guide2] .bookmark-guide2 { display: none; }
html[data-hide-bookmark-guide3] .bookmark-guide3 { display: none; }
html[data-hide-bookmark-guide5] .bookmark-guide5 { display: none; }
html[data-hide-bookmark-guide6] .bookmark-guide6 { display: none; }
html[data-hide-bookmark-guide7] .bookmark-guide7 { display: none; }
html[data-hide-bookmark-guide8] .bookmark-guide8 { display: none; }

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
    color: var(--guide2-color);
    font-weight: bold;
}

.guide-content h4.student-manual-head {
    color: var(--guide5-color);
    font-weight: bold;
    margin-bottom: 0.4em;
}

.guide-content h4.evidence-head {
    color: var(--guide7-color);
    font-weight: bold;
    margin-bottom: 0.4em;
}

.guide-content p.evidence-abstract {
    color: var(--text-muted);
    font-style: italic;
}

.guide-content figure {
    margin: 1em 0;
}

.guide-content img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
}

.guide-content figcaption {
    font-size: 13px;
    color: var(--text-muted);
    text-align: center;
    margin-top: 0.4em;
}

.guide-content ul.footnotes {
    list-style: none;
    padding-left: 0;
    margin-top: 1.5em;
    padding-top: 1em;
    border-top: 1px solid var(--border);
    font-size: 13px;
    color: var(--text-muted);
}

.guide-content ul.footnotes li {
    margin-bottom: 0.6em;
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

.entry-card-actions button.refs-toggle-btn {
    position: relative;
    font-size: 15px;
    letter-spacing: 0.02em;
}

.entry-card-actions button.refs-toggle-btn.active {
    color: var(--text-faint);
}

.entry-card-actions button.refs-toggle-btn.active::after {
    content: '';
    position: absolute;
    left: 18%;
    right: 18%;
    top: 50%;
    height: 2px;
    background: currentColor;
    transform: rotate(-12deg);
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

/* Gospel Doctrine (data-volume-key="guide") : ses <h4> viennent tels quels
   de la source (titres de citation) et suivaient jusqu'ici le bleu generique
   .guide-content h4 au lieu de la couleur de son propre signet - l'attribut
   ajoute juste assez de specificite pour gagner sur la regle generique
   ci-dessus sans toucher aux autres guides (guide2 a deja sa
   propre classe plus specifique, guide3 n'utilise pas de <h4>). */
.guide-content[data-volume-key="guide"] h4 {
    color: var(--guide1-color);
}

/* La source Gospel Doctrine surligne des extraits de versets en rouge
   (<font color="#b22222">, code d'origine) - recolore en or pour rester
   fidele a la couleur du signet de CE guide plutot que le rouge de
   Start to Finish, qui n'avait ete choisi que par coincidence avec ce
   rouge deja present dans cette source (voir .commentary-head). */
.guide-content[data-volume-key="guide"] font[color] {
    color: var(--guide1-color) !important;
}

.guide-content p {
    margin: 0.7em 0;
    line-height: 1.6;
    font-size: var(--reading-font-size);
}

.guide-content p.Indent1,
.guide-content [style*="margin-left"],
.guide-content blockquote {
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

            // Retire les references entre parentheses du corps du texte
            // ("(voir 1 Nephi 2:16)", "(Ensign, oct. 2011, p. 43)"...) -
            // option de partage uniquement (jamais Copier), non recursif
            // mais suffisant : les parentheses de ce contenu ne s'embrouillent
            // jamais entre elles (verifie sur le Student Manual).
            function stripParenRefs(text) {
                return text.replace(/\\s*\\([^()]*\\)/g, '').replace(/[ \\t]{2,}/g, ' ').trim();
            }

            // Un message Messenger au-dela d'un certain nombre de caracteres
            // est coupe automatiquement par Messenger. Non documentee
            // officiellement, mais mesuree empiriquement par l'utilisateur :
            // un message de 5000 caracteres exactement est coupe en plein mot
            // pile a cette limite (teste en conditions reelles, 2026-08-14) -
            // marge de securite retenue pour le prefixe "(x/y)" ajoute a
            // chaque morceau. Le texte est decoupe en plusieurs messages a
            // envoyer a la suite plutot que risquer une troncature silencieuse.
            var MESSENGER_CHUNK_MAX = 4900;

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

            function entryBlocks(entry, underlineNotesLabel, stripRefs) {
                var p = entryParts(entry);
                var notesLabel = underlineNotesLabel ? underline('Notes du guide') : 'Notes du guide';
                var bodyParts = stripRefs ? p.bodyParts.map(stripParenRefs) : p.bodyParts;

                var blocks = [todayLong()];
                if (p.verseRef && p.verseText) {
                    blocks.push(p.verseRef);
                    blocks.push(p.verseText);
                    blocks.push(notesLabel);
                }
                return blocks.concat(bodyParts);
            }

            // Copier : texte integral, jamais decoupe (destination inconnue
            // - Notes, email... pas forcement Messenger), jamais de retrait
            // de reference non plus (ce toggle n'existe que sur Partager).
            function entryFullText(entry, underlineNotesLabel) {
                return entryBlocks(entry, underlineNotesLabel, false).join('\\n\\n');
            }

            // Partager : decoupe en plusieurs messages, uniquement pour ne
            // jamais depasser la limite Messenger (voir MESSENGER_CHUNK_MAX).
            function entryTextParts(entry, underlineNotesLabel, stripRefs) {
                var blocks = entryBlocks(entry, underlineNotesLabel, stripRefs);

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
                navigator.clipboard.writeText(entryFullText(matches[current], true)).then(function() {
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
                var parts = entryTextParts(matches[current], false, refsHidden());
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

            // Interrupteur persistant : retire les references entre
            // parentheses du corps du texte au moment de Partager
            // uniquement (jamais Copier). Etat garde en localStorage,
            // comme les autres reglages du site (taille de texte, signets).
            var REFS_HIDE_KEY = 'bukaAMoromona:hideRefsOnShare';
            function refsHidden() { return localStorage.getItem(REFS_HIDE_KEY) === '1'; }

            var refsToggleBtn = document.createElement('button');
            refsToggleBtn.type = 'button';
            refsToggleBtn.className = 'refs-toggle-btn';
            refsToggleBtn.textContent = '(…)';
            function updateRefsToggleUI() {
                var hidden = refsHidden();
                refsToggleBtn.setAttribute('aria-pressed', hidden ? 'true' : 'false');
                refsToggleBtn.classList.toggle('active', hidden);
                refsToggleBtn.title = hidden
                    ? 'Références (...) masquées au partage - cliquer pour les remettre'
                    : 'Masquer les références (...) au partage';
            }
            refsToggleBtn.addEventListener('click', function() {
                if (refsHidden()) localStorage.removeItem(REFS_HIDE_KEY);
                else localStorage.setItem(REFS_HIDE_KEY, '1');
                updateRefsToggleUI();
            });
            updateRefsToggleUI();

            actionsRow.appendChild(copyBtn);
            actionsRow.appendChild(shareBtn);
            actionsRow.appendChild(refsToggleBtn);
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

                // Arrive via signet = simple consultation ponctuelle d'un
                // verset, pas un parcours du guide lui-meme : Precedent/
                // Suivant doit continuer la LECTURE du Livre de Mormon
                // francais (chapitre reel +-1), jamais rester dans le guide
                // en mode "liste complete" du chapitre voisin.
                [].slice.call(nav.querySelectorAll('a')).forEach(function(a) {
                    var m = a.getAttribute('href').match(/^chapter_(\d+)_(\d+)\.html$/);
                    if (!m) return;
                    a.href = '../../chapters-fr/chapter_' + m[1] + '_' + m[2] + '.html';
                });
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
        // Seuls francais/tahitien sont listes sur la page d'accueil - un
        // Continuer vers un volume retire de l'accordeon (guides, etc.)
        // n'a pas de sens ici.
        var HOME_VOLUME_KEYS = ['french', 'tahitian'];
        var savedAll = {};
        try { savedAll = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {}; } catch (e) {}
        Object.keys(savedAll).forEach(function(key) {
            if (HOME_VOLUME_KEYS.indexOf(key) === -1) return;
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
# continuer a servir un ancien script.js/styles.css en cache apres un
# deploy, donnant l'impression qu'un fix ne "marche pas" alors qu'il est
# bien en ligne. Version = hash du contenu, ajoutee en ?v= sur toutes les
# pages generees. styles.css n'avait jamais ce traitement (seul script.js
# l'avait) - ajoute le 2026-08-16 apres qu'un fix de couleur CSS soit reste
# invisible chez l'utilisateur a cause du cache navigateur.
import hashlib
script_version = hashlib.md5(js_content.encode('utf-8')).hexdigest()[:8]
css_version = hashlib.md5(css_content.encode('utf-8')).hexdigest()[:8]
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d != '.git']
    for fname in files:
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content.replace('script.js"', f'script.js?v={script_version}"')
        new_content = new_content.replace('styles.css"', f'styles.css?v={css_version}"')
        if new_content != content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
