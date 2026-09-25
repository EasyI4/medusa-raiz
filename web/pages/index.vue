<script setup lang="ts">
import DsBrand from "~/components/ui/DsBrand.vue"
import DsButton from "~/components/ui/DsButton.vue"
import DsIcon from "~/components/ui/DsIcon.vue"
import type {
  ChatHistoryItem,
  NormalizedPartSearch,
} from "~/types/part-search"

definePageMeta({ middleware: "auth" })

type ChatMessage = {
  role: "user" | "assistant"
  content: string
  error?: boolean
  result?: NormalizedPartSearch
}

type Conversation = {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: number
}

const suggestions = [
  "Disco de freio Compass 2020",
  "Pastilha de freio Civic 2018",
  "Filtro de ar Gol 2015",
  "Amortecedor dianteiro Onix 2019",
]

const { email, logout } = useAuth()
const { pending: sending, search } = usePartSearch()
const conversations = ref<Conversation[]>([])
const activeId = ref("")
const draft = ref("")
const railOpen = ref(false)
const conversationQuery = ref("")
const messagesElement = ref<HTMLElement | null>(null)

const active = computed(() => conversations.value.find((item) => item.id === activeId.value) || conversations.value[0])
const filteredConversations = computed(() => {
  const query = conversationQuery.value.trim().toLocaleLowerCase("pt-BR")
  if (!query) return conversations.value
  const terms = query.split(/\s+/)
  return conversations.value.filter((conversation) => {
    const content = conversation.messages.map((message) => message.content || message.result?.summary?.text || "").join(" ")
    const haystack = `${conversation.title} ${content}`.toLocaleLowerCase("pt-BR")
    return terms.every((term) => haystack.includes(term))
  })
})

const accountInitial = computed(() => (email.value.trim()[0] || "U").toLocaleUpperCase("pt-BR"))

function storageKey() {
  return `allora.chats.v2.${email.value}`
}

function blankConversation(): Conversation {
  return { id: crypto.randomUUID(), title: "Nova conversa", messages: [], updatedAt: Date.now() }
}

function loadStore() {
  const raw = localStorage.getItem(storageKey())
  if (!raw) {
    conversations.value = [blankConversation()]
    activeId.value = conversations.value[0].id
    return
  }
  try {
    const saved = JSON.parse(raw)
    conversations.value = Array.isArray(saved.conversations) && saved.conversations.length
      ? saved.conversations
      : [blankConversation()]
    activeId.value = saved.activeId || conversations.value[0].id
    if (!conversations.value.some((item) => item.id === activeId.value)) {
      activeId.value = conversations.value[0].id
    }
  } catch {
    conversations.value = [blankConversation()]
    activeId.value = conversations.value[0].id
  }
}

function saveStore() {
  localStorage.setItem(storageKey(), JSON.stringify({
    conversations: conversations.value.slice(0, 30),
    activeId: activeId.value,
  }))
}

function openConversation(id: string) {
  activeId.value = id
  railOpen.value = false
  saveStore()
}

function removeConversation(id: string) {
  conversations.value = conversations.value.filter((item) => item.id !== id)
  if (!conversations.value.length) conversations.value = [blankConversation()]
  if (!conversations.value.some((item) => item.id === activeId.value)) {
    activeId.value = conversations.value[0].id
  }
  saveStore()
}

function visibleText(content: string) {
  const text = content || ""
  if (/\b(select|from|where|join)\b/i.test(text) || text.includes("```")) {
    return "Não foi possível apresentar esta resposta."
  }
  if (text.trim().startsWith("{") || text.trim().startsWith("[")) {
    return "Resultado estruturado indisponível nesta mensagem anterior."
  }
  return text
}

function conversationSnippet(conversation: Conversation) {
  const last = conversation.messages.at(-1)
  if (!last) return "Conversa sem mensagens"
  const text = last.content || last.result?.summary?.text || "Resultado de peças"
  return text.length > 46 ? `${text.slice(0, 46)}…` : text
}

function conversationDate(timestamp: number) {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(timestamp).replace(" de ", " ")
}

function newChat() {
  if (active.value && !active.value.messages.length) return
  const created = blankConversation()
  conversations.value.unshift(created)
  activeId.value = created.id
  railOpen.value = false
  saveStore()
}

async function scrollToLatest() {
  await nextTick()
  if (messagesElement.value) {
    messagesElement.value.scrollTop = messagesElement.value.scrollHeight
  }
}

async function send() {
  const text = draft.value.trim()
  const conversation = active.value
  if (!text || sending.value || !conversation) return
  const history: ChatHistoryItem[] = conversation.messages
    .filter((message) => !message.error)
    .slice(-6)
    .map((message) => {
      const summary = message.result?.summary
      const content = message.content
        || summary?.text
        || [summary?.vehicle, summary?.year].filter(Boolean).join(" ")
      return { role: message.role, content }
    })
    .filter((message) => Boolean(message.content))
  conversation.messages.push({ role: "user", content: text })
  if (conversation.title === "Nova conversa") {
    conversation.title = text.length > 42 ? `${text.slice(0, 42)}…` : text
  }
  conversation.updatedAt = Date.now()
  conversations.value.sort((a, b) => b.updatedAt - a.updatedAt)
  draft.value = ""
  saveStore()
  await scrollToLatest()
  try {
    const result = await search(text, history)
    conversation.messages.push({
      role: "assistant",
      content: "",
      result,
    })
  } catch (error: any) {
    conversation.messages.push({
      role: "assistant",
      error: true,
      content: error?.message || "Não foi possível consultar as peças agora.",
    })
  } finally {
    conversation.updatedAt = Date.now()
    saveStore()
    await scrollToLatest()
  }
}

