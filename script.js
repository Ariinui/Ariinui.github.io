
document.addEventListener('DOMContentLoaded', function() {
    const buttons = document.querySelectorAll('.accordion-button');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const content = this.nextElementSibling;
            content.classList.toggle('show');
        });
    });

    // Infobulles sur mobile (clic au lieu de survol)
    const tooltips = document.querySelectorAll('.tooltip');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('click', function(e) {
            e.preventDefault();
            // Toggle infobulle au clic
            this.classList.toggle('show-tooltip');
        });
    });
});

// Ajouter un style dynamique pour gérer les infobulles au clic sur mobile
const style = document.createElement('style');
style.innerHTML = `
    .tooltip.show-tooltip::after {
        opacity: 1;
        visibility: visible;
    }
`;
document.head.appendChild(style);
