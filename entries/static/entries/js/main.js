/**
 * Validate if a URL is safe to redirect to.
 * US#79: Only navigate to same-origin URLs to prevent XSS.
 * ChatGPT, OpenAI, 2026-03-12, https://chatgpt.com/share/69abd12e-d60c-8012-9314-256ba8e7c590
 */
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

/**
 * Convert raw text into safe HTML entities.
 * Prevent XSS when rendering user-generated content into .innerHTML.
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Build a valid Markdown syntax for rendering an image.
 */
function buildMarkdownImage(alt, url) {
    const safeAlt = (alt || "").replace(/\]/g, "");
    return `![${safeAlt}](${url})`;
}

/**
 * Validate a string for underlying Markdown image syntax errors.
 * Return a descriptive error string or an empty string if valid.
 */
function validateMarkdownImageSyntax(value) {
    if (!value || !value.includes("![")) {
        return "";
    }

    const missingParenPattern = /!\[[^\]]*\](?!\()/;
    if (missingParenPattern.test(value)) {
        return "Invalid Markdown image syntax. Use the format: ![alt text](url)";
    }

    const emptyUrlPattern = /!\[[^\]]*\]\(\s*\)/;
    if (emptyUrlPattern.test(value)) {
        return "Markdown image URL cannot be empty. Use the format: ![alt text](url)";
    }

    const openPattern = /!\[[^\]]*\]\(/g;
    let match;
    while ((match = openPattern.exec(value)) !== null) {
        const remaining = value.slice(match.index + match[0].length);
        if (!remaining.includes(")")) {
            return "Markdown image link is not enclosed with ')'. Use the format: ![alt text](url)";
        }
    }

    return "";
}

/**
 * Use Regex Capturing Groups to extract data from Markdown.
 * Return an array of objects: { alt: string, url: string }
 */
function extractMarkdownImages(value) {
    const matches = [...(value || "").matchAll(/!\[([^\]]*)\]\(([^)\s]+)\)/g)];
    return matches.map(match => ({
        alt: match[1],
        url: match[2]
    }));
}

/**
 * This JavaScript makes any element with class clickable behave like a link
 * by reading a URL stored in data-url and redirecting the browser when it is clicked.
 * US#79: Only navigate to same-origin URLs to prevent XSS.
 * Remote URLs (data-remote="true") open in new tab.
 * ChatGPT, OpenAI, 2026-03-12, https://chatgpt.com/share/69abd12e-d60c-8012-9314-256ba8e7c590
 */
document.addEventListener("DOMContentLoaded", function() {
    document.body.addEventListener('click', function(event) {
        const clickableEl = event.target.closest('.clickable');

        if (event.target.closest('a, button, input, textarea, select')) {
            return;
        }

        if (clickableEl) {
            const url = clickableEl.dataset.url;
            if (!url || typeof url !== 'string') return;
            if (clickableEl.dataset.remote === 'true') {
                event.preventDefault();
                window.open(url, '_blank', 'noopener,noreferrer');
            } else if (isSameOrigin(url) && !url.startsWith('javascript:')) {
                event.preventDefault();
                window.location.href = url;
            }
        }
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
    const markdownImageUrlInput = document.getElementById("markdownImageUrlInput");
    const markdownImageAltInput = document.getElementById("markdownImageAltInput");
    const insertMarkdownImageBtn = document.getElementById("insertMarkdownImageBtn");

    if (select && textSection && imageSection) {
        /**
         * Record cursor position and insert text there.
         */
        function insertAtCursor(textarea, textToInsert) {
            const start = textarea.selectionStart ?? textarea.value.length;
            const end = textarea.selectionEnd ?? textarea.value.length;
            const before = textarea.value.slice(0, start);
            const after = textarea.value.slice(end);

            textarea.value = before + textToInsert + after;

            const newCursorPos = start + textToInsert.length;
            textarea.focus();
            textarea.setSelectionRange(newCursorPos, newCursorPos);
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

            if (!isMarkdown || isImage || !textInput || textInput.disabled) {
                markdownHelpBox.style.display = "none";
                markdownHintBox.style.display = "none";
                markdownPreviewBox.style.display = "none";
                markdownPreviewContent.innerHTML = "";
                return;
            }

            markdownHelpBox.style.display = "block";

            const issue = validateMarkdownImageSyntax(value);
            if (issue) {
                markdownHintBox.textContent = issue;
                markdownHintBox.style.display = "block";
            } else {
                markdownHintBox.textContent = "";
                markdownHintBox.style.display = "none";
            }

            const images = extractMarkdownImages(value);
            if (images.length > 0) {
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

            updateMarkdownUi();
        }

        select.addEventListener("change", toggleSections);

        if (textInput) {
            textInput.addEventListener("input", updateMarkdownUi);
        }

        if (insertMarkdownImageBtn && textInput) {
            insertMarkdownImageBtn.addEventListener("click", function() {
                const url = markdownImageUrlInput ? markdownImageUrlInput.value.trim() : "";
                const alt = markdownImageAltInput ? markdownImageAltInput.value.trim() : "";

                if (!url) {
                    if (markdownHintBox) {
                        markdownHintBox.textContent = "Please enter an image URL before inserting.";
                        markdownHintBox.style.display = "block";
                    }
                    return;
                }

                if (!/^https?:\/\//i.test(url) && !url.startsWith('/')) {
                    if (markdownHintBox) {
                        markdownHintBox.textContent = "Image URL must start with http://, https://, or /";
                        markdownHintBox.style.display = "block";
                    }
                    return;
                }

                const markdownImage = buildMarkdownImage(alt, url);
                insertAtCursor(textInput, markdownImage);

                if (markdownImageUrlInput) markdownImageUrlInput.value = "";
                if (markdownImageAltInput) markdownImageAltInput.value = "";

                updateMarkdownUi();
            });
        }

        toggleSections();
    }
});
