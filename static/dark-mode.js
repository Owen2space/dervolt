// Dark mode detection and handling
(function() {
  // Detect if browser supports dark mode
  function detectDarkMode() {
    // Check if the browser supports prefers-color-scheme
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return true;
    }
    
    // Check if user has explicitly set dark mode in localStorage
    const userPreference = localStorage.getItem('darkMode');
    if (userPreference === 'true') {
      return true;
    }
    
    return false;
  }

  // Apply dark mode
  function applyDarkMode(isDark) {
    if (isDark) {
      document.body.classList.add('dark-mode');
      localStorage.setItem('darkMode', 'true');
    } else {
      document.body.classList.remove('dark-mode');
      localStorage.setItem('darkMode', 'false');
    }
    
    // Update PWA app theme color meta tag
    const themeColorMeta = document.querySelector('meta[name="theme-color"]');
    if (themeColorMeta) {
      themeColorMeta.setAttribute('content', isDark ? '#121212' : '#ffffff');
    }
  }

  // Function to check if app is in PWA mode
  function isPwaMode() {
    return window.matchMedia('(display-mode: standalone)').matches || 
           window.navigator.standalone || 
           document.referrer.includes('android-app://');
  }
  
  // If in PWA mode, add class to body
  if (isPwaMode()) {
    document.body.classList.add('pwa-mode');
  }

  // Watch for changes to color scheme preference
  if (window.matchMedia) {
    const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    // Apply initial dark mode setting
    applyDarkMode(detectDarkMode());
    
    // Watch for changes
    colorSchemeQuery.addEventListener('change', (e) => {
      applyDarkMode(e.matches);
    });
  }
  
  // Expose dark mode toggle function to global scope
  window.toggleDarkMode = function() {
    const isDarkMode = document.body.classList.contains('dark-mode');
    applyDarkMode(!isDarkMode);
  };
})();

// Ensure this script runs when the DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    // Script already ran on load
  });
} else {
  // DOM is already ready, run script now
  // (The script already self-executes, so we don't need to do anything here)
} 