# 🌤️ Weather Dashboard

A modern, responsive weather dashboard built with Vue 3, TypeScript, and Tailwind CSS.

## Tech Stack

- **Frontend Framework:** Vue 3 (Composition API)
- **Build Tool:** Vite
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Code Quality:** ESLint + Prettier

## Setup Instructions

### Prerequisites

- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd weather-dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint

# Format code
npm run format
```

The app will be available at `http://localhost:5173`

## Project Structure

```
src/
├── assets/
│   └── styles/
│       └── main.css          # Global styles & Tailwind directives
├── components/
│   ├── WeatherDashboard.vue  # Main dashboard container
│   ├── CurrentWeather.vue    # Current conditions display
│   ├── ForecastStrip.vue     # 7-day forecast strip
│   └── ForecastCard.vue      # Individual forecast day card
├── data/
│   └── mockWeather.ts        # Hardcoded mock weather data
├── types/
│   └── weather.ts            # TypeScript interfaces
├── App.vue                   # Root component
└── main.ts                   # App entry point
```

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project Foundation & Static UI Shell | ✅ Complete |
| **Phase 2** | Weather API Integration | 🔜 Planned |
| **Phase 3** | Geolocation & Search | 🔜 Planned |
| **Phase 4** | Animations & Polish | 🔜 Planned |
| **Phase 5** | PWA & Offline Support | 🔜 Planned |

## Phase 1 Details

- ✅ Vite + Vue 3 Composition API + TypeScript setup
- ✅ Tailwind CSS with custom weather-themed color palette
- ✅ Component hierarchy: App → WeatherDashboard → CurrentWeather + ForecastStrip
- ✅ Static placeholder data (no API calls required)
- ✅ ESLint + Prettier configuration
- ✅ Path aliases (@/) configured
- ✅ Responsive mobile-first design
- ✅ TypeScript interfaces for weather data

## License

MIT