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

# Générer la table des matières avec menu dépliant
toc_html = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Livre de Mormon - Table des matières</title>
    <link rel="stylesheet" href="styles.css">
    <script src="script.js"></script>
</head>
<body>
    <h1>Livre de Mormon</h1>
    <h2>Table des matières</h2>
    <div class="accordion">
'''

for book_idx, book in enumerate(book_data, 1):
    toc_html += f'''
        <div class="accordion-item">
            <button class="accordion-button">{book["book_title"]}</button>
            <div class="accordion-content">
                <ul>
    '''
    for chap_idx, chapter in enumerate(book['chapters'], 1):
        chapter_filename = f'chapters/chapter_{book_idx}_{chap_idx}.html'
        toc_html += f'<li><a href="{chapter_filename}">{chapter["title"]}</a></li>'
    toc_html += '''
                </ul>
            </div>
        </div>
    '''

toc_html += '''
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
    <title>{chapter_title}</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <h1>{book_title}</h1>
    <h2>{chapter_title}</h2>
    {verses_html}
    {introduction_html}
    <p>
        {prev_link}
        {next_link}
        <a href="../index.html">Retour à la table des matières</a>
    </p>
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
body {
    font-family: Arial, sans-serif;
    margin: 40px;
    line-height: 1.6;
}
h1, h2 {
    color: #333;
}
.verse-container {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px; /* Espace vertical entre les versets */
}
.verse-container.introduction {
    background-color: #f9f9f9;
    font-style: italic;
    margin-bottom: 10px; /* Même espace pour l'introduction */
}
.tahitien {
    width: 48%;
}
.francais {
    width: 48%;
}
.accordion-button {
    background-color: #f4f4f4;
    color: #333;
    cursor: pointer;
    padding: 15px;
    width: 100%;
    text-align: left;
    border: none;
    outline: none;
    font-size: 16px;
    font-weight: bold;
    margin-bottom: 2px;
}
.accordion-button:hover {
    background-color: #e0e0e0;
}
.accordion-content {
    display: none;
    padding: 0 15px;
    background-color: #fff;
}
.accordion-content ul {
    list-style-type: none;
    padding-left: 20px;
}
.accordion-content a {
    text-decoration: none;
    color: #0066cc;
}
.accordion-content a:hover {
    text-decoration: underline;
}
.accordion-content.show {
    display: block;
}
'''

with open('styles.css', 'w', encoding='utf-8') as file:
    file.write(css_content)

# Créer un fichier JavaScript pour le menu dépliant
js_content = '''
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.accordion-button');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const content = this.nextElementSibling;
            content.classList.toggle('show');
        });
    });
});
'''

with open('script.js', 'w', encoding='utf-8') as file:
    file.write(js_content)