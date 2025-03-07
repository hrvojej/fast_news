// Main JavaScript file for Article Summarizer

document.addEventListener('DOMContentLoaded', function() {
    console.log('Article Summarizer JS initialized');
    
    // Toggle visibility of elements
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
    
    // Add event listeners for toggle buttons
    const toggleButtons = document.querySelectorAll('.toggle-button');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            toggleElement(targetId);
        });
    });
    
    // Enhance entity displays with hover effects
    enhanceEntities();
    
    // Add image zooming capabilities
    setupImageZoom();
    
    // Setup collapsible sections
    setupCollapsibleSections();
    
    // Handle mobile navigation
    setupMobileNav();
});

/**
 * Enhances entity elements with hover effects and tooltips
 */
function enhanceEntities() {
    // Entity classes to enhance
    const entityClasses = [
        'named-individual', 'roles-categories', 'orgs-products',
        'location', 'time-event', 'artistic', 'industry', 
        'financial', 'key-actions'
    ];
    
    // Add hover effects to entities
    entityClasses.forEach(className => {
        const elements = document.querySelectorAll(`.${className}`);
        elements.forEach(element => {
            // Add hover class for CSS targeting
            element.classList.add('entity-hoverable');
            
            // Add tooltip if it's a Wikipedia link
            const link = element.querySelector('a');
            if (link && link.href.includes('wikipedia.org')) {
                const entityName = element.textContent.trim();
                
                // Create tooltip with entity type
                const tooltip = document.createElement('span');
                tooltip.className = 'entity-tooltip';
                
                // Determine entity type from class
                let entityType = "Entity";
                if (className === 'named-individual') entityType = "Person";
                else if (className === 'orgs-products') entityType = "Organization";
                else if (className === 'location') entityType = "Location";
                else if (className === 'time-event') entityType = "Time/Event";
                
                tooltip.textContent = entityType;
                element.appendChild(tooltip);
            }
        });
    });
}

/**
 * Sets up image zoom functionality
 */
function setupImageZoom() {
    const images = document.querySelectorAll('.article-image img, .featured-image img');
    
    images.forEach(img => {
        // Add zoom class for CSS styling
        img.classList.add('zoomable');
        
        // Add click event for zooming
        img.addEventListener('click', function() {
            // Create modal for zoomed image
            const modal = document.createElement('div');
            modal.className = 'image-zoom-modal';
            
            // Create zoomed image
            const zoomedImg = document.createElement('img');
            zoomedImg.src = this.src;
            zoomedImg.alt = this.alt;
            zoomedImg.className = 'zoomed-image';
            
            // Create caption if there is one
            let caption = null;
            const figcaption = this.parentNode.querySelector('figcaption');
            if (figcaption) {
                caption = document.createElement('div');
                caption.className = 'zoomed-caption';
                caption.textContent = figcaption.textContent;
            }
            
            // Create close button
            const closeBtn = document.createElement('button');
            closeBtn.className = 'zoom-close-btn';
            closeBtn.innerHTML = '&times;';
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                document.body.removeChild(modal);
            });
            
            // Add elements to modal
            modal.appendChild(zoomedImg);
            if (caption) modal.appendChild(caption);
            modal.appendChild(closeBtn);
            
            // Add modal to body
            document.body.appendChild(modal);
            
            // Close modal when clicking outside the image
            modal.addEventListener('click', function() {
                document.body.removeChild(modal);
            });
        });
    });
}

/**
 * Sets up collapsible sections for long articles
 */
function setupCollapsibleSections() {
    // Make entity overview and facts sections collapsible
    const sections = [
        { 
            heading: '.entity-overview-heading', 
            content: '.entity-grid',
            initialState: 'expanded' 
        },
        { 
            heading: '.facts-heading', 
            content: '.facts-container',
            initialState: 'expanded' 
        }
    ];
    
    sections.forEach(section => {
        const headings = document.querySelectorAll(section.heading);
        
        headings.forEach(heading => {
            // Find the content section
            const content = heading.parentNode.querySelector(section.content);
            if (!content) return;
            
            // Add collapsible class
            heading.classList.add('collapsible-heading');
            content.classList.add('collapsible-content');
            
            // Set initial state
            if (section.initialState === 'collapsed') {
                content.style.display = 'none';
                heading.classList.add('collapsed');
            }
            
            // Add collapse/expand arrow
            const arrow = document.createElement('span');
            arrow.className = 'collapse-arrow';
            arrow.innerHTML = '▼';
            heading.appendChild(arrow);
            
            // Add click handler
            heading.addEventListener('click', function() {
                if (content.style.display === 'none') {
                    content.style.display = 'block';
                    heading.classList.remove('collapsed');
                    arrow.innerHTML = '▼';
                } else {
                    content.style.display = 'none';
                    heading.classList.add('collapsed');
                    arrow.innerHTML = '▶';
                }
            });
        });
    });
}

/**
 * Sets up mobile navigation functionality
 */
function setupMobileNav() {
    const mobileMenuBtn = document.querySelector('.mobile-menu-button');
    const mainNav = document.querySelector('.main-nav');
    
    if (mobileMenuBtn && mainNav) {
        mobileMenuBtn.addEventListener('click', function() {
            mainNav.classList.toggle('mobile-visible');
        });
    }
    
    // Add responsive table handling
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
}