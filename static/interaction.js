// public/interaction.js

document.addEventListener('DOMContentLoaded', () => {
    // Enable JS-only features
    document.documentElement.classList.add('js-enabled');
    
    // Initialize scroll behavior only for JS users
    let lastScrollTop = 0;
    let ticking = false;

    function updateHeader(scrollTop) {
        const navbar = document.querySelector('.nav-header');
        if (!navbar) return;

        const navbarHeight = navbar.offsetHeight;
        const currentOffset = parseFloat(navbar.dataset.offset || '0');
        
        let scrollDelta = scrollTop - lastScrollTop;
        let newOffset = currentOffset - scrollDelta;

        if (newOffset < -navbarHeight) newOffset = -navbarHeight;
        if (newOffset > 0) newOffset = 0;

        navbar.style.transform = `translateY(${newOffset}px)`;
        navbar.dataset.offset = newOffset;
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    }

    // Scroll handler
    window.addEventListener('scroll', () => {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        if (!ticking) {
            window.requestAnimationFrame(() => {
                updateHeader(scrollTop);
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });

    // View Transitions (if supported)
    if ('startViewTransition' in document) {
        document.addEventListener('click', async (e) => {
            const link = e.target.closest('a[href^="/"]');
            if (!link || e.metaKey || e.ctrlKey || e.shiftKey) return;
            
            // Check if this is a transition from grid to detail view
            const isItemCard = link.classList.contains('item-card');
            const currentPath = window.location.pathname;
            const newPath = link.pathname;
            
            // Skip view transitions for grid->detail navigations
            if (isItemCard) {
                // Just do regular navigation
                window.location.href = link.href;
                return;
            }
            
            e.preventDefault();
            
            try {
                await document.startViewTransition(async () => {
                    const response = await fetch(link.href);
                    const html = await response.text();
                    
                    const parser = new DOMParser();
                    const newDoc = parser.parseFromString(html, 'text/html');
                    
                    // Update content
                    document.querySelector('.nav-header')?.replaceWith(newDoc.querySelector('.nav-header'));
                    document.querySelector('.grid-container')?.replaceWith(
                        newDoc.querySelector('.grid-container')
                    );
                    
                    // Reset navbar state for fresh page
                    const newNavbar = document.querySelector('.nav-header');
                    if (newNavbar) {
                        newNavbar.dataset.offset = '0';
                        newNavbar.style.transform = 'translateY(0)';
                    }
                    
                    // Ensure JS class persists
                    document.documentElement.classList.add('js-enabled');
                    
                    // Update URL and title
                    history.pushState(null, '', link.href);
                    document.title = newDoc.title;
                    
                    // Scroll to top after transition
                    window.scrollTo(0, 0);
                    lastScrollTop = 0; // Reset scroll tracking
                });
            } catch (error) {
                console.error('View transition failed:', error);
                window.location.href = link.href;
            }
        });
        
        // Handle browser navigation
        window.addEventListener('popstate', () => {
            location.reload();
        });
    }
});
