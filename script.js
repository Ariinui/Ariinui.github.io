
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
                        t = answer ? question + '\n\n' + answer : question;
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
                return str.split('').map(function(c) { return c + '\u0332'; }).join('');
            }

            // Retire les references entre parentheses du corps du texte
            // ("(voir 1 Nephi 2:16)", "(Ensign, oct. 2011, p. 43)"...) -
            // option de partage uniquement (jamais Copier), non recursif
            // mais suffisant : les parentheses de ce contenu ne s'embrouillent
            // jamais entre elles (verifie sur le Student Manual).
            function stripParenRefs(text) {
                return text.replace(/\s*\([^()]*\)/g, '').replace(/[ \t]{2,}/g, ' ').trim();
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
                // Titre (<h4> : Gospel Doctrine, Student Manual, ScripturePlus,
                // BOM Evidence) - perdu par inadvertance lors du refactor vers
                // entryBlocks() (8ffcfdec), jamais reintegre depuis. guide2/
                // guide3/guide8 n'ont pas de <h4> donc p.title est vide, ignore.
                if (p.title) blocks.push(p.title);
                return blocks.concat(bodyParts);
            }

            // Copier : texte integral, jamais decoupe (destination inconnue
            // - Notes, email... pas forcement Messenger), jamais de retrait
            // de reference non plus (ce toggle n'existe que sur Partager).
            function entryFullText(entry, underlineNotesLabel) {
                return entryBlocks(entry, underlineNotesLabel, false).join('\n\n');
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
                    var candidate = chunkCur ? chunkCur + '\n\n' + b : b;
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
                        return '(' + (i + 1) + '/' + chunks.length + ')\n' + c;
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
            var verseMatch = /^v(\d+)$/.exec(saved.itemId || '');
            var suffix = verseMatch ? (', verset ' + verseMatch[1]) : '';
            link.textContent = 'Continuer — ' + saved.volumeTitle + ' : ' + saved.chapterTitle + suffix;
            continueSlot.appendChild(link);
        });
    }
});

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js').catch(function() {});
    });
}
