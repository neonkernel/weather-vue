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
│       └── main.css          # Global styles & Tailwind directives
├── components/
│   ├── CurrentWeather.vue    # Current conditions display
│   ├── ForecastCard.vue      # Single forecast day card
│   ├── ForecastStrip.vue     # 7-day forecast strip
│   └── WeatherDashboard.vue  # Main dashboard container
├── data/
│   └── mockWeather.ts        # Hardcoded mock weather data
├── types/
│   └── weather.ts            # TypeScript interfaces
├── App.vue                   # Root component
└── main.ts                   # App bootstrap
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

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Project Foundation & Static UI Shell | ✅ Complete |
| **Phase 2** | API Integration & Live Weather Data | 🔜 Planned |
| **Phase 3** | Location Search & Geolocation | 🔜 Planned |
| **Phase 4** | Animations, PWA & Offline Support | 🔜 Planned |
| **Phase 5** | Unit Tests & CI/CD Pipeline | 🔜 Planned |

## Features (Phase 1)

- 🌡️ Current temperature and conditions display
- 📅 7-day forecast strip with high/low temperatures
- 💨 Wind speed and humidity indicators
- 🎨 Weather-themed gradient background
- 📱 Fully responsive layout
- 🌙 Clean, modern UI with Tailwind CSS

## Environment Variables

```env
# .env.local (Phase 2+)
VITE_WEATHER_API_KEY=your_openweathermap_api_key
VITE_WEATHER_API_BASE_URL=https://api.openweathermap.org/data/2.5
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License — see [LICENSE](LICENSE) for details.