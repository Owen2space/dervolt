// Loading Animation for Page Transitions
document.addEventListener('DOMContentLoaded', () => {
    // Create the loading overlay if it doesn't exist
    if (!document.getElementById('page-transition-overlay')) {
        // Create overlay container
        const overlay = document.createElement('div');
        overlay.id = 'page-transition-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0)'; // Transparent background
        overlay.style.zIndex = '9999';
        overlay.style.display = 'none';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.flexDirection = 'column';
        overlay.style.transition = 'opacity 0.3s ease';
        overlay.style.backdropFilter = 'blur(5px)';
        
        // Create loading container for candlesticks
        const loadingContainer = document.createElement('div');
        loadingContainer.id = 'loading-container';
        loadingContainer.style.display = 'flex';
        loadingContainer.style.justifyContent = 'center';
        loadingContainer.style.alignItems = 'center';
        loadingContainer.style.height = '100px';
        loadingContainer.style.marginBottom = '20px';
        
        // Create loading text
        const loadingText = document.createElement('div');
        loadingText.textContent = 'Loading...';
        loadingText.style.fontFamily = 'Poppins, sans-serif';
        loadingText.style.fontSize = '18px';
        loadingText.style.color = '#3b82f6';
        loadingText.style.marginTop = '20px';
        
        // Add elements to DOM
        overlay.appendChild(loadingContainer);
        overlay.appendChild(loadingText);
        document.body.appendChild(overlay);
        
        // Initialize candlestick animation
        initCandlestickAnimation();
    }
    
    // Set up link interception for page transitions
    setupPageTransitions();
    
    // Hide loading screen once the page is fully loaded
    window.addEventListener('load', hidePageLoading);
    
    // Handle page shown after back/forward navigation
    window.addEventListener('pageshow', (event) => {
        // Hide the loader whether we came from cache or not
        hidePageLoading();
    });
});

function initCandlestickAnimation() {
    const container = document.getElementById('loading-container');
    const numCandles = 10;
    const animationDuration = 1000; // milliseconds
    
    function createCandlestick(height, wickHeightTop, wickHeightBottom) {
        const stick = document.createElement('div');
        stick.classList.add('candlestick');
        stick.style.margin = '5px';
        stick.style.width = '10px';
        stick.style.transition = 'opacity 0.3s ease-in-out';
        stick.style.backgroundColor = '#3b82f6';
        stick.style.border = '1px solid #1e40af';
        stick.style.height = `${height}px`;
        stick.style.position = 'relative';
        stick.style.borderRadius = '2px';
        
        if (wickHeightTop > 0) {
            const topWick = document.createElement('div');
            topWick.classList.add('wick');
            topWick.style.backgroundColor = 'black';
            topWick.style.width = '2px';
            topWick.style.position = 'absolute';
            topWick.style.left = '4px';
            topWick.style.height = `${wickHeightTop}px`;
            topWick.style.top = `-${wickHeightTop}px`;
            stick.appendChild(topWick);
        }
        
        if (wickHeightBottom > 0) {
            const bottomWick = document.createElement('div');
            bottomWick.classList.add('wick');
            bottomWick.style.backgroundColor = 'black';
            bottomWick.style.width = '2px';
            bottomWick.style.position = 'absolute';
            bottomWick.style.left = '4px';
            bottomWick.style.height = `${wickHeightBottom}px`;
            bottomWick.style.bottom = `-${wickHeightBottom}px`;
            stick.appendChild(bottomWick);
        }
        
        return stick;
    }
    
    function generateCandlestickData() {
        const data = [];
        for (let i = 0; i < numCandles; i++) {
            const height = Math.floor(Math.random() * 40) + 10; // Random height between 10 and 50
            const wickTop = Math.floor(Math.random() * 10);
            const wickBottom = Math.floor(Math.random() * 10);
            data.push({ height, wickTop, wickBottom });
        }
        return data;
    }
    
    function animateLoading() {
        if (!document.getElementById('loading-container')) return;
        
        const data = generateCandlestickData();
        container.innerHTML = ''; // Clear previous candles
        
        data.forEach((candleData, index) => {
            const stick = createCandlestick(candleData.height, candleData.wickTop, candleData.wickBottom);
            stick.style.opacity = 0;
            container.appendChild(stick);
            
            setTimeout(() => {
                if (stick.parentNode) stick.style.opacity = 1;
            }, (index * animationDuration) / numCandles); // Stagger the appearance
        });
        
        setTimeout(animateLoading, animationDuration); // Repeat the animation
    }
    
    // Start the animation
    animateLoading();
}

function setupPageTransitions() {
    // Track if we're currently in a page transition
    window.isNavigating = false;
    
    // Intercept all internal navigation link clicks
    document.addEventListener('click', (e) => {
        // Find closest anchor tag
        const link = e.target.closest('a');
        
        // Only proceed if this is an internal link to our own site
        if (link && link.href && 
            link.href.startsWith(window.location.origin) && 
            !link.getAttribute('target') && 
            !link.hasAttribute('download') &&
            !e.ctrlKey && !e.metaKey && !e.shiftKey) {
            
            // Check if link is not pointing to the current page
            if (link.href !== window.location.href) {
                e.preventDefault();
                
                // Show loading overlay
                const overlay = document.getElementById('page-transition-overlay');
                overlay.style.display = 'flex';
                overlay.style.opacity = '1';
                
                // Set navigation flag
                window.isNavigating = true;
                
                // Add a small delay to ensure animation is visible
                setTimeout(() => {
                    // Navigate to new page
                    window.location.href = link.href;
                    
                    // Set a failsafe to hide loading if navigation takes too long
                    setTimeout(() => {
                        if (window.isNavigating) {
                            hidePageLoading();
                            window.isNavigating = false;
                        }
                    }, 5000); // Hide after 5 seconds if navigation doesn't complete
                    
                }, 300);
            }
        }
    });
    
    // Handle back/forward navigation
    window.addEventListener('popstate', () => {
        // Don't show loading for back/forward navigation
        // This prevents the infinite loading on back gesture
        hidePageLoading();
        window.isNavigating = false;
    });
}

// Show loading overlay for form submissions too
document.addEventListener('submit', (e) => {
    // Only intercept forms that don't have the 'no-loading' class
    if (!e.target.classList.contains('no-loading')) {
        const overlay = document.getElementById('page-transition-overlay');
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        
        // Set a failsafe timer to hide loading if form submission takes too long
        setTimeout(() => {
            hidePageLoading();
        }, 8000); // 8 seconds timeout for form submissions
    }
});

// Function to manually show the loading overlay
window.showPageLoading = function() {
    const overlay = document.getElementById('page-transition-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        window.isNavigating = true;
    }
};

// Function to manually hide the loading overlay
window.hidePageLoading = function() {
    const overlay = document.getElementById('page-transition-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.style.display = 'none';
            window.isNavigating = false;
        }, 300);
    }
}; 