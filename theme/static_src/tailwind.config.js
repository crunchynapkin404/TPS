module.exports = {
  content: [
    // Templates
    '../frontend/templates/**/*.html',
    '../../apps/**/*.html',
    '../../frontend/templates/**/*.html',
    // JavaScript
    '../frontend/static/js/**/*.js',
    '../../apps/**/*.js',
    '../../frontend/static/js/**/*.js',
  ],
  darkMode: 'class', // Enable class-based dark mode
  safelist: [
    // Common dark mode classes used in the application
    'dark:bg-gray-800',
    'dark:bg-gray-900',
    'dark:bg-gray-700',
    'dark:bg-gray-600',
    'dark:text-gray-50',
    'dark:text-gray-100',
    'dark:text-gray-200',
    'dark:text-gray-300',
    'dark:text-gray-400',
    'dark:border-gray-600',
    'dark:border-gray-700',
    'dark:hover:bg-gray-700',
    'dark:hover:bg-gray-800',
    'dark:hover:bg-gray-600',
    'dark:hover:text-gray-300',
    'dark:hover:border-gray-600',
    // Calendar specific
    'dark:bg-blue-900',
    'dark:border-blue-800',
    'dark:text-blue-200',
    'dark:text-blue-300',
    'dark:text-blue-400',
    // Assignment blocks
    'dark:text-white',
    'dark:bg-blue-700',
    'dark:bg-green-900',
    'dark:bg-red-900',
    'dark:bg-amber-900',
    'dark:bg-purple-900',
    'dark:bg-orange-900',
  ],
  theme: {
    extend: {
      colors: {
        'tps-primary': '#2563eb',
        'tps-primary-dark': '#1d4ed8',
        'tps-secondary': '#64748b',
        'tps-success': '#059669',
        'tps-warning': '#d97706',
        'tps-danger': '#dc2626',
        'tps-info': '#0284c7',
      },
      fontFamily: {
        'sans': ['Inter', 'ui-sans-serif', 'system-ui'],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
