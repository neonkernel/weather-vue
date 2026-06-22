# 🌤️ Weather Dashboard

A beautiful, responsive weather dashboard built with Vue 3, TypeScript, and Tailwind CSS.

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
│   └── ForecastCard.vue     # Individual forecast day card
├── data/
│   └── mockWeather.ts       # Hardcoded mock weather data
├── types/
│   └── weather.ts           # TypeScript interfaces
├── App.vue                  # Root component
└── main.ts                  # App bootstrap
```

## Setup Instructions

### Prerequisites

- Node.js >= 18.x
- npm >= 9.x

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint

# Format code
npm run format
```

The app will be available at `http://localhost:5173`

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project Foundation & Static UI Shell | ✅ Complete |
| **Phase 2** | Weather API Integration | 🔜 Planned |
| **Phase 3** | Geolocation & Search | 🔜 Planned |
| **Phase 4** | Animations & Polish | 🔜 Planned |
| **Phase 5** | PWA & Offline Support | 🔜 Planned |

## Features (Phase 1)

- 📍 City name and current conditions display
- 🌡️ Temperature with feels-like reading
- 💧 Humidity and wind speed indicators
- 📅 7-day forecast strip with high/low temps
- 🎨 Weather-themed gradient background
- 📱 Fully responsive mobile-first design