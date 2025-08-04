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
    chapter_title = chapter.text.strip()
    book_name = ' '.join(chapter_title.split()[:-2])
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

os.makedirs('chapters', exist_ok=True)

# Générer la table des matières
toc_html = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Livre de Mormon - Table des matières</title>
    <link rel="stylesheet" href="styles.css">
    <script src="script.js" defer></script>
</head>
<body>
    <header class="navbar">
        <div class="container">
            <div class="logo">Livre de Mormon</div>
            <nav>
                <ul>
                    <li><a href="index.html" class="active">Accueil</a></li>
                    <li><a href="#library">Bibliothèque</a></li>
                    <li><a href="#discover">Découvrir</a></li>
                    <li><a href="#search">Recherche</a></li>
                    <li><a href="#account">Compte</a></li>
                </ul>
            </nav>
        </div>
    </header>
    <section class="hero">
        <div class="container">
            <h1>Bienvenue dans le Livre de Mormon</h1>
            <p>Explorez une bibliothèque bilingue tahitienne et française, avec des écritures inspirantes.</p>
            <a href="#library" class="cta-button">Découvrir la Bibliothèque</a>
        </div>
    </section>
    <section id="library" class="library-section">
        <div class="container">
            <h2>Table des matières</h2>
            <div class="accordion">
'''

for book_idx, book in enumerate(book_data, 1):
    toc_html += f'''
                <div class="accordion-item">
                    <button class="accordion-button">{book['book_title']}</button>
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
        </div>
    </section>
    <footer>
        <div class="container">
            <p>&copy; 2025 Livre de Mormon. Tous droits réservés.</p>
        </div>
    </footer>
</body>
</html>
'''

with open('index.html', 'w', encoding='utf-8') as file:
    file.write(toc_html)

# Modèle pour les pages de chapitres
chapter_template = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{chapter_title}</title>
    <link rel="stylesheet" href="../styles.css">
</head>
<body>
    <header class="navbar">
        <div class="container">
            <div class="logo">Livre de Mormon</div>
            <nav>
                <ul>
                    <li><a href="../index.html">Accueil</a></li>
                    <li><a href="../index.html#library" class="active">Bibliothèque</a></li>
                    <li><a href="#discover">Découvrir</a></li>
                    <li><a href="#search">Recherche</a></li>
                    <li><a href="#account">Compte</a></li>
                </ul>
            </nav>
        </div>
    </header>
    <section class="chapter-content">
        <div class="container">
            <h1>{book_title}</h1>
            <h2>{chapter_title}</h2>
            {verses_html}
            {introduction_html}
            <nav class="chapter-nav">
                {prev_link}
                {next_link}
                <a href="../index.html">Retour à la table des matières</a>
            </nav>
        </div>
    </section>
    <footer>
        <div class="container">
            <p>&copy; 2025 Livre de Mormon. Tous droits réservés.</p>
        </div>
    </footer>
</body>
</html>
'''

# Générer les pages de chapitres
for book_idx, book in enumerate(book_data, 1):
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
        
        prev_link = f'<a href="chapter_{book_idx}_{chap_idx-1}.html">Chapitre précédent</a> | ' if chap_idx > 1 else ''
        next_link = f'<a href="chapter_{book_idx}_{chap_idx+1}.html">Chapitre suivant</a> | ' if chap_idx < len(book['chapters']) else ''
        
        chapter_html = chapter_template.format(
            book_title=book['book_title'],
            chapter_title=chapter['title'],
            verses_html=verses_html,
            introduction_html=introduction_html,
            prev_link=prev_link,
            next_link=next_link
        )
        
        chapter_filename = f'chapters/chapter_{book_idx}_{chap_idx}.html'
        with open(chapter_filename, 'w', encoding='utf-8') as file:
            file.write(chapter_html)

