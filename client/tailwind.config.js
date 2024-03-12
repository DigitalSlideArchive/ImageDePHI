/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{vue,js,ts}"],
  theme: {
    extend: {
      colors: {
        primary: "#5A387C",

        secondary: "#00A6BF",

        accent: "#FF6A6A",

        neutral: "#201C35",

        "base-100": "#FFFFFF",

        info: "#3ABFF8",

        success: "#36D399",

        warning: "#FBBD23",

        error: "#F87272",

        secondaryContent: "#E8F2F3",
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        light: {
          // eslint-disable-next-line @typescript-eslint/no-var-requires
          ...require("daisyui/src/theming/themes")["light"],

          primary: "#5A387C",

          secondary: "#00A6BF",

          accent: "#FF6A6A",

          neutral: "#201C35",

          "base-100": "#FFFFFF",

          info: "#3ABFF8",

          success: "#36D399",

          warning: "#FBBD23",

          error: "#F87272",

          secondaryContent: "#E8F2F3",
        },
      },
    ],
  },
};
