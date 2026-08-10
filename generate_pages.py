from bs4 import BeautifulSoup
import os
import re

# Lire le fichier HTML
with open('livre_de_mormon.html', 'r', encoding='utf-8') as file:
    soup = BeautifulSoup(file, 'lxml')

# Extraire les chapitres
chapters = soup.find_all('h1', id=re.compile('chapitre-\d+'))
book_data = []
current_book = None
chapter_list = []

for chapter in chapters:
    # Extraire le titre du chapitre (par exemple, "1 Ne Chapitre 1")
    chapter_title = chapter.text.strip()
    # Déterminer le nom du livre (par exemple, "1 Néphi")
    book_name = ' '.join(chapter_title.split()[:-2])  # Prend tout sauf "Chapitre X"
    if book_name != current_book:
        if current_book is not None:
            book_data.append({'book_title': current_book, 'chapters': chapter_list})
        current_book = book_name
        chapter_list = []
    
    # Extraire les versets et l'introduction
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

# Ajouter le dernier livre
if current_book and chapter_list:
    book_data.append({'book_title': current_book, 'chapters': chapter_list})

# Créer un dossier pour les chapitres
os.makedirs('chapters', exist_ok=True)

# Générer la table des matières avec menu dépliant (volume > livre > grille de chapitres)
toc_html = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Livre de Mormon - Table des matières</title>
    <link rel="stylesheet" href="styles.css">
    <script src="script.js"></script>
</head>
<body>
    <div class="page">
        <h1>
            <button class="volume-toggle" type="button" aria-expanded="false">
                <span class="chevron" aria-hidden="true"></span>
                Livre de Mormon
            </button>
        </h1>
        <div class="volume-content">
            <div class="accordion">
'''

for book_idx, book in enumerate(book_data, 1):
    toc_html += f'''
                <div class="accordion-item">
                    <button class="accordion-button" type="button" aria-expanded="false">
                        <span class="chevron" aria-hidden="true"></span>
                        {book["book_title"]}
                    </button>
                    <div class="accordion-content">
                        <div class="chapter-grid">
    '''
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        chapter_filename = f'chapters/chapter_{book_idx}_{chap_idx}.html'
        toc_html += f'<a class="chapter-link" href="{chapter_filename}" title="{chapter["title"]}">{chap_idx}</a>'
    toc_html += '''
                        </div>
                    </div>
                </div>
    '''

toc_html += '''
            </div>
        </div>
    </div>
</body>
</html>
'''

# Sauvegarder la table des matières
with open('index.html', 'w', encoding='utf-8') as file:
    file.write(toc_html)

# Modèle pour les pages de chapitres
chapter_template = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{chapter_title}</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <div class="page">
    <h1>{book_title}</h1>
    <h2>{chapter_title}</h2>
    {verses_html}
    {introduction_html}
    <nav>
        {prev_link}
        {next_link}
        <a href="../index.html">Retour à la table des matières</a>
    </nav>
    </div>
</body>
</html>
'''

# Générer une page pour chaque chapitre
for book_idx, book in enumerate(book_data, 1):
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        # Générer le HTML pour les versets
        verses_html = ''
        for verse in chapter['verses']:
            verses_html += '<div class="verse-container">'
            verses_html += f'<div class="tahitien">{verse["tahitien"]}</div>'
            verses_html += f'<div class="francais">{verse["francais"]}</div>'
            verses_html += '</div>'
        
        # Générer le HTML pour l'introduction (si présente)
        introduction_html = ''
        if chapter['introduction']:
            introduction_html = '<div class="verse-container introduction">'
            introduction_html += f'<div class="tahitien">{chapter["introduction"]["tahitien"]}</div>'
            introduction_html += f'<div class="francais">{chapter["introduction"]["francais"]}</div>'
            introduction_html += '</div>'
        
        # Générer les liens précédent/suivant
        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre précédent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''
        
        # Remplir le modèle
        chapter_html = chapter_template.format(
            book_title=book['book_title'],
            chapter_title=chapter['title'],
            verses_html=verses_html,
            introduction_html=introduction_html,
            prev_link=prev_link,
            next_link=next_link
        )
        
        # Sauvegarder la page du chapitre
        chapter_filename = f'chapters/chapter_{book_idx}_{chap_idx}.html'
        with open(chapter_filename, 'w', encoding='utf-8') as file:
            file.write(chapter_html)

# Créer un fichier CSS pour le style
css_content = '''
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #f5f6f8;
    color: #1c1e21;
}

h1, h2 {
    color: #1c1e21;
}

.page {
    max-width: 720px;
    margin: 0 auto;
    padding: 32px 20px 80px;
}

h1 {
    margin: 0 0 16px;
    font-size: 22px;
}

.volume-toggle,
.accordion-button {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    background: #ffffff;
    color: #1c1e21;
    cursor: pointer;
    text-align: left;
    font: inherit;
    border: 1px solid #e2e5ea;
    border-radius: 8px;
    outline: none;
}

.volume-toggle {
    padding: 14px 16px;
    font-size: 20px;
    font-weight: 600;
}

.accordion-button {
    padding: 12px 16px;
    font-size: 15px;
}

.volume-toggle:hover,
.accordion-button:hover {
    background: #eef1f5;
}

.chevron {
    flex-shrink: 0;
    display: inline-block;
    width: 9px;
    height: 9px;
    border-right: 2px solid #5b6270;
    border-bottom: 2px solid #5b6270;
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
    background: #ffffff;
    border: 1px solid #e2e5ea;
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
    background: #f5f6f8;
    border: 1px solid #e2e5ea;
    color: #1b4d89;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
}

.chapter-link:hover,
.chapter-link:focus-visible {
    background: #1b4d89;
    color: #ffffff;
    border-color: #1b4d89;
}

.verse-container {
    display: flex;
    gap: 16px;
    justify-content: space-between;
    margin-bottom: 10px;
}

.verse-container.introduction {
    background-color: #f9f9f9;
    font-style: italic;
}

.tahitien, .francais {
    width: 48%;
}

@media (max-width: 640px) {
    .page {
        padding: 20px 14px 60px;
    }

    .volume-toggle {
        font-size: 18px;
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

with open('styles.css', 'w', encoding='utf-8') as file:
    file.write(css_content)

# Créer un fichier JavaScript pour le menu dépliant
js_content = '''
document.addEventListener('DOMContentLoaded', function() {
    function wireToggle(button, content) {
        button.addEventListener('click', function() {
            const isOpen = content.classList.toggle('show');
            button.setAttribute('aria-expanded', String(isOpen));
        });
    }

    document.querySelectorAll('.volume-toggle').forEach(function(button) {
        wireToggle(button, button.closest('h1').nextElementSibling);
    });

    document.querySelectorAll('.accordion-button').forEach(function(button) {
        wireToggle(button, button.nextElementSibling);
    });
});
'''

with open('script.js', 'w', encoding='utf-8') as file:
    file.write(js_content)