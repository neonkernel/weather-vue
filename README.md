# 🌤️ Weather Dashboard

A beautiful, responsive weather dashboard built with Vue 3, TypeScript, and Tailwind CSS.

## Tech Stack

- **Vue 3** — Composition API with `<script setup>`
- **TypeScript** — Strict mode for type safety
- **Vite** — Lightning-fast build tool and dev server
- **Tailwind CSS** — Utility-first styling with custom weather theme
- **ESLint + Prettier** — Code quality and formatting

## Getting Started

### Prerequisites

- Node.js >= 18
- npm >= 9

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

### Lint & Format

```bash
npm run lint
npm run format
```

## Project Structure

```
src/
├── assets/
│   └── styles/
│       └── main.css        # Global styles + Tailwind directives
├── components/
│   ├── CurrentWeather.vue  # Current conditions display
│   ├── ForecastCard.vue    # Single forecast day card
│   ├── ForecastStrip.vue   # 7-day horizontal forecast strip
│   └── WeatherDashboard.vue # Main dashboard container
├── data/
│   └── mockWeather.ts      # Hardcoded mock weather data
├── types/
│   └── weather.ts          # TypeScript interfaces
├── App.vue                 # Root component
└── main.ts                 # App bootstrap
```

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project Foundation & Static UI Shell | ✅ Complete |
| **Phase 2** | API Integration & Live Data | 🔜 Planned |
| **Phase 3** | Search & Geolocation | 🔜 Planned |
| **Phase 4** | Enhanced UX (animations, themes) | 🔜 Planned |
| **Phase 5** | PWA & Offline Support | 🔜 Planned |

## Features (Phase 1)

- 🌡️ Current temperature, condition, and "feels like"
- 💧 Humidity and 💨 wind speed display
- 📅 7-day forecast strip with high/low temperatures
- 📱 Fully responsive mobile-first layout
- 🎨 Weather-themed gradient background

## License

MIT