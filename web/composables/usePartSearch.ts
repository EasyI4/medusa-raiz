import type {
  ChatHistoryItem,
  NormalizedPartSearch,
  PartSearchApiResponse,
} from "~/types/part-search"
import { normalizePartSearchResponse } from "~/utils/parts"

export class PartSearchError extends Error {
  status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = "PartSearchError"
    this.status = status
  }
}

export function usePartSearch() {
  const { idToken, logout } = useAuth()
  const pending = ref(false)
  const activeQuery = ref("")

  async function search(query: string, history: ChatHistoryItem[] = []): Promise<NormalizedPartSearch> {
    const normalizedQuery = query.trim()
    if (!normalizedQuery) {
      throw new PartSearchError("Informe a peça ou o veículo que deseja consultar.")
    }
    if (pending.value) {
      throw new PartSearchError(
        activeQuery.value === normalizedQuery
          ? "Essa consulta já está em andamento."
          : "Aguarde a consulta atual terminar.",
      )
    }

    pending.value = true
    activeQuery.value = normalizedQuery
    try {
      const token = await idToken()
      const response = await $fetch<PartSearchApiResponse>("/chat/messages", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: {
          message: normalizedQuery,
          history: history.slice(-6),
        },
      })

      if (!response || response.success !== true) {
        throw new PartSearchError(
          response?.message || "A API não conseguiu concluir a consulta.",
        )
      }
      return normalizePartSearchResponse(response)
    } catch (error: unknown) {
      if (error instanceof PartSearchError) throw error

      const candidate = error as {
        status?: number
        statusCode?: number
        data?: { message?: string, error?: string }
      }
      const status = candidate.statusCode ?? candidate.status ?? null
      if (status === 401) {
        await logout()
        throw new PartSearchError("Sua sessão expirou. Entre novamente.", 401)
      }
      throw new PartSearchError(
        candidate.data?.message
          || candidate.data?.error
          || "Não foi possível consultar as peças agora. Tente novamente.",
        status,
      )
    } finally {
      pending.value = false
      activeQuery.value = ""
    }
  }

  return {
    pending: readonly(pending),
    activeQuery: readonly(activeQuery),
    search,
  }
}
