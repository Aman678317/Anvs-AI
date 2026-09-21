/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        surface: {
          50: "#18181b",
          100: "#27272a",
          200: "#3f3f46",
          300: "#52525b",
          800: "#121215",
          900: "#09090b",
        },
        brand: {
          primary: "#3b82f6",
          accent: "#8b5cf6",
          active: "#10b981",
          warning: "#f59e0b",
          danger: "#ef4444",
        },
      },
      animation: {
        "pulse-subtle": "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "halo-glow": "halo 1.5s ease-in-out infinite alternate",
      },
      keyframes: {
        halo: {
          "0%": { boxShadow: "0 0 0 0px rgba(16, 185, 129, 0.4)" },
          "100%": { boxShadow: "0 0 0 4px rgba(16, 185, 129, 0.8)" },
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
