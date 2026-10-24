/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B1220',
        panel: '#111A2B',
        panelSecondary: '#162238',
        border: '#1E2A3F',
        borderLight: '#2A3C59',
        textPrimary: '#E6EDF7',
        textMuted: '#8FA3BF',
        primaryBlue: '#3B82F6',
        primaryBlueHover: '#2563EB',
        accentCyan: '#06B6D4',
        statusPass: '#10B981',
        statusFail: '#EF4444',
        statusUnknown: '#F59E0B',
        statusNotReached: '#6B7280',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
