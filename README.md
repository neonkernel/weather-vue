# 🌤️ Weather Dashboard

A modern, responsive weather dashboard built with Vue 3, TypeScript, and Tailwind CSS.

## Tech Stack

- **Framework**: Vue 3 (Composition API)
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Code Quality**: ESLint + Prettier

## Project Structure

```
src/
├── assets/
│   └── styles/
│       └── main.css        # Global styles & Tailwind directives
├── components/
│   ├── WeatherDashboard.vue # Main dashboard container
│   ├── CurrentWeather.vue   # Current conditions display
│   ├── ForecastStrip.vue    # 7-day forecast strip
│   └── ForecastCard.vue     # Single forecast day card
├── data/
│   └── mockWeather.ts       # Hardcoded mock weather data
├── types/
│   └── weather.ts           # TypeScript interfaces
├── App.vue                  # Root component
└── main.ts                  # App entry point
```

## Setup Instructions

### Prerequisites

- Node.js >= 18.x
- npm >= 9.x

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd weather-dashboard

# Install dependencies
npm install

# Start development server
npm run dev
```

### Available Scripts

```bash
npm run dev        # Start Vite dev server (http://localhost:5173)
npm run build      # Production build
npm run preview    # Preview production build
npm run lint       # Run ESLint
npm run format     # Run Prettier formatter
npm run type-check # TypeScript type checking
```

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project Foundation & Static UI Shell | ✅ Complete |
| **Phase 2** | API Integration (OpenWeatherMap) | 🔜 Planned |
| **Phase 3** | Search & Geolocation | 🔜 Planned |
| **Phase 4** | Animations & Polish | 🔜 Planned |
| **Phase 5** | PWA & Offline Support | 🔜 Planned |

## Phase 1 Details

- Vite + Vue 3 Composition API + TypeScript project scaffold
- Tailwind CSS with custom weather-themed color palette
- Component hierarchy: `App` → `WeatherDashboard` → `CurrentWeather` + `ForecastStrip` → `ForecastCard`
- Hardcoded mock data for immediate visual review
- ESLint + Prettier configured for code quality
- Path aliases (`@/`) configured in Vite and TypeScript

## License

MIT