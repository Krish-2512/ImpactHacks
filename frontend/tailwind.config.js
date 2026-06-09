/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50:  "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
        },
        soil: {
          50:  "#fdf8f0",
          400: "#c78a3e",
          600: "#92641e",
          800: "#5c3d10",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        devanagari: ["Noto Sans Devanagari", "sans-serif"],
      },
    },
  },
  plugins: [],
}
