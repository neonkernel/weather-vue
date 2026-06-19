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
          primary: '#1e3a5f',
          secondary: '#2d6a9f',
          accent: '#4fc3f7',
          warm: '#ff8c42',
          cool: '#90caf9',
          storm: '#546e7a',
          sunny: '#fdd835',
          card: 'rgba(255, 255, 255, 0.12)',
          'card-hover': 'rgba(255, 255, 255, 0.20)',
          text: {
            primary: '#ffffff',
            secondary: 'rgba(255, 255, 255, 0.75)',
            muted: 'rgba(255, 255, 255, 0.55)',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'temp-lg': ['6rem', { lineHeight: '1', fontWeight: '200' }],
        'temp-md': ['4rem', { lineHeight: '1', fontWeight: '200' }],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-soft': 'pulseSoft 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
      backgroundImage: {
        'gradient-sky': 'linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 40%, #4a90d9 70%, #87ceeb 100%)',
        'gradient-night': 'linear-gradient(135deg, #0a0e27 0%, #1a1a3e 40%, #2d2d6b 100%)',
        'gradient-sunset': 'linear-gradient(135deg, #1a0533 0%, #8b2252 40%, #ff6b35 70%, #ffa07a 100%)',
        'gradient-stormy': 'linear-gradient(135deg, #1c2833 0%, #2c3e50 50%, #4a5568 100%)',
        'gradient-card': 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%)',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
        'glass-sm': '0 4px 16px 0 rgba(31, 38, 135, 0.25)',
        'inner-light': 'inset 0 1px 0 rgba(255, 255, 255, 0.2)',
      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
    },
  },
  plugins: [],
}