/**
 * This JavaScript makes any element with class clickable behave like a link 
 * by reading a URL stored in data-url and redirecting the browser when it is clicked.
 * ChatGPT, OpenAI, 2026-03-12, https://chatgpt.com/share/69abd12e-d60c-8012-9314-256ba8e7c590
 */
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