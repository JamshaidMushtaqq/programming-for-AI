// Image Preview Functionality
function previewImage(event) {
    const reader = new FileReader();
    const preview = document.getElementById('image-preview');
    
    reader.onload = function() {
        preview.src = reader.result;
        preview.style.display = 'block';
    }
    
    reader.readAsDataURL(event.target.files[0]);
}

// Drag and Drop for Editor Page
function setupDragDrop() {
    const dropArea = document.getElementById('drop-area');
    
    if (!dropArea) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupDragDrop();
    
    // Text editing functionality for editor page
    const textInputs = document.querySelectorAll('.text-input');
    if (textInputs.length > 0) {
        textInputs.forEach(input => {
            input.addEventListener('input', updateMemeText);
        });
    }
});

function updateMemeText() {
    const topText = document.getElementById('top-text').value;
    const bottomText = document.getElementById('bottom-text').value;
    
    document.getElementById('meme-top-text').textContent = topText;
    document.getElementById('meme-bottom-text').textContent = bottomText;
}