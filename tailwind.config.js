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
          cool: '#a8d8ea',
          storm: '#4a4e69',
          sunny: '#ffd166',
          card: 'rgba(255, 255, 255, 0.12)',
          'card-hover': 'rgba(255, 255, 255, 0.2)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
      backgroundImage: {
        'gradient-day': 'linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 50%, #4fc3f7 100%)',
        'gradient-night': 'linear-gradient(135deg, #0d1b2a 0%, #1e3a5f 50%, #2d6a9f 100%)',
        'gradient-sunset': 'linear-gradient(135deg, #1e3a5f 0%, #8b3a62 50%, #ff8c42 100%)',
        'gradient-cloudy': 'linear-gradient(135deg, #4a4e69 0%, #6b7fa3 50%, #a8d8ea 100%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
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
      },
    },
  },
  plugins: [],
}