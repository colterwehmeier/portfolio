// public/interaction.js

document.addEventListener('DOMContentLoaded', () => {
    // Enable JS-only features
    document.documentElement.classList.add('js-enabled');
    
    // Handle legacy hash-based URLs for backward compatibility
    handleLegacyHashUrls();
    
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
    // if ('startViewTransition' in document) {
    //     document.addEventListener('click', async (e) => {
    //         const link = e.target.closest('a[href^="/"]');
    //         if (!link || e.metaKey || e.ctrlKey || e.shiftKey) return;
            
    //         // Check if this is a transition from grid to detail view
    //         const isItemCard = link.classList.contains('item-card');
    //         const currentPath = window.location.pathname;
    //         const newPath = link.pathname;
            
    //         // Skip view transitions for grid->detail navigations
    //         if (isItemCard) {
    //             // Just do regular navigation
    //             window.location.href = link.href;
    //             return;
    //         }
            
    //         e.preventDefault();
            
    //         try {
    //             await document.startViewTransition(async () => {
    //                 const response = await fetch(link.href);
    //                 const html = await response.text();
                    
    //                 const parser = new DOMParser();
    //                 const newDoc = parser.parseFromString(html, 'text/html');
                    
    //                 // Update content
    //                 document.querySelector('.nav-header')?.replaceWith(newDoc.querySelector('.nav-header'));
    //                 document.querySelector('.grid-container')?.replaceWith(
    //                     newDoc.querySelector('.grid-container')
    //                 );
                    
    //                 // Reset navbar state for fresh page
    //                 const newNavbar = document.querySelector('.nav-header');
    //                 if (newNavbar) {
    //                     newNavbar.dataset.offset = '0';
    //                     newNavbar.style.transform = 'translateY(0)';
    //                 }
                    
    //                 // Ensure JS class persists
    //                 document.documentElement.classList.add('js-enabled');
                    
    //                 // Update URL and title
    //                 history.pushState(null, '', link.href);
    //                 document.title = newDoc.title;
                    
    //                 // Scroll to top after transition
    //                 window.scrollTo(0, 0);
    //                 lastScrollTop = 0; // Reset scroll tracking
    //             });
    //         } catch (error) {
    //             console.error('View transition failed:', error);
    //             window.location.href = link.href;
    //         }
    //     });
        
    //     // Handle browser navigation
    //     window.addEventListener('popstate', () => {
    //         location.reload();
    //     });
    // }
});

// Legacy hash URL handler for backward compatibility
function handleLegacyHashUrls() {
    console.log('🔍 Hash URL handler called');
    console.log('Current URL:', window.location.href);
    console.log('Hash:', window.location.hash);
    
    const hash = window.location.hash;
    
    if (!hash || hash === '#') {
        console.log('❌ No hash found or empty hash');
        return;
    }
    
    // Extract the item ID from the hash (remove the #)
    const itemId = hash.substring(1);
    
    // Only proceed if it looks like a valid item ID
    if (!itemId || itemId.includes('/') || itemId.includes('?')) {
        console.log('❌ Invalid item ID format:', itemId);
        return;
    }
    
    console.log('✅ Legacy hash URL detected:', itemId);
    
    // Try to find the item and redirect to new URL structure
    console.log('🌐 Fetching compiled data...');
    fetch('/static/compiled.json')
        .then(response => {
            console.log('📡 Fetch response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('📊 Compiled data loaded, entries found:', data.length);
            const item = data.find(item => item.id === itemId);
            
            if (item && !item.locked) {
                const year = item.year || '0000';
                const newUrl = `/${year}/${itemId}`;
                
                console.log('🎯 Item found:', item.title);
                console.log('📅 Year:', year);
                console.log('🔗 Redirecting to new URL:', newUrl);
                
                // Replace the current URL to avoid back button issues
                window.location.replace(newUrl);
            } else {
                console.log('❌ Item not found or locked:', itemId);
                // Clear the hash but stay on current page
                history.replaceState(null, null, window.location.pathname);
            }
        })
        .catch(error => {
            console.error('💥 Error loading compiled data for legacy redirect:', error);
            // Clear the hash but stay on current page
            history.replaceState(null, null, window.location.pathname);
        });
}
