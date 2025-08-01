/**
 * Base JavaScript for TPS Application
 * Handles Alpine.js initialization and global functionality
 */

// Alpine.js Global Store Initialization
document.addEventListener('alpine:init', () => {
    // Global notification store
    Alpine.store('notifications', {
        items: [],
        
        add(notification) {
            const id = Date.now();
            this.items.push({ ...notification, id });
            
            // Auto-remove after delay
            const delay = notification.type === 'error' ? 5000 : 3000;
            setTimeout(() => this.remove(id), delay);
        },
        
        remove(id) {
            this.items = this.items.filter(item => item.id !== id);
        }
    });
    
    // Global theme store
    Alpine.store('theme', {
        dark: localStorage.getItem('theme') === 'dark' || 
             (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches),
             
        toggle() {
            this.dark = !this.dark;
            localStorage.setItem('theme', this.dark ? 'dark' : 'light');
            document.documentElement.classList.toggle('dark', this.dark);
        }
    });
});

// Custom event listener for global notifications
document.addEventListener('show-notification', (e) => {
    if (window.Alpine && Alpine.store('notifications')) {
        Alpine.store('notifications').add(e.detail);
    }
});

// Accessibility enhancements
document.addEventListener('DOMContentLoaded', () => {
    // Add keyboard navigation for card elements
    const clickableCards = document.querySelectorAll('[role="button"]');
    clickableCards.forEach(card => {
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                card.click();
            }
        });
    });

    // Enhanced form validation
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
                
                // Find and focus first invalid field
                const firstInvalidField = form.querySelector(':invalid');
                if (firstInvalidField) {
                    firstInvalidField.focus();
                    firstInvalidField.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        });

        // Real-time validation feedback
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                validateField(input);
            });

            input.addEventListener('input', () => {
                if (input.classList.contains('border-red-300')) {
                    validateField(input);
                }
            });
        });
    });

    // Field validation helper
    function validateField(field) {
        const isValid = field.checkValidity();
        const errorId = field.getAttribute('aria-describedby')?.split(' ').find(id => id.includes('error'));
        const errorElement = errorId ? document.getElementById(errorId) : null;
        
        if (isValid) {
            field.classList.remove('border-red-300', 'text-red-900', 'focus:ring-red-500', 'focus:border-red-500');
            field.classList.add('border-gray-300', 'focus:ring-blue-500', 'focus:border-blue-500');
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.classList.add('hidden');
            }
        } else {
            field.classList.add('border-red-300', 'text-red-900', 'focus:ring-red-500', 'focus:border-red-500');
            field.classList.remove('border-gray-300', 'focus:ring-blue-500', 'focus:border-blue-500');
            if (errorElement) {
                errorElement.textContent = field.validationMessage;
                errorElement.classList.remove('hidden');
            }
        }
    }

    // Loading state management
    window.showLoadingState = (element, text = 'Loading...') => {
        const originalContent = element.innerHTML;
        element.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${text}
        `;
        element.disabled = true;
        
        return () => {
            element.innerHTML = originalContent;
            element.disabled = false;
        };
    };
});

// Utility functions
window.TPS = window.TPS || {};

window.TPS.utils = {
    // CSRF token helper
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.querySelector('meta[name="csrf-token"]')?.content || '';
    },

    // API helper with loading states and error handling
    async apiCall(url, options = {}) {
        const defaultOptions = {
            headers: {
                'X-CSRFToken': this.getCsrfToken(),
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, { ...options, ...defaultOptions });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API call failed:', error);
            document.dispatchEvent(new CustomEvent('show-notification', {
                detail: { message: error.message, type: 'error' }
            }));
            throw error;
        }
    },

    // Format date helper
    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            ...options
        };
        return new Intl.DateTimeFormat(document.documentElement.lang || 'en', defaultOptions).format(new Date(date));
    },

    // Debounce helper
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};