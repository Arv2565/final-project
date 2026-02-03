/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Poppins', 'sans-serif'],
      },
      colors: {
        light: {
          bg: '#ffffff',
          surface: '#f8f9fa',
          text: '#1a1a1a',
          border: '#d4d9e3',
        },
        legal: {
          navy: '#1e3a8a',
          darkNavy: '#0f172a',
          lightNavy: '#3b5bdb',
          gold: '#d4af37',
          lightGold: '#f3d87f',
          gray: '#6b7280',
          lightGray: '#f3f4f6',
          borders: '#cbd5e1',
          accent: '#2563eb',
        },
        dark: {
          bg: '#131416',
          surface: '#1e1e1e',
          text: '#ffffff',
          border: '#ffffff1a',
        },
      },
    },
  },
  plugins: [],
}
