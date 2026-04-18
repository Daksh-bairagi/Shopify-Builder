/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        midnight: '#0A0E27',
        'midnight-light': '#0F1535',
        'midnight-card': '#141830',
        'midnight-border': '#1E2545',
        brand: {
          50: '#eff6ff',
          400: '#60a5fa',
          500: '#3B82F6',
          600: '#2563eb',
          700: '#1E40AF',
        },
        amber: {
          400: '#fbbf24',
          500: '#F59E0B',
          600: '#d97706',
        },
      },
      fontFamily: {
        code: ['"Fira Code"', 'monospace'],
        sans: ['"Fira Sans"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'glow-blue': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-amber': '0 0 30px rgba(245, 158, 11, 0.4)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.3)',
        'glow-red': '0 0 20px rgba(239, 68, 68, 0.3)',
        card: '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(16px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
