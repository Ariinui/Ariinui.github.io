
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
    // visibles, seuls les AUTRES versets sont caches), avec un bouton pour
    // revenir a tout le chapitre.
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
            var showAll = document.createElement('button');
            showAll.type = 'button';
            showAll.className = 'show-all-entries';
            showAll.textContent = 'Voir tout le chapitre';
            showAll.addEventListener('click', function() {
                guideContent.classList.remove('isolated');
                showAll.remove();
            });
            guideContent.parentNode.insertBefore(showAll, guideContent);
        }
    }
});
