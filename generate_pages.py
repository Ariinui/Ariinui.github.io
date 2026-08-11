from bs4 import BeautifulSoup
import os
import re
import shutil

VERSE_REF_RE = re.compile(r'(\d+)\s*:\s*(\d+)')


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
                seen[(h4_chap, h4_verse)] = seen.get((h4_chap, h4_verse), 0) + 1
                n = seen[(h4_chap, h4_verse)]
                anchor_id = f'v{h4_verse}' if n == 1 else f'v{h4_verse}-{n}'

                wrapper = soup.new_tag('div')
                wrapper['class'] = 'guide-entry'
                wrapper['id'] = anchor_id
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
            <button class="text-size-toggle" type="button" aria-label="Taille du texte">A</button>
            <div class="text-size-modal" id="text-size-modal" hidden>
                <div class="text-size-modal-inner">
                    <button type="button" class="text-size-option" data-size="normal" aria-label="Texte normal">a</button>
                    <button type="button" class="text-size-option text-size-option-large" data-size="large" aria-label="Grand texte">A</button>
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
guide_intro_items, guide_books_by_name, guide_verse_index_by_name = parse_guide_source(
    'The_Book_of_Mormon_Study_Guide/The_Book_of_Mormon_Study_Guide.html'
)

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
for d in ('chapters', 'chapters-fr', 'guide'):
    shutil.rmtree(d, ignore_errors=True)
os.makedirs('chapters', exist_ok=True)
os.makedirs('chapters-fr', exist_ok=True)
os.makedirs('guide/chapters', exist_ok=True)

# --- index.html : bibliotheque a 3 volumes ---------------------------------

toc_html = PAGE_HEAD.format(title='Bibliotheque - Table des matieres', styles_href='styles.css', script_href='script.js', lang='fr', extra_controls=TEXT_SIZE_CONTROL)
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

toc_html += PAGE_TAIL
write('index.html', toc_html)

# --- Volume 1 : chapitres tahitien/francais (inchange) ----------------------

for book_idx, book in enumerate(bom_book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        verses_html = ''
        for verse in chapter['verses']:
            verses_html += '<div class="verse-container">'
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

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls='')
        html += f'    <h1>{book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += verses_html + introduction_html
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

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../styles.css', script_href='../script.js', lang='fr', extra_controls='')
        html += f'    <h1>{book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="verses-fr" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}">'
        html += verses_html + introduction_html
        html += '</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../index.html')
        html += PAGE_TAIL

        write(f'chapters-fr/chapter_{book_idx}_{chap_idx}.html', html)

# --- Volume 3 : Book of Mormon Study Guide ----------------------------------

