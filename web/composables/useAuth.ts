import {
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut,
  type Auth,
  type User,
} from "firebase/auth"
import { initializeApp } from "firebase/app"

let auth: Auth | null = null
let currentUser: User | null = null
let starting: Promise<void> | null = null

export function useAuth() {
  const email = useState("auth-email", () => "")
  const ready = useState("auth-ready", () => false)
  const missing = useState<string[]>("auth-missing", () => [])

  async function init() {
    if (starting) return starting
    starting = (async () => {
      let response: { success: boolean, config: Record<string, string>, missing: string[] }
      try {
        response = await $fetch<{
          success: boolean
          config: Record<string, string>
          missing: string[]
        }>("/chat/config")
      } catch (error: any) {
        missing.value = error?.data?.missing || ["FIREBASE_API_KEY", "FIREBASE_AUTH_DOMAIN", "FIREBASE_PROJECT_ID", "FIREBASE_APP_ID"]
        ready.value = true
        return
      }
      if (!response.success) {
        missing.value = response.missing || []
        ready.value = true
        return
      }
      auth = getAuth(initializeApp(response.config))
      auth.languageCode = "pt-BR"
      await new Promise<void>((resolve) => {
        onAuthStateChanged(auth!, (user) => {
          currentUser = user
          email.value = user?.email || ""
          ready.value = true
          resolve()
        })
      })
    })()
    return starting
  }

  function requireUser() {
    return currentUser
  }

  async function idToken() {
    if (!currentUser) throw new Error("Entre na conta para enviar perguntas.")
    return currentUser.getIdToken()
  }

  return {
    email,
    ready,
    missing,
    init,
    requireUser,
    idToken,
    async signIn(userEmail: string, password: string) {
      const credential = await signInWithEmailAndPassword(auth!, userEmail, password)
      currentUser = credential.user
      email.value = credential.user.email || userEmail
      return credential
    },
    async signUp(userEmail: string, password: string) {
      const credential = await createUserWithEmailAndPassword(auth!, userEmail, password)
      currentUser = credential.user
      email.value = credential.user.email || userEmail
      return credential
    },
    resetPassword: (userEmail: string) => sendPasswordResetEmail(auth!, userEmail),
    logout: () => signOut(auth!),
  }
}
