# 🌤️ Weather Dashboard

A beautiful, responsive weather dashboard built with Vue 3, TypeScript, and Tailwind CSS.

## Tech Stack

- **Framework**: Vue 3 (Composition API)
- **Language**: TypeScript
- **Bundler**: Vite
- **Styling**: Tailwind CSS
- **Linting**: ESLint + Prettier

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

## Project Structure

```
src/
├── assets/
│   └── styles/
│       └── main.css        # Global styles & Tailwind directives
├── components/
│   ├── WeatherDashboard.vue  # Main dashboard container
│   ├── CurrentWeather.vue    # Current weather display
│   ├── ForecastStrip.vue     # 7-day forecast strip
│   └── ForecastCard.vue      # Single forecast day card
├── data/
│   └── mockWeather.ts        # Hardcoded mock weather data
├── types/
│   └── weather.ts            # TypeScript interfaces
├── App.vue                   # Root component
└── main.ts                   # App bootstrap
```

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project Foundation & Static UI Shell | ✅ Complete |
| **Phase 2** | Weather API Integration | 🔜 Planned |
| **Phase 3** | Geolocation & Search | 🔜 Planned |
| **Phase 4** | Animations & Polish | 🔜 Planned |
| **Phase 5** | PWA & Offline Support | 🔜 Planned |

## Features (Phase 1)

- 🎨 Weather-themed gradient background
- 🌡️ Current weather display with temperature, condition, humidity, and wind
- 📅 7-day forecast strip with high/low temperatures
- 📱 Fully responsive design
- 🔷 Type-safe with TypeScript strict mode