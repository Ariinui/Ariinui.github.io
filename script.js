
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
    var moreMenuToggle = document.querySelector('.more-menu-toggle');
    var moreMenuPopover = document.getElementById('more-menu-popover');
    if (moreMenuToggle && moreMenuPopover) {
        moreMenuToggle.addEventListener('click', function(event) {
            event.stopPropagation();
            moreMenuPopover.hidden = !moreMenuPopover.hidden;
            moreMenuToggle.setAttribute('aria-expanded', moreMenuPopover.hidden ? 'false' : 'true');
        });
        document.addEventListener('click', function(event) {
            if (!moreMenuPopover.hidden && !moreMenuPopover.contains(event.target) && !moreMenuToggle.contains(event.target)) {
                moreMenuPopover.hidden = true;
                moreMenuToggle.setAttribute('aria-expanded', 'false');
            }
        });
    }

    [].slice.call(document.querySelectorAll('[data-bookmark-key]')).forEach(function(row) {
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

    var themeRow = document.querySelector('.theme-menu-row');
    if (themeRow) {
        var currentTheme = function() {
            var stored = localStorage.getItem('bukaAMoromona:theme');
            if (stored === 'light' || stored === 'dark') return stored;
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        };
        var syncTheme = function() {
            themeRow.setAttribute('aria-checked', currentTheme() === 'dark' ? 'true' : 'false');
        };
        syncTheme();
        themeRow.addEventListener('click', function() {
            var next = currentTheme() === 'dark' ? 'light' : 'dark';
            localStorage.setItem('bukaAMoromona:theme', next);
            document.documentElement.setAttribute('data-theme', next);
            syncTheme();
        });
    }

    var textSizeRow = document.querySelector('.text-size-row');
    if (textSizeRow) {
        var sizes = ['xsmall', 'small', 'normal', 'large', 'xlarge', 'xxlarge'];
        var steps = [].slice.call(textSizeRow.querySelectorAll('.text-size-step'));
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
        steps.forEach(function(step) {
            step.addEventListener('click', function() {
                var dir = parseInt(step.getAttribute('data-dir'), 10);
                var next = currentIndex() + dir;
                if (next >= 0 && next < sizes.length) applySize(sizes[next]);
            });
        });
    }

    // Popover "..." de l'accueil uniquement (reset_time_row cote Python) -
    // un bouton par volume porteur du badge %/temps (francais, qui inclut deja
    // le temps des guides via le meme bucket ; tahitien). Efface seulement
    // le temps de lecture (bukaAMoromona:readingTime) de CE bucket, jamais
    // la position/% (bukaAMoromona:reading) ni l'autre volume - confirmation
    // requise, action irreversible. Recharge la page pour faire disparaitre
    // les badges de temps deja affiches.
    var RESET_VOLUME_LABELS = { french: 'Livre de Mormon (et ses guides)', tahitian: 'Te Buka a Moromona' };
    [].slice.call(document.querySelectorAll('.reset-time-row')).forEach(function(row) {
        var vol = row.getAttribute('data-reset-volume');
        row.addEventListener('click', function() {
            var label = RESET_VOLUME_LABELS[vol] || vol;
            var ok = window.confirm('Réinitialiser le temps de lecture cumulé pour ' + label + ' ? Ta position de lecture et ton % de progression ne seront pas touchés.');
            if (!ok) return;
            var timesAll = {};
            try { timesAll = JSON.parse(localStorage.getItem('bukaAMoromona:readingTime')) || {}; } catch (e) {}
            delete timesAll[vol];
            localStorage.setItem('bukaAMoromona:readingTime', JSON.stringify(timesAll));
            location.reload();
        });
    });

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
    // Efface directement (synchrone, au clic) la position "Continuer" de CE
    // guide - utilise par "Retour au verset"/Precedent/Suivant plus bas.
    // Deliberement PAS un simple flag lu plus tard par le pagehide de fin de
    // page (moins fiable sur mobile/Safari iOS ou pagehide peut ne pas
    // s'executer a temps sur une navigation vers une nouvelle URL) -
    // l'effacement doit etre termine AVANT que la navigation ne commence.
    // skipGuidePositionSave sert seulement a empecher le pagehide (plus loin
    // dans ce script) de RE-creer l'entree juste apres qu'on vient de
    // l'effacer ici.
    var skipGuidePositionSave = false;
    function clearContinueForThisGuide() {
        skipGuidePositionSave = true;
        var key = guideContent && guideContent.getAttribute('data-volume-key');
        if (!key) return;
        var all = {};
        try { all = JSON.parse(localStorage.getItem('bukaAMoromona:reading')) || {}; } catch (e) {}
        delete all[key];
        localStorage.setItem('bukaAMoromona:reading', JSON.stringify(all));
    }
    // Marque un lien comme "sortie de guide" - le clic est capture par
    // delegation depuis <nav> lui-meme (voir plus bas), un element STABLE
    // jamais recree, plutot qu'un ecouteur attache individuellement a
    // chaque lien.
    function markGuideExitLink(link) {
        link.setAttribute('data-guide-exit', '1');
    }
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
            // Arrivee via "Continuer" avec une sous-entree precise dans le
            // hash (ex. #v1-5, 5e entree du verset 1) : afficher directement
            // celle-ci plutot que de toujours retomber sur la 1ere (bug
            // corrige - showEntry(0) etait appele sans condition avant).
            var initialIndex = 0;
            for (var mi = 0; mi < matches.length; mi++) {
                if (matches[mi].id === targetId) { initialIndex = mi; break; }
            }
            showEntry(initialIndex);
            // Le navigateur scrolle nativement vers l'ancre (#v3) AVANT/
            // pendant que ce script isole l'entree (les autres passent en
            // display:none) - resultat : l'ouverture atterrit en plein
            // milieu du texte, h1/h2 (titre du guide + chapitre) restes
            // au-dessus, hors ecran. Corrige uniquement pour une entree
            // JAMAIS OUVERTE (par page+ancre precise, pas par guide entier -
            // un guide deja visite via une AUTRE entree doit quand meme
            // ouvrir en haut ses propres entrees encore inedites) ; une
            // entree deja ouverte au moins une fois (Continuer y compris)
            // garde le comportement actuel inchange, sur demande explicite.
            var VISITED_GUIDE_ENTRIES_KEY = 'bukaAMoromona:visitedGuideEntries';
            var visitedEntryKey = location.pathname + '#' + targetId;
            var visitedGuideEntries = {};
            try { visitedGuideEntries = JSON.parse(localStorage.getItem(VISITED_GUIDE_ENTRIES_KEY)) || {}; } catch (e) {}
            if (!visitedGuideEntries[visitedEntryKey]) {
                // Une seule tentative (rAF, ou meme rAF+"load") ne suffit
                // pas de façon fiable : le navigateur peut rejouer son
                // propre scroll natif vers l'ancre a plusieurs reprises
                // pendant que la mise en page se stabilise (images qui se
                // chargent...), y compris APRES l'evenement "load" - mesure
                // empiriquement sur ce site (BOM Evidence notamment).
                // Reforce donc a plusieurs echeances etalees sur 1.5s -
                // seule methode fiable trouvee pour gagner cette course
                // contre un re-scroll natif dont le timing exact varie.
                var forceScrollTop = function() { window.scrollTo(0, 0); };
                requestAnimationFrame(forceScrollTop);
                window.addEventListener('load', forceScrollTop);
                [50, 150, 300, 600, 1000, 1500].forEach(function(delay) {
                    setTimeout(forceScrollTop, delay);
                });
                visitedGuideEntries[visitedEntryKey] = 1;
                try { localStorage.setItem(VISITED_GUIDE_ENTRIES_KEY, JSON.stringify(visitedGuideEntries)); } catch (e) {}
            }
            // Le navigateur scrolle nativement vers l'ancre (#v3) AVANT/
            // pendant que ce script isole l'entree (les autres passent en
            // display:none) - resultat : l'ouverture atterrit en plein
            // milieu du texte, h1/h2 (titre du guide + chapitre) restes
            // au-dessus, hors ecran. Corrige UNIQUEMENT pour un guide
            // jamais visite (aucune entree encore sauvegardee dans
            // bukaAMoromona:reading pour ce volume) - un guide deja visite
            // (arrivee via "Continuer" ou tout autre signet du meme guide)
            // garde le comportement actuel inchange, sur demande explicite.
            var volKeyForScroll = guideContent.getAttribute('data-volume-key');
            var guideAlreadyVisited = false;
            if (volKeyForScroll) {
                try {
                    var savedReadingForScroll = JSON.parse(localStorage.getItem('bukaAMoromona:reading')) || {};
                    guideAlreadyVisited = !!savedReadingForScroll[volKeyForScroll];
                } catch (e) {}
            }
            if (!guideAlreadyVisited) {
                // rAF pour executer apres que le navigateur ait fini son
                // propre scroll natif vers l'ancre, sinon il peut regagner.
                requestAnimationFrame(function() { window.scrollTo(0, 0); });
            }

            var bookIdx = guideContent.getAttribute('data-book-idx');
            var chapterIdx = guideContent.getAttribute('data-chapter-idx');
            var nav = document.querySelector('nav');
            if (bookIdx && chapterIdx && nav) {
                var backLink = document.createElement('a');
                backLink.href = '../../chapters-fr/chapter_' + bookIdx + '_' + chapterIdx + '.html#' + baseId;
                backLink.textContent = 'Retour au verset';
                // "Retour au verset"/Precedent/Suivant = l'utilisateur quitte
                // deliberement cette entree de guide (pas juste ferme
                // l'onglet ou navigue ailleurs par accident) - le "Continuer"
                // de ce signet ne doit plus reapparaitre a l'accueil.
                markGuideExitLink(backLink);
                nav.insertBefore(backLink, nav.firstChild);

                // "Accueil" (lien statique du template CHAPTER_NAV) - sur
                // demande explicite, NE compte PAS comme une sortie
                // volontaire de cette entree (contrairement a Retour au
                // verset/Precedent/Suivant juste en dessous) : navigation
                // normale, non interceptee par la delegation nav ci-dessous,
                // donc le pagehide sauvegarde la position comme le ferait
                // un retour par geste natif du telephone.

                // Arrive via signet = simple consultation ponctuelle d'un
                // verset, pas un parcours du guide lui-meme : Precedent/
                // Suivant doit continuer la LECTURE du Livre de Mormon
                // francais (chapitre reel +-1), jamais rester dans le guide
                // en mode "liste complete" du chapitre voisin. Mute l'element
                // EXISTANT (plus de replaceChild) - la delegation depuis nav
                // ne depend plus de l'identite exacte de l'element clique.
                [].slice.call(nav.querySelectorAll('a')).forEach(function(a) {
                    var m = a.getAttribute('href').match(/^chapter_(\d+)_(\d+)\.html$/);
                    if (!m) return;
                    a.href = '../../chapters-fr/chapter_' + m[1] + '_' + m[2] + '.html';
                    markGuideExitLink(a);
                });

                // Delegation : un seul ecouteur sur <nav> (jamais recree),
                // plutot qu'un ecouteur par lien individuel - cf. le
                // commentaire de markGuideExitLink plus haut.
                nav.addEventListener('click', function(event) {
                    var link = event.target.closest && event.target.closest('a[data-guide-exit]');
                    if (!link) return;
                    event.preventDefault();
                    var href = link.href;
                    clearContinueForThisGuide();
                    setTimeout(function() { window.location.href = href; }, 50);
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
    function setupTapToTranslate(selector, dictUrl, audioUrl, defUrl) {
        if (!document.querySelector(selector)) return;
        var dictPromise = null;
        var audioDictPromise = null;
        var defDictPromise = null;
        var popup = null;
        var activeWord = null;

        function loadDict() {
            if (!dictPromise) {
                dictPromise = fetch(dictUrl).then(function(r) { return r.json(); }).catch(function() { return {}; });
            }
            return dictPromise;
        }

        function loadAudioDict() {
            if (!audioUrl) return Promise.resolve({});
            if (!audioDictPromise) {
                audioDictPromise = fetch(audioUrl).then(function(r) { return r.json(); }).catch(function() { return {}; });
            }
            return audioDictPromise;
        }

        function loadDefDict() {
            if (!defUrl) return Promise.resolve({});
            if (!defDictPromise) {
                defDictPromise = fetch(defUrl).then(function(r) { return r.json(); }).catch(function() { return {}; });
            }
            return defDictPromise;
        }

        function closePopup() {
            if (popup) { popup.remove(); popup = null; }
            if (activeWord) { activeWord.classList.remove('active'); activeWord = null; }
        }

        // Reconstruit le style categorie grammaticale (bleu, italique) a partir
        // du texte brut, sans donnee structuree separee - 2 formats connus car
        // generes par nos propres scripts de scraping : "vt: battre, ..." (reo.pf,
        // categorie+deux-points) et "n.c. recit, ..." / "v.t." seul (Fare Vana'a,
        // categorie en abreviations a points, jamais suivie de deux-points).
        var CAT_COLON_RE = /^([a-zàâäéèêëïîôöùûüç]{1,6}):\s*/i;
        var CAT_DOT_RE = /^((?:[a-zàâäéèêëïîôöùûüç]{1,4}\.){1,3})\s*/i;

        function appendStyledLine(container, line) {
            if (!line) return;
            var lineEl = document.createElement('div');
            var m = line.match(CAT_COLON_RE) || line.match(CAT_DOT_RE);
            if (m) {
                var catSpan = document.createElement('span');
                catSpan.className = 'tah-popup-cat';
                catSpan.textContent = m[0];
                lineEl.appendChild(catSpan);
                lineEl.appendChild(document.createTextNode(line.slice(m[0].length)));
            } else {
                lineEl.textContent = line;
            }
            container.appendChild(lineEl);
        }

        function renderLines(container, text) {
            container.textContent = '';
            text.split('\n').forEach(function(line) { appendStyledLine(container, line); });
        }

        // Prononciation reelle des lettres empruntees (absentes du tahitien natif,
        // f/h/m/n/p/r/t/v/') dans les noms/mots bibliques transcrits avec leur
        // orthographe d'origine (ex. Alama, Babulonia) - regle systematique
        // confirmee par l'utilisateur, sans liste d'exceptions : b->p, d->t,
        // l->r, s->t, z->t ; k et les voyelles (dont u, jamais "ou") inchanges.
        var PHONETIC_MAP = { b: 'p', d: 't', l: 'r', s: 't', z: 't', B: 'P', D: 'T', L: 'R', S: 'T', Z: 'T' };
        function toPhoneticTahitian(text) {
            return text.replace(/[bdlszBDLSZ]/g, function(ch) { return PHONETIC_MAP[ch]; });
        }

        var AUDIO_ICON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>';
        var INFO_ICON = '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>';

        function showPopup(el, gloss, audioSrc, def) {
            closePopup();
            activeWord = el;
            el.classList.add('active');
            popup = document.createElement('div');
            popup.className = 'tah-popup';

            var header = document.createElement('div');
            header.className = 'tah-popup-header';
            var titleEl = document.createElement('div');
            titleEl.className = 'tah-popup-title';
            titleEl.textContent = el.textContent;
            header.appendChild(titleEl);

            var phoneticText = toPhoneticTahitian(el.textContent);
            if (phoneticText !== el.textContent) {
                var phoneticEl = document.createElement('div');
                phoneticEl.className = 'tah-popup-phonetic';
                phoneticEl.textContent = phoneticText;
                header.appendChild(phoneticEl);
            }

            var icons = document.createElement('div');
            icons.className = 'tah-popup-icons';
            if (audioSrc) {
                var audioBtn = document.createElement('button');
                audioBtn.className = 'tah-popup-audio-btn';
                audioBtn.type = 'button';
                audioBtn.setAttribute('aria-label', 'Écouter la prononciation');
                audioBtn.innerHTML = AUDIO_ICON;
                audioBtn.addEventListener('click', function(event) {
                    event.stopPropagation();
                    new Audio(audioSrc).play().catch(function() {});
                });
                icons.appendChild(audioBtn);
            }

            // Sens precis pour ce verset (pose a la generation en comparant
            // au texte francais officiel du meme verset, cf. disambiguate_sense
            // dans generate_pages.py) : si present, il devient le texte
            // principal et la liste complete reo.pf rejoint la definition
            // Fare Vana'a derriere le (i) - sinon comportement inchange
            // (liste complete en principal, rien de plus a montrer que
            // Fare Vana'a derriere le (i)).
            var matchedSense = el.getAttribute('data-sense');
            var primaryText = matchedSense || gloss;

            var defEl = null;
            if (matchedSense || (def && def.text)) {
                defEl = document.createElement('div');
                defEl.className = 'tah-popup-definition';
                defEl.style.display = 'none';

                if (matchedSense) {
                    var fullGlossText = document.createElement('div');
                    fullGlossText.className = 'tah-popup-definition-text';
                    renderLines(fullGlossText, gloss);
                    defEl.appendChild(fullGlossText);
                }
                if (def && def.text) {
                    var defText = document.createElement('div');
                    defText.className = 'tah-popup-definition-text';
                    renderLines(defText, def.text);
                    defEl.appendChild(defText);
                    var sourceEl = document.createElement('span');
                    sourceEl.className = 'tah-popup-definition-source';
                    sourceEl.textContent = "Source : Fare Vana'a";
                    defEl.appendChild(sourceEl);
                }

                var infoBtn = document.createElement('button');
                infoBtn.className = 'tah-popup-info-btn';
                infoBtn.type = 'button';
                infoBtn.setAttribute('aria-label', 'Voir la définition complète');
                infoBtn.innerHTML = INFO_ICON;
                infoBtn.addEventListener('click', function(event) {
                    event.stopPropagation();
                    defEl.style.display = defEl.style.display === 'none' ? 'block' : 'none';
                });
                icons.appendChild(infoBtn);
            }
            header.appendChild(icons);
            popup.appendChild(header);

            var textEl = document.createElement('div');
            textEl.className = 'tah-popup-text';
            renderLines(textEl, primaryText);
            popup.appendChild(textEl);

            if (defEl) popup.appendChild(defEl);

            var arrow = document.createElement('div');
            arrow.className = 'tah-popup-arrow';
            popup.appendChild(arrow);

            popup.style.maxWidth = Math.min(320, window.innerWidth - 24) + 'px';
            popup.addEventListener('click', function(event) {
                event.stopPropagation();
                closePopup();
            });
            document.body.appendChild(popup);
            positionPopup(el, popup, arrow);
        }

        // Recalcule position de la bulle + pointe par rapport au mot - appele a
        // l'ouverture et a chaque scroll (la bulle reste ouverte et suit le mot
        // au lieu de se fermer, sur demande explicite de l'utilisateur).
        function positionPopup(el, popupEl, arrowEl) {
            var wordRect = el.getBoundingClientRect();
            var popupRect = popupEl.getBoundingClientRect();
            var left = Math.min(Math.max(8, wordRect.left), window.innerWidth - popupRect.width - 8);
            var top = wordRect.bottom + 10;
            var openedBelow = true;
            if (top + popupRect.height > window.innerHeight - 8) {
                top = wordRect.top - popupRect.height - 10;
                openedBelow = false;
            }
            popupEl.style.left = left + 'px';
            popupEl.style.top = top + 'px';

            var wordCenterX = wordRect.left + wordRect.width / 2;
            var arrowX = wordCenterX - left - 6;
            arrowX = Math.max(14, Math.min(arrowX, popupRect.width - 26));
            arrowEl.style.left = arrowX + 'px';
            if (openedBelow) {
                arrowEl.style.top = '-6px';
                arrowEl.style.bottom = '';
            } else {
                arrowEl.style.bottom = '-6px';
                arrowEl.style.top = '';
            }
        }

        // Delegation depuis document (pas d'attache par mot) : les mots du
        // mode Traduction plein ecran sont des clones ajoutes apres coup
        // (cf. openTranslation) et n'auraient jamais recu de listener direct
        // - deja documente comme peu fiable sur Android Chrome de toute
        // facon (cf. feedback_mobile_click_delegation).
        document.addEventListener('click', function(event) {
            // Dates des resumes de chapitre 1 (.tah-date, cf. wrap_tah_dates
            // dans generate_pages.py) : ecriture tahitienne deja embarquee en
            // data-words a la generation, meme bulle visuelle (showPopup)
            // que le tap-to-translate mais sans dictionnaire/audio/definition.
            var dateEl = event.target.closest('.tah-date');
            if (dateEl) {
                event.stopPropagation();
                if (activeWord === dateEl) { closePopup(); return; }
                showPopup(dateEl, dateEl.getAttribute('data-words'), null, null);
                return;
            }
            var el = event.target.closest(selector);
            if (!el) return;
            event.stopPropagation();
            if (activeWord === el) { closePopup(); return; }
            Promise.all([loadDict(), loadAudioDict(), loadDefDict()]).then(function(results) {
                var gloss = results[0][el.getAttribute('data-w')];
                var audioSrc = results[1][el.getAttribute('data-w')];
                var def = results[2][el.getAttribute('data-w')];
                if (gloss) showPopup(el, gloss, audioSrc, def);
            });
        });
        window.addEventListener('scroll', function() {
            if (popup && activeWord) {
                positionPopup(activeWord, popup, popup.querySelector('.tah-popup-arrow'));
            }
        }, true);
        window.__closeTahPopup = closePopup;
    }

    setupTapToTranslate('.tah-word', '../tah_dict.json', '../tah_audio.json', '../tah_definitions.json');

    // Mode "Traduction" plein ecran : tap sur un numero de verset tahitien
    // (.verse-num-tap) -> overlay avec CE SEUL verset dans 2 panneaux
    // (tahitien/francais) qui defilent en synchronisation proportionnelle
    // (memes % de progression - pas la meme longueur de texte dans les 2
    // langues). Traduction francaise deja embarquee en JSON inerte par
    // generate_pages.py (#translation-fr-verses), aucun fetch. Absent sur
    // toute page sans ce bloc (francais, guides...) - tout le reste de cette
    // IIFE ne s'execute donc que sur les pages tahitiennes.
    (function() {
        var frDataEl = document.getElementById('translation-fr-verses');
        if (!frDataEl) return;
        var translationFr = {};
        try { translationFr = JSON.parse(frDataEl.textContent) || {}; } catch (e) {}
        var verseNums = Object.keys(translationFr).map(Number).sort(function(a, b) { return a - b; });
        if (!verseNums.length) return;

        var versesContainer = document.querySelector('.verses-tah');
        var translationRef = versesContainer ? versesContainer.getAttribute('data-translation-ref') : '';

        var overlay = null, tahPane = null, frPane = null, prevBtn = null, nextBtn = null;
        var currentVerse = null;
        var syncing = false;

        function buildOverlay() {
            overlay = document.createElement('div');
            overlay.className = 'translation-overlay';

            var header = document.createElement('div');
            header.className = 'translation-header';
            var closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'translation-close';
            closeBtn.setAttribute('aria-label', 'Fermer');
            closeBtn.textContent = '×';
            closeBtn.addEventListener('click', closeOverlay);
            header.appendChild(closeBtn);

            var titles = document.createElement('div');
            titles.className = 'translation-titles';
            var titleEl = document.createElement('div');
            titleEl.className = 'translation-title';
            titleEl.textContent = 'Traduction';
            titles.appendChild(titleEl);
            var refEl = document.createElement('div');
            refEl.className = 'translation-ref';
            refEl.textContent = translationRef || '';
            titles.appendChild(refEl);
            header.appendChild(titles);
            overlay.appendChild(header);

            var body = document.createElement('div');
            body.className = 'translation-body';

            var tahLabel = document.createElement('div');
            tahLabel.className = 'translation-lang-label';
            tahLabel.textContent = 'tahitien';
            body.appendChild(tahLabel);

            tahPane = document.createElement('div');
            tahPane.className = 'translation-pane';
            tahPane.setAttribute('data-lang', 'tah');
            body.appendChild(tahPane);

            var frLabel = document.createElement('div');
            frLabel.className = 'translation-lang-label';
            frLabel.textContent = 'français';
            body.appendChild(frLabel);

            frPane = document.createElement('div');
            frPane.className = 'translation-pane';
            frPane.setAttribute('data-lang', 'fr');
            body.appendChild(frPane);

            overlay.appendChild(body);

            var footer = document.createElement('div');
            footer.className = 'translation-footer';
            prevBtn = document.createElement('button');
            prevBtn.type = 'button';
            prevBtn.className = 'translation-nav-btn';
            prevBtn.textContent = '‹ Verset précédent';
            prevBtn.addEventListener('click', function() { gotoVerse(-1); });
            footer.appendChild(prevBtn);
            nextBtn = document.createElement('button');
            nextBtn.type = 'button';
            nextBtn.className = 'translation-nav-btn';
            nextBtn.textContent = 'Verset suivant ›';
            nextBtn.addEventListener('click', function() { gotoVerse(1); });
            footer.appendChild(nextBtn);
            overlay.appendChild(footer);

            tahPane.addEventListener('scroll', function() { syncScroll(tahPane, frPane); });
            frPane.addEventListener('scroll', function() { syncScroll(frPane, tahPane); });

            document.body.appendChild(overlay);
        }

        // Defilement libre dans un panneau, l'autre suit a la MEME fraction
        // de progression (scrollTop / (scrollHeight - clientHeight)) plutot
        // qu'en pixels - le tahitien et le francais n'ont jamais la meme
        // longueur pour un meme verset. Drapeau de reentrance releve en rAF
        // (pas immediatement) : le scroll programmatique du panneau cible
        // declenche lui-meme un evenement scroll qu'il ne faut pas re-suivre.
        function syncScroll(src, dst) {
            if (syncing) return;
            syncing = true;
            var srcMax = src.scrollHeight - src.clientHeight;
            var dstMax = dst.scrollHeight - dst.clientHeight;
            if (srcMax > 0 && dstMax > 0) {
                dst.scrollTop = (src.scrollTop / srcMax) * dstMax;
            }
            // setTimeout plutot que requestAnimationFrame : ce dernier peut
            // ne jamais se declencher si la page/onglet est en arriere-plan
            // au moment du scroll (throttling navigateur), ce qui bloquerait
            // definitivement la synchronisation (drapeau syncing jamais
            // releve).
            setTimeout(function() { syncing = false; }, 0);
        }

        function renderVerse(num) {
            currentVerse = num;
            tahPane.textContent = '';
            var sourceP = versesContainer ? versesContainer.querySelector('#v' + num) : null;
            if (sourceP) {
                // Clone du <p> reel (pas une reconstruction du texte) : les
                // <span class="tah-word" data-w… data-sense…> du tap-to-
                // translate sont donc preserves tels quels et restent
                // cliquables via la delegation posee dans setupTapToTranslate.
                var clone = sourceP.cloneNode(true);
                clone.removeAttribute('id');
                tahPane.appendChild(clone);
            }

            frPane.textContent = '';
            var frP = document.createElement('p');
            frP.className = 'verse-fr';
            var sup = document.createElement('sup');
            sup.textContent = num;
            frP.appendChild(sup);
            frP.appendChild(document.createTextNode(translationFr[num] || ''));
            frPane.appendChild(frP);

            tahPane.scrollTop = 0;
            frPane.scrollTop = 0;

            var idx = verseNums.indexOf(Number(num));
            prevBtn.disabled = idx <= 0;
            nextBtn.disabled = idx === -1 || idx >= verseNums.length - 1;
        }

        function gotoVerse(delta) {
            var idx = verseNums.indexOf(Number(currentVerse));
            var nextIdx = idx + delta;
            if (nextIdx < 0 || nextIdx >= verseNums.length) return;
            renderVerse(verseNums[nextIdx]);
        }

        function openTranslation(num) {
            if (window.__closeTahPopup) window.__closeTahPopup();
            if (!overlay) buildOverlay();
            renderVerse(num);
            overlay.style.display = 'flex';
            document.body.style.overflow = 'hidden';
            if (window.history && window.history.pushState) {
                history.pushState({ translationOverlay: true }, '', location.href);
            }
        }

        function closeOverlay() {
            if (!overlay || overlay.style.display === 'none' || overlay.style.display === '') return false;
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            return true;
        }

        window.closeTranslationOverlay = closeOverlay;

        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') closeOverlay();
        });

        document.querySelectorAll('.verse-num-tap').forEach(function(el) {
            el.addEventListener('click', function(event) {
                event.stopPropagation();
                openTranslation(el.getAttribute('data-verse-tap'));
            });
        });
    })();

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
        // Un simple coup d'oeil (page ouverte puis quittee sans defiler) ne
        // doit pas creer d'entree "Continuer" - seul un vrai defilement
        // engage ce volume. Reste false pour l'appel initial (150ms plus
        // bas), passe a true des le premier evenement scroll.
        var hasEngaged = false;

        // Temps de lecture cumule, pour tout volume (francais/tahitien,
        // les 7 guides, Conference generale analogie - generique via
        // data-volume-key, meme principe que saveReadingPosition). Ne
        // compte que le temps ou l'onglet est reellement visible
        // (visibilitychange) - un onglet laisse ouvert en arriere-plan
        // n'incremente rien. Chaque commit ajoute le delta depuis le
        // dernier commit puis remet a zero la fenetre en cours, donc les
        // appels multiples (visibilitychange + pagehide) ne comptent
        // jamais deux fois le meme intervalle.
        var READING_TIME_KEY = 'bukaAMoromona:readingTime';
        {
            // Livre de Mormon francais + les 7 guides partagent UN SEUL
            // compteur ("french") - passer de la lecture au commentaire
            // d'un guide ne coupe pas le temps, ca reste le meme total
            // (sur demande explicite). Tahitien (pas de guide lie) et
            // Conference generale analogie restent des compteurs a part.
            var GUIDE_KEYS_FOR_TIME = Object.keys({"guide": "Gospel Doctrine", "guide2": "Start to Finish", "guide3": "Verse by Verse", "guide5": "Manuel de l'élève", "guide6": "ScripturePlus", "guide7": "BOM Evidence", "guide8": "BOM Minute"});
            var readingTimeBucket = (volumeKey === 'french' || GUIDE_KEYS_FOR_TIME.indexOf(volumeKey) !== -1) ? 'french' : volumeKey;
            var activeSince = (document.visibilityState === 'visible') ? Date.now() : null;
            var commitReadingTime = function() {
                if (activeSince === null) return;
                var deltaMs = Date.now() - activeSince;
                activeSince = Date.now();
                if (deltaMs <= 0) return;
                var timesAll = {};
                try { timesAll = JSON.parse(localStorage.getItem(READING_TIME_KEY)) || {}; } catch (e) {}
                timesAll[readingTimeBucket] = (timesAll[readingTimeBucket] || 0) + deltaMs;
                localStorage.setItem(READING_TIME_KEY, JSON.stringify(timesAll));
            };
            document.addEventListener('visibilitychange', function() {
                if (document.visibilityState === 'hidden') {
                    commitReadingTime();
                    activeSince = null;
                } else {
                    activeSince = Date.now();
                }
            });
            window.addEventListener('pagehide', commitReadingTime);
        }

        function saveReadingPosition() {
            // L'utilisateur a clique "Retour au verset"/Precedent/Suivant
            // depuis cette page de guide (deja efface synchroniquement au
            // clic, cf. clearContinueForThisGuide plus haut) - ne pas
            // re-creer l'entree ici quand pagehide se declenche en quittant.
            if (skipGuidePositionSave) return;
            var items = readingTrack.querySelectorAll('[id]');
            var current = null;
            for (var i = 0; i < items.length; i++) {
                if (items[i].getBoundingClientRect().bottom > 80) {
                    current = items[i];
                    break;
                }
            }
            // Fraction de defilement a l'interieur de l'element courant (0 =
            // son sommet vient d'entrer dans l'ecran, proche de 1 = son bas
            // approche) - permet a "Continuer" de revenir exactement ou la
            // lecture a ete arretee, pas juste en haut du verset/de
            // l'entree. Utile surtout sur les longues entrees de guide (BOM
            // Evidence...), sans effet notable sur les versets (courts).
            var scrollFrac = 0;
            if (current) {
                var rect = current.getBoundingClientRect();
                var h = current.offsetHeight || 1;
                scrollFrac = Math.max(0, Math.min(1, -rect.top / h));
            }
            // Un guide arrive via signet isole plusieurs entrees d'un meme
            // verset (v1, v1-2, v1-3...) avec Precedent/Suivant - on retient
            // aussi laquelle est affichee (index/total) pour l'afficher dans
            // "Continuer" (ex. "BOM Evidence 5/15").
            var entryIndex = null;
            var entryTotal = null;
            if (current && current.classList && current.classList.contains('guide-entry')) {
                var baseId = current.id.split('-')[0];
                var group = [];
                var allEntries = readingTrack.querySelectorAll('.guide-entry');
                for (var gi = 0; gi < allEntries.length; gi++) {
                    var gid = allEntries[gi].id;
                    if (gid === baseId || gid.indexOf(baseId + '-') === 0) group.push(allEntries[gi]);
                }
                if (group.length > 1) {
                    for (var pi = 0; pi < group.length; pi++) {
                        if (group[pi] === current) { entryIndex = pi; entryTotal = group.length; break; }
                    }
                }
            }
            // document.title contient deja "NomDuLivre Chapitre N" (Livre de
            // Mormon, voir chapter_display_title cote Python) ou "NomDuLivre
            // N" (pages de guide) - h2 seul serait insuffisant pour
            // identifier le livre dans "Continuer".
            var h2 = document.querySelector('h2');
            var h1 = document.querySelector('h1');
            // Sur une page de guide, le <title>/h2 vient de la source brute
            // du guide (ex. "1 Nephi 1", sans accent) alors que le <h1> est
            // deja passe par book_display_title (ex. "1 Néphi", accentue,
            // meme nom que le reste du site) - utiliser h1+data-chapter-idx
            // pour "Continuer" plutot que de re-parser un titre non fiable.
            var guideBook = null;
            var guideChapter = readingTrack.getAttribute('data-chapter-idx');
            if (guideChapter) guideBook = h1 ? h1.textContent.trim() : null;
            // Position globale (1..BOM_TOTAL_CHAPTERS) posee uniquement sur
            // les volumes francais/tahitien (data-global-chapter, cf.
            // BOM_CHAPTER_GLOBAL_INDEX cote Python) - sert au badge de
            // pourcentage sur le bouton "Continuer" de l'accueil, absent
            // pour les guides (pas de notion de "total" comparable).
            var globalChapterAttr = readingTrack.getAttribute('data-global-chapter');
            var globalChapter = globalChapterAttr ? parseInt(globalChapterAttr, 10) : null;
            var all = {};
            try { all = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {}; } catch (e) {}
            // Pas encore engage sur ce volume et aucune entree preexistante
            // a rafraichir (ex. retour via "Continuer") - ne pas en creer
            // une juste parce que la page a ete ouverte.
            if (!hasEngaged && !all[volumeKey]) return;
            all[volumeKey] = {
                volumeTitle: volumeTitle,
                href: location.pathname + (current ? '#' + current.id : ''),
                chapterTitle: document.title || (h2 ? h2.textContent.trim() : (h1 ? h1.textContent.trim() : '')),
                itemId: current ? current.id : null,
                scrollFrac: scrollFrac,
                entryIndex: entryIndex,
                entryTotal: entryTotal,
                guideBook: guideBook,
                guideChapter: guideChapter,
                globalChapter: globalChapter
            };
            localStorage.setItem(READING_STORAGE_KEY, JSON.stringify(all));
        }
        window.addEventListener('scroll', function() {
            hasEngaged = true;
            clearTimeout(saveTimer);
            saveTimer = setTimeout(saveReadingPosition, 400);
        });
        window.addEventListener('pagehide', saveReadingPosition);
        // Delai pour laisser le navigateur finir son scroll natif vers
        // l'ancre #vN (ex. arrivee via "Continuer la lecture") avant de
        // capturer/ecraser la position - sinon on lit "haut de page" trop tot.
        setTimeout(saveReadingPosition, 150);

        // Retour precis via "Continuer" : une fois l'ancre native (et
        // l'isolation eventuelle d'une entree de guide, deja executee plus
        // haut dans ce script) en place, ajuste le defilement fin a la
        // fraction sauvegardee - pour retomber exactement ou la lecture
        // avait ete arretee, pas juste en haut du verset/de l'entree. Lu
        // AVANT le setTimeout ci-dessus pour ne pas etre ecrase par la
        // re-sauvegarde qu'il declenche des l'arrivee sur la page.
        if (location.hash) {
            var hashId = location.hash.slice(1);
            var savedForFine = null;
            try {
                var allFine = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {};
                savedForFine = allFine[volumeKey];
            } catch (e) {}
            if (savedForFine && savedForFine.itemId === hashId && typeof savedForFine.scrollFrac === 'number') {
                setTimeout(function() {
                    var el = document.getElementById(hashId);
                    if (!el) return;
                    var rect = el.getBoundingClientRect();
                    var h = el.offsetHeight || 0;
                    var targetY = window.scrollY + rect.top + savedForFine.scrollFrac * h;
                    window.scrollTo({ top: Math.max(0, targetY), behavior: 'auto' });
                }, 300);
            }
        }
    }

    // Temps de lecture cumule (tous volumes, cf. commitReadingTime plus
    // haut) - charge une fois ici, partage entre le bloc francais/tahitien/
    // guides (continueSlot) et le bloc Conference generale analogie
    // (continueAnalogySlot, page distincte) plus bas.
    var readingTimesAll = {};
    try { readingTimesAll = JSON.parse(localStorage.getItem('bukaAMoromona:readingTime')) || {}; } catch (e) {}
    function formatReadingTime(ms) {
        var totalMinutes = Math.floor((ms || 0) / 60000);
        if (totalMinutes < 1) return null;
        var totalHours = Math.floor(totalMinutes / 60);
        var m = totalMinutes % 60;
        if (totalHours < 1) return m + ' min';
        if (totalHours < 24) return totalHours + 'h' + (m < 10 ? '0' : '') + m;
        // Au-dela de 24h, granularite jour+heure (pas de minutes) - reste
        // court et lisible dans le badge, meme sur mobile.
        var d = Math.floor(totalHours / 24);
        var h = totalHours % 24;
        return d + 'j ' + h + 'h';
    }

    // Page d'accueil : une ligne "Continuer la lecture" par volume ayant une
    // position enregistree.
    var continueSlot = document.getElementById('continue-reading-slot');
    if (continueSlot) {
        // Le navigateur (surtout Chrome mobile/Android) peut restaurer cette
        // page depuis le bfcache (retour arriere) sans jamais re-executer ce
        // script - les boutons "Continuer" affiches restent alors figes tels
        // qu'ils etaient AVANT une visite de guide, meme si le localStorage
        // a ete mis a jour entre-temps (ex. Continuer efface via "Chapitre
        // precedent/suivant" - cf. clearContinueForThisGuide plus haut).
        // pageshow avec persisted=true detecte ce cas et force un rechargement
        // frais plutot que de laisser un contenu perime affiche.
        window.addEventListener('pageshow', function(event) {
            if (event.persisted) location.reload();
        });
        // Francais/tahitien (accordeon d'accueil) + les 7 guides/signets
        // (GUIDE_LABELS, meme cle que le popover de filtre de signets) -
        // un Continuer par volume/signet ayant une position sauvegardee.
        var HOME_VOLUME_KEYS = ['french', 'tahitian'];
        var HOME_VOLUME_PREFIX = { french: 'FR', tahitian: 'TAH' };
        var GUIDE_LABELS = {"guide": "Gospel Doctrine", "guide2": "Start to Finish", "guide3": "Verse by Verse", "guide5": "Manuel de l'élève", "guide6": "ScripturePlus", "guide7": "BOM Evidence", "guide8": "BOM Minute"};
        var savedAll = {};
        try { savedAll = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {}; } catch (e) {}

        Object.keys(savedAll).forEach(function(key) {
            var saved = savedAll[key];
            if (!saved || !saved.href) return;
            var isGuide = Object.prototype.hasOwnProperty.call(GUIDE_LABELS, key);
            if (HOME_VOLUME_KEYS.indexOf(key) === -1 && !isGuide) return;

            var link = document.createElement('a');
            link.className = 'continue-reading';
            link.href = saved.href;

            if (isGuide) {
                link.classList.add('continue-' + key);
                var verseMatch = /^v(\d+)/.exec(saved.itemId || '');
                // guideBook/guideChapter (h1 + data-chapter-idx, captures a
                // la sauvegarde) plutot que de re-parser chapterTitle - evite
                // l'accent manquant du titre brut de page de guide ("1
                // Nephi" vs le "1 Néphi" du h1, deja passe par
                // book_display_title comme le reste du site).
                var ref = (saved.guideBook && saved.guideChapter && verseMatch)
                    ? (saved.guideBook + ' ' + saved.guideChapter + ':' + verseMatch[1])
                    : saved.chapterTitle;
                var prefix = true ? 'FR — ' : '';
                var entrySuffix = (saved.entryTotal && saved.entryTotal > 1)
                    ? ' ' + (saved.entryIndex + 1) + '/' + saved.entryTotal
                    : '';
                var textSpan1 = document.createElement('span');
                textSpan1.className = 'continue-reading-text';
                textSpan1.textContent = 'Continuer - ' + prefix + ref + ' · ' + GUIDE_LABELS[key] + entrySuffix;
                link.appendChild(textSpan1);
                // Temps de lecture cumule - partage avec le Livre de
                // Mormon francais (meme bucket "french", cf.
                // readingTimeBucket plus haut) - pas de % ici (pas de
                // notion de progression comparable au Livre de Mormon).
                var guideTimeLabel = formatReadingTime(readingTimesAll['french']);
                if (guideTimeLabel) {
                    var guideBadge = document.createElement('span');
                    guideBadge.className = 'continue-reading-badge';
                    guideBadge.textContent = guideTimeLabel;
                    link.appendChild(guideBadge);
                }
            } else {
                link.classList.add('continue-' + key);
                var verseMatch2 = /^v(\d+)$/.exec(saved.itemId || '');
                var mainText2;
                if (true && verseMatch2) {
                    // chapterTitle = document.title = 'NomDuLivre Chapitre N'
                    // (francais) ou 'NomDuLivre Pene N' (tahitien, chapters-tah).
                    var m2 = /^(.*) (?:Chapitre|Pene) (\d+)$/.exec(saved.chapterTitle || '');
                    var ref2 = m2 ? (m2[1] + ' ' + m2[2] + ':' + verseMatch2[1]) : saved.chapterTitle;
                    var prefix2 = true ? (HOME_VOLUME_PREFIX[key] + ' — ') : '';
                    mainText2 = 'Continuer - ' + prefix2 + ref2;
                } else {
                    var suffix2 = verseMatch2 ? (', verset ' + verseMatch2[1]) : '';
                    mainText2 = 'Continuer — ' + saved.volumeTitle + ' : ' + saved.chapterTitle + suffix2;
                }
                var textSpan2 = document.createElement('span');
                textSpan2.className = 'continue-reading-text';
                textSpan2.textContent = mainText2;
                link.appendChild(textSpan2);
                // Badge de progression (% de BOM_TOTAL_CHAPTERS atteint) -
                // uniquement quand la position enregistree porte une
                // position globale (volumes francais/tahitien, pas guides).
                if (typeof saved.globalChapter === 'number' && saved.globalChapter > 0) {
                    var pct = Math.round(saved.globalChapter / 239 * 100);
                    pct = Math.max(1, Math.min(100, pct));
                    var timeLabel = formatReadingTime(readingTimesAll[key]);
                    var badge = document.createElement('span');
                    badge.className = 'continue-reading-badge';
                    badge.textContent = timeLabel ? (pct + '% · ' + timeLabel) : (pct + '%');
                    link.appendChild(badge);
                }
            }
            continueSlot.appendChild(link);
        });
    }

    // Page "Conference generale analogie" : un seul bouton "Continuer" (pas de
    // variante FR/TAH ici, un seul volume) vers le dernier discours visite.
    var continueAnalogySlot = document.getElementById('continue-analogy-slot');
    if (continueAnalogySlot) {
        var savedAnalogyAll = {};
        try { savedAnalogyAll = JSON.parse(localStorage.getItem(READING_STORAGE_KEY)) || {}; } catch (e) {}
        var savedAnalogy = savedAnalogyAll['conference-analogies'];
        if (savedAnalogy && savedAnalogy.href) {
            var analogyLink = document.createElement('a');
            analogyLink.className = 'continue-reading';
            analogyLink.href = savedAnalogy.href;
            var analogyTextSpan = document.createElement('span');
            analogyTextSpan.className = 'continue-reading-text';
            analogyTextSpan.textContent = 'Continuer — ' + savedAnalogy.chapterTitle;
            analogyLink.appendChild(analogyTextSpan);
            var analogyTimeLabel = formatReadingTime(readingTimesAll['conference-analogies']);
            if (analogyTimeLabel) {
                var analogyBadge = document.createElement('span');
                analogyBadge.className = 'continue-reading-badge';
                analogyBadge.textContent = analogyTimeLabel;
                analogyLink.appendChild(analogyBadge);
            }
            continueAnalogySlot.appendChild(analogyLink);
        }
    }
});

if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js').catch(function() {});
    });
}
