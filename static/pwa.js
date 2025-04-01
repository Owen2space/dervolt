// Register Service Worker for PWA functionality
function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            // First try to register from root
            navigator.serviceWorker.register('/service-worker.js')
                .then(registration => {
                    console.log('Service Worker registered with scope:', registration.scope);

                    // Check for updates on page load
                    registration.update();

                    // Listen for service worker updates
                    registration.addEventListener('updatefound', () => {
                        const newWorker = registration.installing;
                        console.log('Service Worker update found!');

                        // Listen for state changes on the new service worker
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                // A new version has been downloaded
                                showUpdateNotification();
                            }
                        });
                    });
                })
                .catch(error => {
                    console.error('Service Worker registration from root failed, trying static path:', error);
                    
                    // Fallback to static directory if root fails
                    navigator.serviceWorker.register('/static/service-worker.js')
                        .then(registration => {
                            console.log('Service Worker registered from static path with scope:', registration.scope);
                        })
                        .catch(fallbackError => {
                            console.error('Service Worker registration failed from both paths:', fallbackError);
                        });
                });

            // Handle communicating with service worker
            navigator.serviceWorker.addEventListener('message', event => {
                if (event.data.action === 'cacheUpdated') {
                    console.log('Cache updated with new content');
                }
            });

            // For existing service workers
            if (navigator.serviceWorker.controller) {
                console.log('Service Worker is already active');
            }
        });
    }
}

// Show notification when a new version is available
function showUpdateNotification() {
    // Create or get notification container
    let notificationContainer = document.getElementById('pwa-update-notification');
    
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'pwa-update-notification';
        notificationContainer.className = 'fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:max-w-sm bg-white p-4 rounded-lg shadow-lg border border-blue-100 z-50 flex items-center justify-between';
        
        const message = document.createElement('p');
        message.className = 'text-sm text-gray-700';
        message.textContent = 'A new version is available.';
        
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'flex space-x-2';
        
        const refreshButton = document.createElement('button');
        refreshButton.className = 'bg-blue-600 text-white px-3 py-1 text-sm rounded hover:bg-blue-700 transition-colors';
        refreshButton.textContent = 'Update Now';
        refreshButton.addEventListener('click', () => {
            // Trigger skipWaiting and reload
            if (navigator.serviceWorker.controller) {
                navigator.serviceWorker.controller.postMessage({ action: 'skipWaiting' });
                
                // After sending the message, listen for the controllerchange event
                navigator.serviceWorker.addEventListener('controllerchange', () => {
                    window.location.reload();
                });
            }
        });
        
        const dismissButton = document.createElement('button');
        dismissButton.className = 'text-gray-500 px-3 py-1 text-sm rounded hover:bg-gray-100 transition-colors';
        dismissButton.textContent = 'Later';
        dismissButton.addEventListener('click', () => {
            document.body.removeChild(notificationContainer);
        });
        
        buttonContainer.appendChild(refreshButton);
        buttonContainer.appendChild(dismissButton);
        
        notificationContainer.appendChild(message);
        notificationContainer.appendChild(buttonContainer);
        
        document.body.appendChild(notificationContainer);
    }
}

// Handle custom install prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent Chrome 67 and earlier from automatically showing the prompt
    e.preventDefault();
    // Store the event so it can be triggered later
    deferredPrompt = e;
    
    // Show the install button if available
    showInstallButton();
});

function showInstallButton() {
    const installButtons = document.querySelectorAll('[data-pwa-install]');
    
    installButtons.forEach(button => {
        button.classList.remove('hidden');
        
        // Ensure we don't add multiple event listeners
        button.removeEventListener('click', handleInstallClick);
        button.addEventListener('click', handleInstallClick);
    });
}

function handleInstallClick(e) {
    // Hide the installation button
    e.target.classList.add('hidden');
    
    // Show the browser install prompt
    if (deferredPrompt) {
        deferredPrompt.prompt();
        
        // Wait for the user to respond to the prompt
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted the install prompt');
            } else {
                console.log('User dismissed the install prompt');
                // Show the button again
                e.target.classList.remove('hidden');
            }
            // Clear the deferred prompt variable
            deferredPrompt = null;
        });
    }
}

// Check offline status and show appropriate UI
function updateOnlineStatus() {
    const statusIndicator = document.getElementById('offline-status');
    
    if (!statusIndicator) {
        return;
    }
    
    if (navigator.onLine) {
        statusIndicator.classList.add('hidden');
    } else {
        statusIndicator.classList.remove('hidden');
    }
}

window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);

// Initialize PWA features when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    registerServiceWorker();
    updateOnlineStatus();
    
    // Create offline status indicator if it doesn't exist
    if (!document.getElementById('offline-status')) {
        const statusIndicator = document.createElement('div');
        statusIndicator.id = 'offline-status';
        statusIndicator.className = 'fixed top-0 inset-x-0 bg-yellow-500 text-white text-center py-1 z-50 hidden';
        statusIndicator.textContent = 'You are currently offline. Some features may be unavailable.';
        document.body.insertBefore(statusIndicator, document.body.firstChild);
    }
}); 