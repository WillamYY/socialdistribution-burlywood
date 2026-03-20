/**
 * This JavaScript makes any element with class clickable behave like a link 
 * by reading a URL stored in data-url and redirecting the browser when it is clicked.
 * US#79: Only navigate to same-origin URLs to prevent XSS.
 * ChatGPT, OpenAI, 2026-03-12, https://chatgpt.com/share/69abd12e-d60c-8012-9314-256ba8e7c590
 */
document.addEventListener("DOMContentLoaded", function() {
    const clickableElements = document.querySelectorAll('.clickable');

    function isSameOrigin(url) {
        if (!url || typeof url !== 'string') return false;
        if (url.startsWith('/') && !url.startsWith('//')) return true;  // relative URL
        try {
            const link = document.createElement('a');
            link.href = url;
            return link.hostname === window.location.hostname &&
                   link.protocol === window.location.protocol;
        } catch (_) {
            return false;
        }
    }

    clickableElements.forEach(el => {
        el.addEventListener('click', function(event) {
            event.stopPropagation();
            const url = this.dataset.url;
            if (!url || typeof url !== 'string') return;
            if (this.dataset.remote === 'true') {
                window.open(url, '_blank', 'noopener,noreferrer');
            } else if (isSameOrigin(url)) {
                window.location.href = url;
            }
        });
    });

    // Entry form toggle behavior
    const select = document.getElementById("contentTypeSelect");
    const textSection = document.getElementById("textSection");
    const imageSection = document.getElementById("imageSection");
    const textInput = document.getElementById("textContentInput");
    const imageInput = document.getElementById("imageInput");

    if (select && textSection && imageSection) {
        function toggleSections() {
            const value = select.value || "";
            const isImage = value === "image" || value.startsWith("image/");

            textSection.style.display = isImage ? "none" : "";
            imageSection.style.display = isImage ? "" : "none";

            if (textInput) {
                textInput.disabled = isImage;
            }

            if (imageInput) {
                imageInput.disabled = !isImage;
                imageInput.required = isImage;
                if (!isImage) {
                    imageInput.value = "";
                }
            }
        }

        toggleSections();
        select.addEventListener("change", toggleSections);
    }
});