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
          accent: '#56b4e9',
          light: '#a8d8ea',
          card: 'rgba(255, 255, 255, 0.12)',
          'card-border': 'rgba(255, 255, 255, 0.2)',
        },
        sky: {
          dawn: '#ff9a7b',
          day: '#56b4e9',
          dusk: '#7b5ea7',
          night: '#0d1b2a',
        },
        temp: {
          hot: '#ef4444',
          warm: '#f97316',
          mild: '#eab308',
          cool: '#3b82f6',
          cold: '#8b5cf6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'weather-gradient': 'linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 50%, #56b4e9 100%)',
        'card-glass': 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0.05) 100%)',
        'sunrise-gradient': 'linear-gradient(135deg, #1e3a5f 0%, #7b5ea7 40%, #ff9a7b 100%)',
        'sunset-gradient': 'linear-gradient(135deg, #0d1b2a 0%, #7b5ea7 50%, #ff9a7b 100%)',
      },
      backdropBlur: {
        xs: '2px',
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
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
}