# Écrire styles.css
css_content = '''
/* Réinitialisation de base */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Roboto', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f9fafb;
}

/* Conteneur général */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Barre de navigation */
.navbar {
    background-color: #ffffff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    position: sticky;
    top: 0;
    z-index: 1000;
}

.navbar .container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 0;
}

.logo {
    font-size: 24px;
    font-weight: 700;
    color: #1d4ed8;
}

nav ul {
    display: flex;
    list-style: none;
}

nav ul li {
    margin-left: 20px;
}

nav ul li a {
    text-decoration: none;
    color: #374151;
    font-weight: 500;
    font-size: 16px;
}

nav ul li a.active,
nav ul li a:hover {
    color: #1d4ed8;
}

/* Section Hero */
.hero {
    text-align: center;
    padding: 60px 20px;
    background-color: #eff6ff;
}

.hero h1 {
    font-size: 36px;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 20px;
}

.hero p {
    font-size: 18px;
    color: #4b5563;
    margin-bottom: 30px;
}

.cta-button {
    display: inline-block;
    padding: 12px 24px;
    background-color: #1d4ed8;
    color: #ffffff;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 600;
    transition: background-color 0.3s;
}

.cta-button:hover {
    background-color: #1e40af;
}

/* Table des matières */
.library-section {
    padding: 40px 0;
}

.library-section h2 {
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 20px;
}

.accordion-button {
    background-color: #ffffff;
    color: #374151;
    cursor: pointer;
    padding: 16px;
    width: 100%;
    text-align: left;
    border: none;
    outline: none;
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 2px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    transition: background-color 0.3s;
}

.accordion-button:hover {
    background-color: #f3f4f6;
}

.accordion-content {
    display: none;
    padding: 0 16px 16px;
    background-color: #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.accordion-content.show {
    display: block;
}

.accordion-content ul {
    list-style-type: none;
    padding-left: 20px;
}

.accordion-content a {
    text-decoration: none;
    color: #1d4ed8;
    font-size: 16px;
}

.accordion-content a:hover {
    text-decoration: underline;
}

/* Mise en page des chapitres */
.chapter-content {
    padding: 40px 0;
}

.chapter-content h1 {
    font-size: 32px;
    font-weight: 700;
    color: #1f2937;
    margin-bottom: 10px;
}

.chapter-content h2 {
    font-size: 24px;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 20px;
}

.verse-container {
    display: flex;
    justify-content: space-between;
    margin-bottom: 10px;
    padding: 12px;
    background-color: #ffffff;
    border-radius: 6px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.verse-container.introduction {
    background-color: #f9fafb;
    font-style: italic;
}

.tahitien, .francais {
    width: 48%;
    font-size: 16px;
    color: #1f2937;
}

.chapter-nav {
    margin-top: 20px;
}

.chapter-nav a {
    margin-right: 15px;
    color: #1d4ed8;
    text-decoration: none;
    font-weight: 500;
}

.chapter-nav a:hover {
    text-decoration: underline;
}

/* Pied de page */
footer {
    background-color: #ffffff;
    padding: 20px 0;
    box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}

footer p {
    color: #4b5563;
    font-size: 14px;
}

/* Responsive Design */
@media (max-width: 768px) {
    .navbar .container {
        flex-direction: column;
        text-align: center;
    }

    nav ul {
        flex-direction: column;
        margin-top: 10px;
    }

    nav ul li {
        margin: 10px 0;
    }

    .hero h1 {
        font-size: 28px;
    }

    .hero p {
        font-size: 16px;
    }

    .verse-container {
        flex-direction: column;
    }

    .tahitien, .francais {
        width: 100%;
        margin-bottom: 10px;
    }
}
'''

with open('styles.css', 'w', encoding='utf-8') as file:
    file.write(css_content)

# Écrire script.js
js_content = '''
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.accordion-button');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const content = this.nextElementSibling;
            content.classList.toggle('show');
        });
    });

    const navLinks = document.querySelectorAll('nav ul li a');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
});
'''

with open('script.js', 'w', encoding='utf-8') as file:
    file.write(js_content)