export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server) return
  const { ready, email, missing, init } = useAuth()
  await init()
  if (missing.value.length) {
    if (to.path !== "/login") return navigateTo("/login")
    return
  }
  const logged = Boolean(email.value)
  if (!logged && to.path !== "/login") return navigateTo("/login")
  if (logged && to.path === "/login") return navigateTo("/")
})
