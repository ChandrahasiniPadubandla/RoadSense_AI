/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        asphalt: {
          950: '#0E1013',
          900: '#15181C',
          800: '#1D2126',
          700: '#282D34',
          600: '#3A4048',
          500: '#535A63',
          400: '#7A828C',
          300: '#A8AFB7',
          200: '#D3D7DB',
          100: '#EDEFF1',
        },
        signal: {
          amber: '#E8A33D',
          red: '#D14343',
          green: '#3FA772',
          blue: '#3E7CB1',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
