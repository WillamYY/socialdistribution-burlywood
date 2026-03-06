document.addEventListener("DOMContentLoaded", function() {
    const clickableElements = document.querySelectorAll('.clickable');
    
    clickableElements.forEach(el => {
        el.addEventListener('click', function(event) {
            // Stop the click from triggering parent elements
            event.stopPropagation();
            
            const url = this.dataset.url;
            if (url) {
                window.location.href = url;
            }
        });
    });
});