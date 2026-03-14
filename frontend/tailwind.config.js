/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#d4af37',
          light: '#ebcd5a',
          dark: '#a8891c',
          muted: 'rgba(212,175,55,0.15)',
        },
        charcoal: '#1c1c1c',
        surface: '#111111',
        offwhite: '#f5f5f5',
      },
      fontFamily: {
        serif: ['Georgia', 'Cambria', 'serif'],
        display: ['Georgia', 'serif'],
        sans: ['system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease forwards',
        'slide-up': 'slideUp 0.5s ease forwards',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'shimmer': 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(20px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        glow: { from: { textShadow: '0 0 10px #d4af3740' }, to: { textShadow: '0 0 20px #d4af3780, 0 0 40px #d4af3740' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
    },
  },
  plugins: [],
}
