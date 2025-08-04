
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
            const tooltipContent = this.querySelector(':scope::after');
            if (tooltipContent) {
                tooltipContent.style.opacity = tooltipContent.style.opacity === '1' ? '0' : '1';
                tooltipContent.style.visibility = tooltipContent.style.visibility === 'visible' ? 'hidden' : 'visible';
            }
        });
    });
});
