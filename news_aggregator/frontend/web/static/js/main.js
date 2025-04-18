// Main JavaScript file for site interactions

document.addEventListener('DOMContentLoaded', function() {
    console.log('Main JS initialized');

    // --- Begin dynamic header load ---
    const headerURL = document.location.origin + "/header.html";
    console.log("Fetching header from: " + headerURL);
    fetch(headerURL)
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok: ' + response.statusText);
        }
        return response.text();
    })
    .then(headerHTML => {
        const headerContainer = document.getElementById('site-header');
        if (!headerContainer) return;

        // Inject the fetched header HTML
        headerContainer.innerHTML = headerHTML;

        // --- Reinitialize mobile hamburger menu ---
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

        // Close mobile overlay when clicking outside
        const mobileOverlay = document.getElementById('mobile-menu-overlay');
        if (mobileOverlay) {
            mobileOverlay.addEventListener('click', function(e) {
                if (e.target.id === 'mobile-menu-overlay') {
                    mobileOverlay.style.display = 'none';
                }
            });
        }

        // Mobile submenu accordion toggles
        const mobileCategoryTitles = document.querySelectorAll('.mobile-category-title');
        mobileCategoryTitles.forEach(function(title) {
            title.addEventListener('click', function() {
                const parent = this.closest('.mobile-menu-category');
                if (parent) {
                    parent.classList.toggle('active');
                }
            });
        });

        // --- Desktop “More” dropdown toggle & outside-click close ---
        const moreMenuItem = document.querySelector('.dropdown.more');
        if (moreMenuItem) {
            const moreToggle = moreMenuItem.querySelector('> a');
            moreToggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                moreMenuItem.classList.toggle('open');
            });
    
            // Close “More” panel when any click inside the More menu occurs
            const moreMenu = moreMenuItem.querySelector('.more-menu');
            if (moreMenu) {
                moreMenu.addEventListener('click', function() {
                    moreMenuItem.classList.remove('open');
                });
            }

    
            // Close when clicking outside
            document.addEventListener('click', function(e) {
                if (!moreMenuItem.contains(e.target)) {
                    moreMenuItem.classList.remove('open');
                }
            });
        }
    
        // Always start with “More” closed on a fresh page
        moreMenuItem && moreMenuItem.classList.remove('open');
    


    })
    .catch(error => {
        console.error('Error loading dynamic header:', error);
    });
    // --- End dynamic header load ---

    // -------------------------------
    // 1) General Toggle Utility
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
    // 2) Enhance Entity Displays (tooltips)
    // -------------------------------
    function enhanceEntities() {
        const classes = ['named-individual','roles-categories','orgs-products','location','time-event','artistic','industry','financial','key-actions'];
        classes.forEach(className => {
            document.querySelectorAll(`.${className}`).forEach(el => {
                el.classList.add('entity-hoverable');
                const link = el.querySelector('a');
                if (link && link.href.includes('wikipedia.org')) {
                    const tooltip = document.createElement('span');
                    tooltip.className = 'entity-tooltip';
                    let type = 'Entity';
                    if (className === 'named-individual') type = 'Person';
                    else if (className === 'orgs-products') type = 'Organization';
                    else if (className === 'location') type = 'Location';
                    else if (className === 'time-event') type = 'Time/Event';
                    tooltip.textContent = type;
                    el.appendChild(tooltip);
                }
            });
        });
    }
    enhanceEntities();

    // -------------------------------
    // 3) Image Zoom
    // -------------------------------
    function setupImageZoom() {
        document.querySelectorAll('.article-image img, .featured-image img').forEach(img => {
            img.classList.add('zoomable');
            img.addEventListener('click', function() {
                const modal = document.createElement('div');
                modal.className = 'image-zoom-modal';

                const zoomedImg = document.createElement('img');
                zoomedImg.src = this.src;
                zoomedImg.alt = this.alt;
                zoomedImg.className = 'zoomed-image';

                let caption;
                const figcaption = this.parentNode.querySelector('figcaption');
                if (figcaption) {
                    caption = document.createElement('div');
                    caption.className = 'zoomed-caption';
                    caption.textContent = figcaption.textContent;
                }

                const closeBtn = document.createElement('button');
                closeBtn.className = 'zoom-close-btn';
                closeBtn.innerHTML = '&times;';
                closeBtn.addEventListener('click', e => {
                    e.stopPropagation();
                    document.body.removeChild(modal);
                });

                modal.appendChild(zoomedImg);
                if (caption) modal.appendChild(caption);
                modal.appendChild(closeBtn);
                document.body.appendChild(modal);
                modal.addEventListener('click', () => document.body.removeChild(modal));
            });
        });
    }
    setupImageZoom();

    // -------------------------------
    // 4) Collapsible Sections
    // -------------------------------
    function setupCollapsibles() {
        const sections = [
            { heading: '.entity-overview-heading', content: '.entity-grid', initialState: 'expanded' },
            { heading: '.facts-heading', content: '.facts-container', initialState: 'expanded' }
        ];
        sections.forEach(sec => {
            document.querySelectorAll(sec.heading).forEach(head => {
                const content = head.parentNode.querySelector(sec.content);
                if (!content) return;
                head.classList.add('collapsible-heading');
                content.classList.add('collapsible-content');
                if (sec.initialState === 'collapsed') {
                    content.style.display = 'none';
                    head.classList.add('collapsed');
                }
                const arrow = document.createElement('span');
                arrow.className = 'collapse-arrow';
                arrow.innerHTML = '▼';
                head.appendChild(arrow);
                head.addEventListener('click', function() {
                    if (content.style.display === 'none') {
                        content.style.display = 'block';
                        head.classList.remove('collapsed');
                        arrow.innerHTML = '▼';
                    } else {
                        content.style.display = 'none';
                        head.classList.add('collapsed');
                        arrow.innerHTML = '▶';
                    }
                });
            });
        });
    }
    setupCollapsibles();

    // -------------------------------
    // 5) Responsive Table Wrapping
    // -------------------------------
    function wrapTables() {
        document.querySelectorAll('table').forEach(table => {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        });
    }
    wrapTables();
});

// Dynamically add favicons
(function addFaviconDynamically() {
    const basePath = '/static/favicon/';
    const favicons = [
        { rel: 'icon', type: 'image/x-icon', href: `${basePath}favicon.ico` },
        { rel: 'icon', type: 'image/png', sizes: '96x96', href: `${basePath}favicon-96x96.png` },
        { rel: 'icon', type: 'image/svg+xml', href: `${basePath}favicon.svg` },
        { rel: 'apple-touch-icon', sizes: '180x180', href: `${basePath}apple-touch-icon.png` },
        { rel: 'manifest', href: `${basePath}site.webmanifest` }
    ];
    favicons.forEach(data => {
        const link = document.createElement('link');
        Object.entries(data).forEach(([key, value]) => link.setAttribute(key, value));
        document.head.appendChild(link);
    });
})();