watch(activeId, scrollToLatest)

onMounted(() => {
  loadStore()
  scrollToLatest()
})
</script>

<template>
  <div class="shell">
    <button
      v-if="railOpen"
      class="rail-backdrop"
      type="button"
      aria-label="Fechar conversas"
      @click="railOpen = false"
    />
    <aside class="rail" :class="{ open: railOpen }" aria-label="Navegação e histórico">
      <div class="rail__brand">
        <DsBrand subtitle="Medusa Autocenter" />
        <DsButton class="topbar__menu" type="button" variant="ghost" icon="x" icon-only aria-label="Fechar menu" @click="railOpen = false" />
      </div>

      <div class="rail__actions">
        <DsButton type="button" icon="plus" block @click="newChat">Nova conversa</DsButton>
        <label class="history-search">
          <span class="sr-only">Buscar no histórico</span>
          <DsIcon name="search" />
          <input v-model="conversationQuery" class="ds-input" type="search" placeholder="Buscar no histórico…">
        </label>
      </div>

      <p class="rail__section-label">Conversas recentes</p>
      <nav class="conversation-list" aria-label="Conversas">
        <div
          v-for="conversation in filteredConversations"
          :key="conversation.id"
          class="conversation"
          :class="{ active: conversation.id === activeId }"
        >
          <button class="open" type="button" @click="openConversation(conversation.id)">
            <span class="conversation-title">{{ conversation.title }}</span>
            <span class="conversation-date">{{ conversationDate(conversation.updatedAt) }}</span>
            <span class="conversation-snippet">{{ conversationSnippet(conversation) }}</span>
          </button>
          <button class="delete" type="button" aria-label="Excluir conversa" title="Excluir conversa" @click="removeConversation(conversation.id)">
            <DsIcon name="trash" />
          </button>
        </div>
        <p v-if="!filteredConversations.length" class="conversation-empty">Nenhuma conversa encontrada.</p>
      </nav>

      <div class="account">
        <span class="account__avatar">{{ accountInitial }}</span>
        <div class="account__copy">
          <strong>Minha conta</strong>
          <p>{{ email }}</p>
        </div>
        <DsButton type="button" variant="ghost" icon="logout" icon-only aria-label="Sair da conta" title="Sair" @click="logout" />
      </div>
    </aside>

    <main class="stage">
      <header class="topbar">
        <DsButton class="topbar__menu" type="button" variant="ghost" icon="menu" icon-only aria-label="Abrir conversas" @click="railOpen = !railOpen" />
        <div class="topbar__heading">
          <p>Assistente de catálogo</p>
          <h1>{{ active?.title || "Nova conversa" }}</h1>
        </div>
        <div class="topbar__status"><span class="status-dot" /> Catálogo conectado</div>
        <span class="ds-badge">Beta</span>
      </header>

      <div ref="messagesElement" class="messages">
        <div v-if="active && !active.messages.length && !sending" class="empty">
          <div class="empty__icon"><DsIcon name="wrench" /></div>
          <span class="ds-badge"><DsIcon name="sparkles" /> Busca assistida</span>
          <h2>Qual peça você procura?</h2>
          <p>Informe a peça, o veículo e o ano. Organizamos os códigos, marcas e aplicações encontradas no catálogo para facilitar sua conferência.</p>
          <div class="suggestions">
            <button v-for="suggestion in suggestions" :key="suggestion" type="button" @click="draft = suggestion">
              <DsIcon name="search" /> {{ suggestion }}
            </button>
          </div>
        </div>
        <div
          v-for="(message, index) in active?.messages || []"
          :key="index"
          class="turn"
          :class="message.role"
        >
          <div class="avatar" aria-hidden="true">
            <DsIcon :name="message.role === 'user' ? 'user' : 'wrench'" />
          </div>
          <div class="turn-body" :class="{ error: message.error }">
            <PartCatalog v-if="message.result" :result="message.result" />
            <p v-else>{{ visibleText(message.content) }}</p>
          </div>
        </div>
        <div v-if="sending" class="turn assistant">
          <div class="avatar" aria-hidden="true"><DsIcon name="wrench" /></div>
          <div class="turn-body pending">
            <span class="thinking-dots" aria-hidden="true"><span /><span /><span /></span>
            Consultando e organizando as referências…
          </div>
        </div>
      </div>

      <div class="composer-wrap">
        <form class="composer" @submit.prevent="send">
          <label class="sr-only" for="draft">Pergunta</label>
          <textarea
            id="draft"
            v-model="draft"
            rows="1"
            maxlength="2000"
            placeholder="Peça + veículo + ano…"
            @keydown.enter.exact.prevent="send"
          />
          <DsButton type="submit" icon="send" icon-only :disabled="sending || !draft.trim()" :aria-label="sending ? 'Consulta em andamento' : 'Enviar consulta'" />
        </form>
        <p class="composer-hint">Enter para enviar · Shift + Enter para quebrar linha · Confira as aplicações antes da compra</p>
      </div>
    </main>
  </div>
</template>
