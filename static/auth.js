/**
 * Authentication and Security Utilities
 * This file contains functions to handle authentication, prevent back button navigation after logout,
 * and ensure secure page access across the application.
 */

// Authentication script
document.addEventListener('DOMContentLoaded', function() {
    console.log('Auth script loaded');
    
    // Only check auth status on authenticated pages
    if (window.location.pathname !== '/login' && 
        window.location.pathname !== '/signup' && 
        window.location.pathname !== '/forgot' &&
        window.location.pathname !== '/') {
        checkAuthStatus();
    }
    
    // Don't prevent the back button from working
    // The following code is intentionally commented out to allow back navigation
    // window.addEventListener('popstate', function(e) {
    //     window.history.pushState(null, null, window.location.href);
    // });
    
    // window.history.pushState(null, null, window.location.href);
    
    // Check authentication status
    function checkAuthStatus() {
        fetch('/api/check-auth')
            .then(response => {
                if (!response.ok) {
                    // If not authenticated, redirect to login page
                    window.location.href = '/login';
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (data === null) return; // Already redirected
                
                // User is authenticated, update UI if needed
                if (data.authenticated === false) {
                    window.location.href = '/login';
                }
            })
            .catch(error => {
                console.error('Auth check error:', error);
            });
    }
});

/**
 * Handles logout by clearing all data and redirecting to login
 */
function handleLogout() {
    clearAllData();
    window.location.href = '/login';
}

/**
 * Clears all local storage, session storage, and cookies
 */
function clearAllData() {
    // Clear storages
    localStorage.clear();
    sessionStorage.clear();
    
    // Clear cookies
    document.cookie.split(";").forEach(function(c) {
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
    });
}

/**
 * Adds cache control headers to prevent page caching
 * This is done via meta tags in the HTML, but this function
 * can be used to add additional cache prevention
 */
function preventCaching() {
    // This is primarily handled via meta tags in the HTML
    // But we can add additional measures here if needed
} 