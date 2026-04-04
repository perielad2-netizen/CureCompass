import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#f4f9fb",
        foreground: "#0b213f",
        primary: {
          DEFAULT: "#2cb6af",
          dark: "#249890",
          foreground: "#ffffff",
        },
        navy: {
          DEFAULT: "#0b213f",
          muted: "#1e3a5c",
        },
        ice: "#e0f4f7",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        calm: "0 10px 40px rgba(11, 33, 63, 0.07)",
        "calm-teal": "0 10px 36px rgba(44, 182, 175, 0.12)",
      },
      backgroundImage: {
        "page-mesh":
          "radial-gradient(ellipse 120% 80% at 50% -30%, rgba(44, 182, 175, 0.14), transparent 55%), radial-gradient(ellipse 90% 60% at 100% 0%, rgba(11, 33, 63, 0.06), transparent 50%)",
      },
    },
  },
  plugins: [],
};

export default config;
