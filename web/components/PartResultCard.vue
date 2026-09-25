<script setup lang="ts">
import type { PartApplication, PartGroup } from "~/types/part-search"

const props = defineProps<{
  part: PartGroup
  index: number
  assessment?: string
}>()

const copied = ref(false)

const status = computed(() => ({
  CONFIRMED: {
    label: "Aplicação compatível",
    help: "Os dados consultados conferem com esta aplicação.",
  },
  PROBABLE: {
    label: "Provável aplicação",
    help: "Há correspondência parcial. Confirme versão, motor e ano antes da compra.",
  },
  AMBIGUOUS: {
    label: "",
    help: "Faltam dados para garantir que esta peça serve no veículo.",
  },
}[props.part.compatibility]))

const primaryApplication = computed(() => props.part.applications[0] || null)
const partTitle = computed(() => mainDescription(props.part.descriptions)
  || props.part.types[0]
  || "Peça encontrada")
const partType = computed(() => props.part.types.join(", "))
const userWarnings = computed(() => [...new Set(
  [...props.part.conflicts, ...props.part.warnings].map(warningLabel),
)])

const warningLabels: Record<string, string> = {
  PART_FAMILY_INFERRED_BY_FALLBACK: "O tipo da peça foi identificado pela descrição.",
  PART_FAMILY_UNKNOWN: "O tipo exato da peça não foi confirmado.",
  YEAR_UNKNOWN: "O ano do veículo não foi informado.",
  YEAR_OR_APPLICATION_SOURCE_CONFLICT: "Há divergência entre o ano pesquisado e a aplicação cadastrada.",
  POSITION_UNKNOWN: "A posição da peça no veículo não foi informada.",
  MULTIPLE_POSITIONS: "Este código aparece para posições diferentes no veículo.",
  ENGINE_UNKNOWN: "O motor do veículo não foi informado.",
  MULTIPLE_ENGINES_REQUIRE_SELECTION: "Este código varia conforme o motor. Confirme o motor correto.",
  GENERATION_UNKNOWN: "A geração do veículo não foi informada.",
  MULTIPLE_GENERATIONS: "Este código aparece em mais de uma geração do veículo.",
  TRIM_UNKNOWN: "A versão do veículo não foi informada.",
  SINGLE_SOURCE_ONLY: "Resultado encontrado em uma única referência de catálogo.",
}

async function copyCode() {
  if (!props.part.code) return
  try {
    await navigator.clipboard.writeText(props.part.code)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    copied.value = false
  }
}

function mainDescription(descriptions: string[]) {
  return [...descriptions].sort((a, b) => b.length - a.length)[0] || ""
}

function attributes(descriptions: string[], types: string[]) {
  const source = `${descriptions.join(" ")} ${types.join(" ")}`.toLocaleLowerCase("pt-BR")
  const values: string[] = []
  for (const value of ["dianteiro", "traseiro", "esquerdo", "direito", "ventilado", "sólido", "solido"]) {
    const normalized = value === "solido" ? "sólido" : value
    if (source.includes(value) && !values.includes(normalized)) values.push(normalized)
  }
  return values
}

function warningLabel(value: string) {
  return warningLabels[value] || "Esta aplicação precisa de uma conferência adicional."
}

function vehicleName(application: PartApplication) {
  return [application.make, application.model].filter(Boolean).join(" ")
}

function yearRange(application: PartApplication) {
  const { yearStart, yearEnd } = application
  if (yearStart != null && yearEnd != null) {
    return yearStart === yearEnd ? String(yearStart) : `${yearStart} a ${yearEnd}`
  }
  if (yearStart != null) return `A partir de ${yearStart}`
  if (yearEnd != null) return `Até ${yearEnd}`
  return ""
}

function applicationFacts(application: PartApplication) {
  return [
    { label: "Versão", value: application.variant },
    { label: "Motor", value: application.engine },
    { label: "Geração", value: application.generation },
    { label: "Ano", value: yearRange(application) },
    { label: "Câmbio", value: application.transmission },
    { label: "Combustível", value: application.fuel },
    { label: "Carroceria", value: application.body },
  ].filter((item) => item.value)
}
</script>

<template>
  <article
    class="part-card"
    :class="[
      `compatibility-${part.compatibility.toLowerCase()}`,
      { original: part.origin === 'original' },
    ]"
  >
    <div class="part-head">
      <span class="part-index">{{ index + 1 }}</span>
      <div class="part-identity">
        <p v-if="partType" class="part-label">{{ partType }}</p>
        <h5>{{ partTitle }}</h5>
        <div class="part-reference">
          <span v-if="part.brands.length"><small>Marca</small> {{ part.brands.join(", ") }}</span>
          <button
            v-if="part.code"
            type="button"
            class="code-chip"
            :class="{ copied }"
            :aria-label="`Copiar código ${part.code}`"
            @click="copyCode"
          >
            <small>{{ copied ? "Código copiado" : "Código" }}</small>
            {{ part.code }}
          </button>
        </div>
      </div>
      <div class="part-status">
        <span
          v-if="part.compatibility !== 'AMBIGUOUS'"
          class="compatibility-badge"
          :class="part.compatibility.toLowerCase()"
        >
          {{ status.label }}
        </span>
        <span v-if="part.origin === 'original'" class="origin-badge original">
          Original
        </span>
      </div>
    </div>

    <div v-if="attributes(part.descriptions, part.types).length" class="part-tags">
      <span
        v-for="attribute in attributes(part.descriptions, part.types)"
        :key="attribute"
        class="attribute-tag"
      >
        {{ attribute }}
      </span>
    </div>

    <p class="compatibility-help">{{ status.help }}</p>

    <section v-if="primaryApplication" class="application-summary">
      <div class="application-summary__head">
        <div>
          <span>Aplicação principal</span>
          <strong>{{ vehicleName(primaryApplication) || "Veículo não especificado" }}</strong>
        </div>
      </div>
      <dl v-if="applicationFacts(primaryApplication).length" class="application-facts">
        <div v-for="fact in applicationFacts(primaryApplication)" :key="fact.label">
          <dt>{{ fact.label }}</dt>
          <dd>{{ fact.value }}</dd>
        </div>
      </dl>
    </section>
    <p v-else class="application-unavailable">
      A aplicação por veículo não está cadastrada. Confirme pelo código da peça antes da compra.
    </p>

    <div v-if="part.equivalents.length" class="equivalents">
      <span class="equivalents-label">Outros códigos da mesma peça</span>
      <span v-for="item in part.equivalents" :key="item.code" class="equivalent-chip">
        {{ item.code }} <small v-if="item.brand">{{ item.brand }}</small>
      </span>
    </div>

    <div v-if="assessment" class="ai-part-assessment">
      <span aria-hidden="true">A</span>
      <div><strong>Orientação para conferência</strong><p>{{ assessment }}</p></div>
    </div>

    <div v-if="userWarnings.length" class="compatibility-warnings">
      <strong>Antes de escolher</strong>
      <span v-for="warning in userWarnings" :key="warning">{{ warning }}</span>
    </div>

  </article>
</template>
