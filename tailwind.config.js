/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        weather: {
          // Sky blues
          'sky-light': '#87CEEB',
          'sky': '#4A90D9',
          'sky-dark': '#1e3a5f',
          // Night / deep atmosphere
          'night': '#0f1f3d',
          'dusk': '#2c3e6e',
          // Accent colors
          'sun': '#FFD700',
          'sun-warm': '#FFA500',
          'cloud': '#B0C4DE',
          'rain': '#4682B4',
          'snow': '#E0F0FF',
          'storm': '#4a4a6a',
        },
        // Semantic aliases
        primary: {
          50:  '#e8f4fd',
          100: '#c5e2f9',
          200: '#9dcef4',
          300: '#6fb8ef',
          400: '#4aa8ec',
          500: '#2598e8',
          600: '#1e87d4',
          700: '#1571b9',
          800: '#0d5c9e',
          900: '#003d78',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'sky-gradient': 'linear-gradient(135deg, #1e3a5f 0%, #2c5282 40%, #2b6cb0 70%, #3182ce 100%)',
        'night-gradient': 'linear-gradient(135deg, #0f1f3d 0%, #1a2f5e 50%, #243b6e 100%)',
        'sunset-gradient': 'linear-gradient(135deg, #7c3aed 0%, #db2777 40%, #f97316 70%, #eab308 100%)',
        'card-glass': 'linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%)',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.2)',
        'glass-sm': '0 4px 16px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255,255,255,0.15)',
        'glow': '0 0 20px rgba(66, 153, 225, 0.4)',
      },
      backdropBlur: {
        'xs': '2px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.6s ease-out',
        'slide-up': 'slideUp 0.5s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}