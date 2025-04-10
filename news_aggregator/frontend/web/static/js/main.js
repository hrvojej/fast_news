// Main JavaScript file for Article Summarizer

document.addEventListener('DOMContentLoaded', function() {
    console.log('Article Summarizer JS initialized');

    // -------------------------------
    // 1) General Toggle Utility (if needed)
    // -------------------------------
    function toggleElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = (element.style.display === 'none') ? 'block' : 'none';
        }
    }
    const toggleButtons = document.querySelectorAll('.toggle-button');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            toggleElement(targetId);
        });
    });

    // -------------------------------
    // 2) Enhance Entity Displays (add tooltips, etc.)
    // -------------------------------
    function enhanceEntities() {
        const entityClasses = [
            'named-individual', 'roles-categories', 'orgs-products',
            'location', 'time-event', 'artistic', 'industry',
            'financial', 'key-actions'
        ];
        entityClasses.forEach(className => {
            const elements = document.querySelectorAll(`.${className}`);
            elements.forEach(element => {
                element.classList.add('entity-hoverable');
                const link = element.querySelector('a');
                if (link && link.href.includes('wikipedia.org')) {
                    const tooltip = document.createElement('span');
                    tooltip.className = 'entity-tooltip';
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
    enhanceEntities();

    // -------------------------------
    // 3) Image Zoom
    // -------------------------------
    function setupImageZoom() {
        const images = document.querySelectorAll('.article-image img, .featured-image img');
        images.forEach(img => {
            img.classList.add('zoomable');
            img.addEventListener('click', function() {
                const modal = document.createElement('div');
                modal.className = 'image-zoom-modal';
                
                const zoomedImg = document.createElement('img');
                zoomedImg.src = this.src;
                zoomedImg.alt = this.alt;
                zoomedImg.className = 'zoomed-image';
                
                let caption = null;
                const figcaption = this.parentNode.querySelector('figcaption');
                if (figcaption) {
                    caption = document.createElement('div');
                    caption.className = 'zoomed-caption';
                    caption.textContent = figcaption.textContent;
                }
                
                const closeBtn = document.createElement('button');
                closeBtn.className = 'zoom-close-btn';
                closeBtn.innerHTML = '&times;';
                closeBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    document.body.removeChild(modal);
                });
                
                modal.appendChild(zoomedImg);
                if (caption) modal.appendChild(caption);
                modal.appendChild(closeBtn);
                document.body.appendChild(modal);
                
                modal.addEventListener('click', function() {
                    document.body.removeChild(modal);
                });
            });
        });
    }
    setupImageZoom();

    // -------------------------------
    // 4) Collapsible Sections
    // -------------------------------
    function setupCollapsibleSections() {
        const sections = [
            { heading: '.entity-overview-heading', content: '.entity-grid', initialState: 'expanded' },
            { heading: '.facts-heading', content: '.facts-container', initialState: 'expanded' }
        ];
        sections.forEach(section => {
            const headings = document.querySelectorAll(section.heading);
            headings.forEach(heading => {
                const content = heading.parentNode.querySelector(section.content);
                if (!content) return;
                heading.classList.add('collapsible-heading');
                content.classList.add('collapsible-content');
                if (section.initialState === 'collapsed') {
                    content.style.display = 'none';
                    heading.classList.add('collapsed');
                }
                const arrow = document.createElement('span');
                arrow.className = 'collapse-arrow';
                arrow.innerHTML = '▼';
                heading.appendChild(arrow);
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
    setupCollapsibleSections();

    // -------------------------------
    // 5) Responsive Table Wrapping
    // -------------------------------
    function wrapTablesForResponsiveness() {
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        });
    }
    wrapTablesForResponsiveness();

    // -------------------------------
    // 6) Mobile Overlay Menu Logic
    // -------------------------------
    // Toggle overlay when hamburger is clicked
    const mobileHamburger = document.querySelector('.hamburger');
    if (mobileHamburger) {
        mobileHamburger.addEventListener('click', function(e) {
            e.stopPropagation();
            const overlay = document.getElementById('mobile-menu-overlay');
            if (overlay) {
                overlay.style.display = (overlay.style.display === 'block') ? 'none' : 'block';
            }
        });
    }
    // Close overlay if clicking outside the mobile menu container
    const mobileOverlay = document.getElementById('mobile-menu-overlay');
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', function(e) {
            if (e.target.id === 'mobile-menu-overlay') {
                mobileOverlay.style.display = 'none';
            }
        });
    }
    // Accordion for mobile submenu toggling
    const mobileCategoryTitles = document.querySelectorAll('.mobile-category-title');
    mobileCategoryTitles.forEach(function(title) {
        title.addEventListener('click', function() {
            const parent = this.closest('.mobile-menu-category');
            if (parent) {
                parent.classList.toggle('active');
            }
        });
    });
});
