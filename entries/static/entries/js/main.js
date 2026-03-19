/**
 * This JavaScript makes any element with class clickable behave like a link 
 * by reading a URL stored in data-url and redirecting the browser when it is clicked.
 * US#79: Only navigate to same-origin URLs to prevent XSS.
 * ChatGPT, OpenAI, 2026-03-12, https://chatgpt.com/share/69abd12e-d60c-8012-9314-256ba8e7c590
 * 
 * Handle different UI behaviors for different toggles.
 * Handle the visibilities of different sections accordingly.
 */
document.addEventListener("DOMContentLoaded", function() {
    const clickableElements = document.querySelectorAll('.clickable');

    /**
     * Validate if a URL is safe to redirect to.
     */
    function isSameOrigin(url) {
        if (!url || typeof url !== 'string') return false;
        if (url.startsWith('/') && !url.startsWith('//')) return true;  // relative URL
        try {
            // Use the DOM to parse the URL by creating a temporary anchor element
            const link = document.createElement('a');
            link.href = url;
            
            // Compare the parsed components against the current window's location
            // This enforces the Same-Origin Policy
            return link.hostname === window.location.hostname &&
                   link.protocol === window.location.protocol;
        } catch (_) {
            return false;
        }
    }

    // Attach click listeners to all .clickable elements
    clickableElements.forEach(el => {
        el.addEventListener('click', function(event) {
            // Prevent the click event from further propagation to parent DOM elements
            event.stopPropagation();
            const url = this.dataset.url;
            if (url && isSameOrigin(url)) {
                window.location.href = url; // Perform the redirection
            }
        });
    });

    // Entry form toggle behavior
    const select = document.getElementById("contentTypeSelect");
    const textSection = document.getElementById("textSection");
    const imageSection = document.getElementById("imageSection");

    const textInput = document.getElementById("textContentInput");
    const imageInput = document.getElementById("imageInput");

    // UI Feedback elements for Markdown
    const markdownHelpBox = document.getElementById("markdownHelpBox");
    const markdownHintBox = document.getElementById("markdownHintBox");
    const markdownPreviewBox = document.getElementById("markdownPreviewBox");
    const markdownPreviewContent = document.getElementById("markdownPreviewContent");

    // Ensure essential form elements exist before initializing logic
    if (select && textSection && imageSection) {
        
        /**
         * Convert raw text into safe HTML entities.
         * Prevent XSS when rendering user-generated content into .innerHTML.
         */
        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text; // Browser handles encoding
            return div.innerHTML; // Returns the safe string
        }

        /**
         * Validate a string for underlying Markdown image syntax errors.
         * Return a descriptive error string or an empty string if valid.
         */
        function validateMarkdownImageSyntax(value) {
            // Check if user probably wants to use Markdown image syntax
            if (!value || !value.includes("![")) {
                return "";
            }

            // If image marker ![ exists, but no proper ( after it
            const missingParenPattern = /!\[[^\]]*\](?!\()/;
            if (missingParenPattern.test(value)) {
                return "Invalid Markdown image syntax. Use the format: ![alt text](url)";
            }

            // If no image URL in ()
            const emptyUrlPattern = /!\[[^\]]*\]\(\s*\)/;
            if (emptyUrlPattern.test(value)) {
                return "Markdown image URL cannot be empty. Use the format: ![alt text](url)";
            }

            // If not enclose the URL with )
            const openPattern = /!\[[^\]]*\]\(/g;
            let match;
            while ((match = openPattern.exec(value)) !== null) {
                const remaining = value.slice(match.index + match[0].length);
                if (!remaining.includes(")")) {
                    return "Markdown image link is not enclosed with ')'. Use the format: ![alt text](url)";
                }
            }
            
            // Otherwise valid syntax
            return "";
        }

        /**
         * Use Regex Capturing Groups to extract data from Markdown.
         * Return an array of objects: { alt: string, url: string }
         */
        function extractMarkdownImages(value) {
            // Note: Every regex match in JS is represented as [fullMatch, captureGroup1, captureGroup2, ...]
            const matches = [...value.matchAll(/!\[([^\]]*)\]\(([^)\s]+)\)/g)];
            // Decompose each matched pattern into alt and url
            return matches.map(match => ({
                alt: match[1],
                url: match[2]
            }));
        }

        /**
         * Update the visibility of help boxes and the live preview.
         */
        function updateMarkdownUi() {
            const isMarkdown = select.value === "text/markdown";
            const isImage = select.value === "image" || select.value.startsWith("image/");
            const value = textInput ? textInput.value : "";

            if (!markdownHelpBox || !markdownHintBox || !markdownPreviewBox || !markdownPreviewContent) {
                return;
            }

            // Hide all Markdown-related UI if the mode is not Markdown (like Image toggle)
            if (!isMarkdown || isImage || !textInput || textInput.disabled) {
                markdownHelpBox.style.display = "none";
                markdownHintBox.style.display = "none";
                markdownPreviewBox.style.display = "none";
                markdownPreviewContent.innerHTML = "";
                return;
            }

            // Display general Markdown instructions
            markdownHelpBox.style.display = "block";

            // Update error hints based on real-time validation
            const issue = validateMarkdownImageSyntax(value);
            if (issue) {
                markdownHintBox.textContent = issue;
                markdownHintBox.style.display = "block";
            } else {
                markdownHintBox.textContent = "";
                markdownHintBox.style.display = "none";
            }

            // Render live preview of images found in the text
            const images = extractMarkdownImages(value);
            if (images.length > 0) {
                // Map image data to <img> tags, ensuring URLs and Alts are escaped for safety
                markdownPreviewContent.innerHTML = images
                    .map(img => `<img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.alt)}">`)
                    .join("");
                markdownPreviewBox.style.display = "block";
            } else {
                markdownPreviewContent.innerHTML = "";
                markdownPreviewBox.style.display = "none";
            }
        }

        /**
         * Manage DOM visibility based on the selected content type.
         */
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

            // Sync the Markdown UI with the new section state
            updateMarkdownUi();
        }

        toggleSections();
        select.addEventListener("change", toggleSections);

        if (textInput) {
            textInput.addEventListener("input", updateMarkdownUi);
        }
    }
});