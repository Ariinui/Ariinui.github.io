
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
    [].slice.call(document.querySelectorAll('.bookmark-toggle')).forEach(function(btn) {
        var key = btn.getAttribute('data-bookmark-key');
        var storageKey = 'bukaAMoromona:hideBookmark:' + key;
        var attr = 'data-hide-bookmark-' + key;
        var sync = function() {
            btn.setAttribute('aria-pressed', localStorage.getItem(storageKey) === '1' ? 'false' : 'true');
        };
        sync();
        btn.addEventListener('click', function() {
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
            themeToggle.textContent = currentTheme() === 'dark' ? '☀️' : '🌙';
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
                var guideText = bodyParts.length ? title + '\n\n' + bodyParts.join('\n\n') : title;
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

            function underline(str) {
                return str.split('').map(function(c) { return c + '\u0332'; }).join('');
            }

            function entryText(entry, underlineNotesLabel) {
                var p = entryParts(entry);
                var datePrefix = todayLong() + '\n\n';
                var notesLabel = underlineNotesLabel ? underline('Notes du guide') : 'Notes du guide';
                if (p.verseRef && p.verseText) {
                    return datePrefix + p.verseRef + '\n\n' + p.verseText + '\n\n' + notesLabel + '\n\n' + p.guideText;
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
                navigator.clipboard.writeText(entryText(matches[current], true)).then(function() {
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

    // Bouton flottant "retour a la table des matieres" : apparait quand on
    // scroll vers le haut, se cache immediatement quand on scroll vers le
    // bas (pas de debounce ici, contrairement a la sauvegarde de position
    // plus bas, pour que le masquage soit instantane).
    var backToToc = document.querySelector('.back-to-toc-float');
    if (backToToc) {
        var lastScrollY = window.scrollY;
        var tocTicking = false;
        window.addEventListener('scroll', function() {
            if (tocTicking) return;
            tocTicking = true;
            window.requestAnimationFrame(function() {
                var currentScrollY = window.scrollY;
                if (currentScrollY < lastScrollY) {
                    backToToc.classList.add('visible');
                } else if (currentScrollY > lastScrollY) {
                    backToToc.classList.remove('visible');
                }
                lastScrollY = currentScrollY;
                tocTicking = false;
            });
        });
    }

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
            var verseMatch = /^v(\d+)$/.exec(saved.itemId || '');
            var suffix = verseMatch ? (', verset ' + verseMatch[1]) : '';
            link.textContent = 'Continuer — ' + saved.volumeTitle + ' : ' + saved.chapterTitle + suffix;
            continueSlot.appendChild(link);
        });
    }
});
