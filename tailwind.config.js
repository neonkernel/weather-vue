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
          warm: '#ff8f00',
          hot: '#f4511e',
          cold: '#80d8ff',
          cloud: '#b0bec5',
          storm: '#455a64',
          snow: '#e3f2fd',
          night: '#0d1b2a',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'sky-day': 'linear-gradient(135deg, #1e3a5f 0%, #2d6a9f 50%, #4fc3f7 100%)',
        'sky-sunset': 'linear-gradient(135deg, #1a237e 0%, #b71c1c 50%, #ff8f00 100%)',
        'sky-night': 'linear-gradient(135deg, #0d1b2a 0%, #1a237e 100%)',
        'sky-cloudy': 'linear-gradient(135deg, #455a64 0%, #607d8b 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}