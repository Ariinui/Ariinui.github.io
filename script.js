
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
    // l'entree ciblee, avec un bouton pour revenir a tout le chapitre.
    var guideContent = document.querySelector('.guide-content');
    if (guideContent && location.hash) {
        var target = null;
        try {
            target = guideContent.querySelector(location.hash);
        } catch (e) {}
        if (target && target.classList.contains('guide-entry')) {
            guideContent.classList.add('isolated');
            target.classList.add('target');
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
