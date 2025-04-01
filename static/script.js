// Mobile menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            // Toggle the 'hidden' class
            mobileMenu.classList.toggle('hidden');
            
            // Add slide animation
            if (!mobileMenu.classList.contains('hidden')) {
                mobileMenu.style.maxHeight = mobileMenu.scrollHeight + 'px';
                mobileMenu.style.opacity = '1';
            } else {
                mobileMenu.style.maxHeight = '0';
                mobileMenu.style.opacity = '0';
            }
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInside = mobileMenuButton.contains(event.target) || mobileMenu.contains(event.target);
            
            if (!isClickInside && !mobileMenu.classList.contains('hidden')) {
                mobileMenu.classList.add('hidden');
                mobileMenu.style.maxHeight = '0';
                mobileMenu.style.opacity = '0';
            }
        });
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
                // Close mobile menu if open
                const mobileMenu = document.getElementById('mobile-menu');
                if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                    mobileMenu.classList.add('hidden');
                    mobileMenu.style.maxHeight = '0';
                    mobileMenu.style.opacity = '0';
                }
            }
        });
    });

    // Add scroll animation to elements
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fadeIn');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('section > div').forEach((el) => {
        observer.observe(el);
    });
}); 