for n, item in enumerate(guide_intro_items, 1):
    content_html = guide_section_content_html(item['section'])
    prev_link = f'<a href="intro_{n-1}.html">Page precedente</a> | ' if n > 1 else ''
    next_link = f'<a href="intro_{n+1}.html">Page suivante</a> | ' if n < len(guide_intro_items) else ''

    html = PAGE_HEAD.format(title=item['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls='')
    html += f'    <h1>Introductory Pages</h1>\n    <h2>{item["title"]}</h2>\n'
    html += f'<div class="guide-content">{content_html}</div>'
    html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
    html += PAGE_TAIL

    write(f'guide/chapters/intro_{n}.html', html)

for book_idx, bom_book in enumerate(bom_book_data, 1):
    guide_chapters = guide_chapters_by_bom_idx[book_idx]
    chapter_nums = sorted(guide_chapters.keys())
    for chap_idx in chapter_nums:
        chapter = guide_chapters[chap_idx]
        content_html = guide_section_content_html(chapter['section'])
        has_prev = chapter_nums.index(chap_idx) > 0
        has_next = chapter_nums.index(chap_idx) < len(chapter_nums) - 1
        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre precedent</a> | ' if has_prev else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if has_next else ''

        html = PAGE_HEAD.format(title=chapter['title'], styles_href='../../styles.css', script_href='../../script.js', lang='en', extra_controls='')
        html += f'    <h1>{bom_book["book_title"]}</h1>\n    <h2>{chapter["title"]}</h2>\n'
        html += f'<div class="guide-content" data-book-idx="{book_idx}" data-chapter-idx="{chap_idx}">{content_html}</div>'
        html += CHAPTER_NAV.format(prev_link=prev_link, next_link=next_link, index_href='../../index.html')
        html += PAGE_TAIL

        write(f'guide/chapters/chapter_{book_idx}_{chap_idx}.html', html)

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

:root[data-text-size="large"] {
    --reading-font-size: 20px;
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

.text-size-modal {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}

.text-size-modal[hidden] {
    display: none;
}

.text-size-modal-inner {
    display: flex;
    gap: 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
}

.text-size-option {
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    cursor: pointer;
    font-weight: 600;
    font-size: 18px;
}

.text-size-option-large {
    font-size: 32px;
}

.text-size-option.active {
    border-color: var(--accent);
    color: var(--accent);
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

.guide-content h4 {
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
    if (storedSize === 'large') {
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
    var textSizeModal = document.getElementById('text-size-modal');
    if (textSizeToggle && textSizeModal) {
        var options = [].slice.call(textSizeModal.querySelectorAll('.text-size-option'));
        var markActive = function() {
            var current = document.documentElement.getAttribute('data-text-size') === 'large' ? 'large' : 'normal';
            options.forEach(function(opt) {
                opt.classList.toggle('active', opt.getAttribute('data-size') === current);
            });
        };
        markActive();
        textSizeToggle.addEventListener('click', function() {
            markActive();
            textSizeModal.hidden = false;
        });
        textSizeModal.addEventListener('click', function(event) {
            if (event.target === textSizeModal) textSizeModal.hidden = true;
        });
        options.forEach(function(opt) {
            opt.addEventListener('click', function() {
                var size = opt.getAttribute('data-size');
                if (size === 'large') {
                    localStorage.setItem('bukaAMoromona:textSize', 'large');
                    document.documentElement.setAttribute('data-text-size', 'large');
                } else {
                    localStorage.removeItem('bukaAMoromona:textSize');
                    document.documentElement.removeAttribute('data-text-size');
                }
                markActive();
                textSizeModal.hidden = true;
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

            function entryText(entry) {
                var h4 = entry.querySelector('h4');
                var title = h4 ? h4.textContent.trim() : '';
                var bodyParts = [];
                [].slice.call(entry.children).forEach(function(child) {
                    if (child !== h4) {
                        var t = child.textContent.trim();
                        if (t) bodyParts.push(t);
                    }
                });
                return bodyParts.length ? title + '\\n\\n' + bodyParts.join('\\n\\n') : title;
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

            var copyBtn = document.createElement('button');
            copyBtn.type = 'button';
            copyBtn.textContent = '\U0001F4CB';
            copyBtn.setAttribute('aria-label', 'Copier');
            copyBtn.title = 'Copier';
            copyBtn.addEventListener('click', function() {
                navigator.clipboard.writeText(entryText(matches[current])).then(function() {
                    showToast('Copie dans le presse-papier');
                }, function() {
                    showToast('Impossible de copier');
                });
            });

            var shareBtn = document.createElement('button');
            shareBtn.type = 'button';
            shareBtn.textContent = '\U0001F4E4';
            shareBtn.setAttribute('aria-label', 'Partager');
            shareBtn.title = 'Partager';
            shareBtn.addEventListener('click', function() {
                var text = entryText(matches[current]);
                if (navigator.share) {
                    navigator.share({ text: text }).catch(function() {});
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

    // Suivi de la position de lecture (volume francais uniquement) : sauve
    // en localStorage le verset actuellement en haut de l'ecran, pour
    // pouvoir proposer "Continuer la lecture" depuis l'accueil.
    var STORAGE_KEY = 'bukaAMoromona:lastRead';
    var versesFr = document.querySelector('.verses-fr');
    if (versesFr) {
        var saveTimer = null;
        function saveReadingPosition() {
            var verses = versesFr.querySelectorAll('.verse-fr[id]');
            var current = null;
            for (var i = 0; i < verses.length; i++) {
                if (verses[i].getBoundingClientRect().bottom > 80) {
                    current = verses[i];
                    break;
                }
            }
            if (!current) return;
            var h1 = document.querySelector('h1');
            var h2 = document.querySelector('h2');
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                bookIdx: versesFr.getAttribute('data-book-idx'),
                chapterIdx: versesFr.getAttribute('data-chapter-idx'),
                verseId: current.id,
                bookTitle: h1 ? h1.textContent : '',
                chapterTitle: h2 ? h2.textContent : '',
                verseNum: current.id.replace('v', '')
            }));
        }
        window.addEventListener('scroll', function() {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(saveReadingPosition, 400);
        });
        window.addEventListener('pagehide', saveReadingPosition);
        saveReadingPosition();
    }

    // Page d'accueil : propose "Continuer la lecture" si une position est
    // enregistree.
    var continueSlot = document.getElementById('continue-reading-slot');
    if (continueSlot) {
        var saved = null;
        try {
            saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
        } catch (e) {}
        if (saved && saved.bookIdx && saved.chapterIdx && saved.verseId) {
            var link = document.createElement('a');
            link.className = 'continue-reading';
            link.href = 'chapters-fr/chapter_' + saved.bookIdx + '_' + saved.chapterIdx + '.html#' + saved.verseId;
            link.textContent = 'Continuer la lecture — ' + saved.chapterTitle + ', verset ' + saved.verseNum;
            continueSlot.appendChild(link);
        }
    }
});
'''

write('script.js', js_content)
