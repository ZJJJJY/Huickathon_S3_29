/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0A0A0F",
        bgCard: "#13131A",
        text: "#F5F5F7",
        textMuted: "#8B8B95",
        neon: {
          cyan: "#3EE8FF",
          orange: "#FF6B35",
          yellow: "#FFD23F",
          purple: "#A855F7",
          green: "#34D399",
          pink: "#FF3EA5",
        },
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Helvetica", "Arial", "sans-serif"],
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0px transparent" },
          "50%": { boxShadow: "0 0 18px currentColor" },
        },
      },
      animation: {
        pulseGlow: "pulseGlow 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
