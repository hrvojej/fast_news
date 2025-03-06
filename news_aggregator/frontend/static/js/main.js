// Main JavaScript file for Article Summarizer

document.addEventListener('DOMContentLoaded', function() {
    console.log('Article Summarizer JS initialized');
    
    // Example function to toggle visibility of elements
    function toggleElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            if (element.style.display === 'none') {
                element.style.display = 'block';
            } else {
                element.style.display = 'none';
            }
        }
    }
    
    // Add event listeners for interactive elements
    const toggleButtons = document.querySelectorAll('.toggle-button');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            toggleElement(targetId);
        });
    });
});
