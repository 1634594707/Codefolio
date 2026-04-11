/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'var(--color-primary)',
          light: '#acc7ff',
        },
        secondary: {
          DEFAULT: 'var(--color-secondary)',
          light: '#d2bbff',
        },
        tertiary: {
          DEFAULT: 'var(--color-tertiary)',
          light: '#67df70',
        },
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        'surface-container': 'var(--color-surface-container)',
        'on-surface': 'var(--color-on-surface)',
        'on-surface-variant': 'var(--color-on-surface-variant)',
        outline: 'var(--color-outline)',
        'outline-variant': 'var(--color-outline-variant)',
      },
    },
  },
  plugins: [],
}
