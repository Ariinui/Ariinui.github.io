
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
