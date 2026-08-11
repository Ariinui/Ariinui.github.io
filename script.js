
document.addEventListener('DOMContentLoaded', function() {
    function wireToggle(button, content) {
        button.addEventListener('click', function() {
            const isOpen = content.classList.toggle('show');
            button.setAttribute('aria-expanded', String(isOpen));
        });
    }

    document.querySelectorAll('.volume-toggle, .accordion-button').forEach(function(button) {
        wireToggle(button, button.nextElementSibling);
    });

    // Arrivee via un signet (#vN) sur une page de guide : n'affiche que
    // la ou les entrees du meme verset (un verset peut avoir plusieurs
    // entrees de commentaire : vN, vN-2, vN-3... - toutes doivent rester
    // visibles, seuls les AUTRES versets sont caches). Un lien "Retour au
    // verset" est ajoute dans la nav du bas (une fois la lecture terminee)
    // pour revenir exactement au verset francais d'origine.
    var guideContent = document.querySelector('.guide-content');
    if (guideContent && location.hash) {
        var targetId = location.hash.slice(1);
        var baseId = targetId.split('-')[0];
        var matches = [].slice.call(guideContent.querySelectorAll('.guide-entry')).filter(function(el) {
            return el.id === baseId || el.id.indexOf(baseId + '-') === 0;
        });
        if (matches.length) {
            guideContent.classList.add('isolated');
            matches.forEach(function(el) { el.classList.add('target'); });

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
            var verses = versesFr.querySelectorAll('.verse-container-fr[id]');
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
