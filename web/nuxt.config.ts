const apiOrigin = process.env.API_ORIGIN || (process.env.NODE_ENV === "production"
  ? "http://127.0.0.1:5001"
  : "http://127.0.0.1:5000")

export default defineNuxtConfig({
  compatibilityDate: "2026-09-25",
  ssr: false,
  app: {
    head: {
      title: "Autocenter IA · Medusa Autocenter",
      meta: [
        { name: "description", content: "Assistente inteligente para consulta de peças da Medusa Autocenter." },
        { name: "theme-color", content: "#338b38" },
      ],
      link: [
        { rel: "preconnect", href: "https://fonts.googleapis.com" },
        { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" },
        { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" },
      ],
    },
  },
  css: ["~/assets/css/main.css"],
  routeRules: {
    "/chat/**": { proxy: `${apiOrigin}/chat/**` },
    "/health": { proxy: `${apiOrigin}/health` },
  },
})
