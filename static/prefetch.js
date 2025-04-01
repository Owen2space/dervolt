// Page prefetching for faster navigation
document.addEventListener('DOMContentLoaded', () => {
    // Only proceed if the user is authenticated
    // (We're already on an authenticated page, so we know the user is logged in)
    
    // List of pages to prefetch
    const pagesToPrefetch = [
        '/dashboard',
        '/help',
        '/settings',
        '/notifications',
        '/transactions'
    ];
    
    // Get the current page path
    const currentPath = window.location.pathname;
    
    // Create prefetch links in the document head
    const head = document.head;
    
    // Only prefetch the pages the user is most likely to visit next
    // (not all pages at once)
    let nextPages = [];
    
    // Determine which pages to prefetch based on current page
    if (currentPath === '/dashboard') {
        // From dashboard, users most likely visit transactions or settings
        nextPages = ['/transactions', '/settings'];
    } else if (currentPath === '/transactions') {
        // From transactions, users likely go back to dashboard
        nextPages = ['/dashboard', '/notifications'];
    } else if (currentPath === '/settings') {
        // From settings, users likely go back to dashboard
        nextPages = ['/dashboard', '/help'];
    } else if (currentPath === '/notifications') {
        // From notifications, users likely go back to dashboard
        nextPages = ['/dashboard', '/transactions'];
    } else if (currentPath === '/help') {
        // From help, users likely go back to dashboard or to settings
        nextPages = ['/dashboard', '/settings'];
    } else {
        // For other pages, only prefetch dashboard
        nextPages = ['/dashboard'];
    }
    
    // Create prefetch links for only the next likely pages
    nextPages.forEach(page => {
        if (page !== currentPath) {
            // Create prefetch link
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = page;
            link.as = 'document';
            head.appendChild(link);
            
            // Don't do additional fetching - the prefetch is enough
            console.log(`Prefetched ${page} for faster navigation`);
        }
    });
    
    // Prefetch critical assets (but fewer of them)
    const assetsToPreload = [
        '/static/dashboard.css',
        '/static/dark-mode.css'
    ];
    
    assetsToPreload.forEach(asset => {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = asset;
        
        // Set appropriate 'as' attribute based on file extension
        if (asset.endsWith('.css')) {
            link.as = 'style';
        } else if (asset.endsWith('.js')) {
            link.as = 'script';
        }
        
        head.appendChild(link);
    });
}); 