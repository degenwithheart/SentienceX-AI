# SentienceX-AI Frontend

The frontend component is a Next.js application providing an interactive web interface for the SentienceX-AI chatbot. It features a chat interface, real-time data visualizations for sentiment analysis, and panels for threat detection and analytics.

## Features

- **Chat Interface**: Send messages to the AI and receive responses with analysis.
- **Sentiment Graph**: Real-time line chart visualizing sentiment trends using Recharts.
- **Threat Panel**: Display threat detection results.
- **Analytics Toggle**: Show/hide analytics panels.
- **Audio Playback**: Play synthesized audio responses.
- **Responsive Design**: Tailwind CSS for mobile-friendly UI.
- **Real-Time Updates**: Server-sent events for live data streaming.
- **Error Handling**: Toast notifications for user feedback.

## Requirements

- Node.js 16+
- npm or yarn

## How to Run

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Set environment variables** (optional, create `.env.local`):
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_AUTH_TOKEN=your_token
   ```

3. **Run the development server**:
   ```bash
   npm run dev
   ```

4. **Build for production**:
   ```bash
   npm run build
   npm start
   ```

5. **Access the app**: http://localhost:3000

The frontend proxies API requests to the backend. Ensure the backend is running on port 8000 or configure `NEXT_PUBLIC_API_URL`.

## Technologies

- **Next.js**: React framework for server-side rendering and routing.
- **React**: UI library with hooks for state management.
- **TypeScript**: Type-safe JavaScript.
- **Tailwind CSS**: Utility-first CSS framework.
- **Recharts**: Chart library for data visualization.
- **Sonner**: Toast notification library.
- **Lodash**: Utility functions (debounce).

## Folder Structure

- `README.md`: This file.
- Additional frontend-specific files are minimal; most code is in the root `app/` and `components/` directories.
