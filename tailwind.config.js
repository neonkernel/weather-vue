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
          cool: '#74b9ff',
          storm: '#636e72',
          sunny: '#fdcb6e',
          cloudy: '#b2bec3',
          bg: {
            from: '#0f2027',
            via: '#203a43',
            to: '#2c5364',
          },
          card: 'rgba(255, 255, 255, 0.1)',
          'card-hover': 'rgba(255, 255, 255, 0.18)',
          text: {
            primary: '#ffffff',
            secondary: 'rgba(255,255,255,0.75)',
            muted: 'rgba(255,255,255,0.5)',
          },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
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
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}