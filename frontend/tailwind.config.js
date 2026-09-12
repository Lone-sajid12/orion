/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        sand: '#F3EFE6',
        surface: '#FAF8F2',
        ink: '#252522',
        muted: '#68665E',
        moss: '#66745A',
        mossdark: '#4C5744',
        bronze: '#A68A64',
        line: '#D9D4C8',
        panel: '#292A26',
        panelsoft: '#33342F',
      },
      fontFamily: {
        sans: ['Inter', 'Manrope', 'DM Sans', 'system-ui', 'sans-serif'],
        serif: ['Newsreader', 'Georgia', 'serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(37,37,34,0.06), 0 4px 14px rgba(37,37,34,0.05)',
      },
    },
  },
  plugins: [],
}
