// tailwind.config.js
module.exports = {
    content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
        extend: {
            colors: {
                primary: "hsl(220, 90%, 56%)",
                secondary: "hsl(210, 15%, 20%)",
                accent: "hsl(340, 80%, 60%)",
            },
        },
    },
    plugins: [],
};
