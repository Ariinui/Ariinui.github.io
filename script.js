
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
                return bodyParts.length ? title + '\n\n' + bodyParts.join('\n\n') : title;
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
            copyBtn.textContent = '📋';
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
            shareBtn.textContent = '📤';
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
