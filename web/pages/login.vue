<script setup lang="ts">
import DsBrand from "~/components/ui/DsBrand.vue"
import DsButton from "~/components/ui/DsButton.vue"
import DsIcon from "~/components/ui/DsIcon.vue"

definePageMeta({ middleware: "auth" })

const { missing, signIn, signUp, resetPassword } = useAuth()
const mode = ref<"login" | "signup" | "reset">("login")
const email = ref("")
const password = ref("")
const formError = ref("")
const pending = ref(false)

const copy = computed(() => {
  if (mode.value === "signup") {
    return ["Criar conta", "Use o e-mail da equipe. A senha precisa ter pelo menos 6 caracteres.", "Criar conta"]
  }
  if (mode.value === "reset") {
    return ["Recuperar senha", "Enviaremos um link de redefinição para o e-mail informado.", "Enviar link"]
  }
  return ["Entrar no Autocenter IA", "Acesse o catálogo da Medusa Autocenter e continue seus atendimentos.", "Entrar"]
})

function authMessage(code: string) {
  const messages: Record<string, string> = {
    "auth/email-already-in-use": "Esse e-mail já tem conta. Entre com a senha.",
    "auth/invalid-credential": "E-mail ou senha incorretos.",
    "auth/wrong-password": "E-mail ou senha incorretos.",
    "auth/user-not-found": "Não encontramos essa conta.",
    "auth/weak-password": "A senha precisa ter pelo menos 6 caracteres.",
    "auth/invalid-email": "Informe um e-mail válido.",
    "auth/too-many-requests": "Muitas tentativas. Espere um pouco e tente de novo.",
    "auth/operation-not-allowed": "Ative o login por e-mail e senha no console do Firebase.",
    "auth/unauthorized-domain": "Inclua localhost nos domínios autorizados do Firebase.",
  }
  return messages[code] || "Não foi possível concluir o acesso."
}

async function submit() {
  formError.value = ""
  pending.value = true
  try {
    if (mode.value === "login") await signIn(email.value.trim(), password.value)
    if (mode.value === "signup") await signUp(email.value.trim(), password.value)
    if (mode.value === "login" || mode.value === "signup") {
      await navigateTo("/")
      return
    }
    if (mode.value === "reset") {
      await resetPassword(email.value.trim())
      formError.value = "Enviamos o link de redefinição para o seu e-mail."
    }
  } catch (error: any) {
    formError.value = authMessage(error?.code || "")
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <main v-if="missing.length" class="configuration-gate">
    <section class="configuration-card">
      <DsBrand />
      <h1>Falta a configuração do Firebase</h1>
      <p>O acesso fica disponível assim que as variáveis públicas do Firebase Web forem configuradas no ambiente.</p>
      <ul>
        <li v-for="key in missing" :key="key">{{ key }}</li>
      </ul>
    </section>
  </main>

  <main v-else class="auth-page">
    <section class="auth-form-panel">
      <div class="auth-card">
        <DsBrand class="auth-card__brand" subtitle="Medusa Autocenter" />

        <div class="auth-card__heading">
          <p class="eyebrow">Acesso seguro</p>
          <h1>{{ copy[0] }}</h1>
          <p>{{ copy[1] }}</p>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <label class="ds-field">
            <span class="ds-field__label">E-mail</span>
            <span class="field-control">
              <DsIcon name="mail" />
              <input v-model="email" class="ds-input" type="email" autocomplete="email" placeholder="voce@autocenter.com.br" required>
            </span>
          </label>

          <label v-if="mode !== 'reset'" class="ds-field">
            <span class="ds-field__label">Senha</span>
            <span class="field-control">
              <DsIcon name="lock" />
              <input v-model="password" class="ds-input" type="password" autocomplete="current-password" placeholder="Sua senha" minlength="6" required>
            </span>
          </label>

          <p class="form-error" :class="{ success: mode === 'reset' && formError.startsWith('Enviamos') }" role="alert">{{ formError }}</p>
          <DsButton type="submit" size="lg" block :disabled="pending">
            {{ pending ? "Aguarde…" : copy[2] }}
          </DsButton>
        </form>

        <nav class="auth-links" aria-label="Opções de acesso">
          <button v-if="mode !== 'signup'" type="button" @click="mode = 'signup'; formError = ''">Criar conta</button>
          <button v-if="mode !== 'reset'" type="button" @click="mode = 'reset'; formError = ''">Esqueci a senha</button>
          <button v-if="mode !== 'login'" type="button" @click="mode = 'login'; formError = ''">Já tenho conta</button>
        </nav>
      </div>
    </section>

    <aside class="auth-showcase" aria-label="Benefícios do AUTOCENTER IA">
      <div class="auth-showcase__content">
        <span class="ds-badge"><DsIcon name="sparkles" /> Assistente inteligente</span>
        <h2>Da oficina à referência certa, em uma conversa.</h2>
        <p class="auth-showcase__lead">Consulte o catálogo da Medusa Autocenter com contexto de veículo, organize o atendimento e compare referências com mais agilidade.</p>

        <ul class="feature-list">
          <li class="feature-item">
            <span class="feature-item__icon"><DsIcon name="car" /></span>
            <div><strong>Busca por peça e veículo</strong><p>Informe peça, modelo e ano para refinar a consulta ao catálogo.</p></div>
          </li>
          <li class="feature-item">
            <span class="feature-item__icon"><DsIcon name="wrench" /></span>
            <div><strong>Referências organizadas</strong><p>Visualize códigos originais, paralelos, aplicações e evidências em cards claros.</p></div>
          </li>
          <li class="feature-item">
            <span class="feature-item__icon"><DsIcon name="history" /></span>
            <div><strong>Histórico por usuário</strong><p>Retome pesquisas recentes sem perder o contexto do atendimento.</p></div>
          </li>
        </ul>
      </div>
    </aside>
  </main>
</template>
