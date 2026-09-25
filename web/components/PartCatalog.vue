<script setup lang="ts">
import type { NormalizedPartSearch, PartGroup } from "~/types/part-search"

const props = defineProps<{ result: NormalizedPartSearch }>()

const confirmed = computed(() => props.result.parts.filter((part) => part.compatibility === "CONFIRMED"))
const probable = computed(() => props.result.parts.filter((part) => part.compatibility === "PROBABLE"))
const ambiguous = computed(() => props.result.parts.filter((part) => part.compatibility === "AMBIGUOUS"))
const sections = computed(() => [
  { status: "CONFIRMED" as const, parts: confirmed.value },
  { status: "PROBABLE" as const, parts: probable.value },
  { status: "AMBIGUOUS" as const, parts: ambiguous.value },
].filter((section) => section.parts.length))

function assessmentForPart(code: string) {
  const normalizedCode = code.replace(/\s+/g, "").toLocaleUpperCase("pt-BR")
  for (const product of props.result.summary?.products || []) {
    const matches = product.codes.some(
      (item) => item.code.replace(/\s+/g, "").toLocaleUpperCase("pt-BR") === normalizedCode,
    )
    if (matches && product.assessment) return product.assessment
  }
  return ""
}

function sectionTitle(status: PartGroup["compatibility"]) {
  return {
    CONFIRMED: "Peças compatíveis",
    PROBABLE: "Confira os detalhes",
    AMBIGUOUS: "Precisam de confirmação",
  }[status]
}

function sectionDescription(status: PartGroup["compatibility"]) {
  return {
    CONFIRMED: "Os dados da busca conferem com o cadastro destas peças.",
    PROBABLE: "Há correspondência, mas algum dado do veículo precisa ser conferido.",
    AMBIGUOUS: "Não compre sem confirmar os dados indicados no card.",
  }[status]
}
</script>

<template>
  <section class="catalog" aria-label="Resultado da consulta">
    <header v-if="result.summary" class="catalog-head">
      <div>
        <p class="result-kicker">Resumo da busca</p>
        <h3 v-if="result.summary.vehicle || result.summary.year">
          {{ [result.summary.vehicle, result.summary.year].filter(Boolean).join(" · ") }}
        </h3>
        <p v-if="result.summary.text" class="answer-text">{{ result.summary.text }}</p>
        <div v-if="result.summary.assessment" class="ai-overview">
          <span aria-hidden="true">A</span>
          <div>
            <strong>Avaliação de aplicação</strong>
            <p>{{ result.summary.assessment }}</p>
          </div>
        </div>
      </div>
      <div v-if="result.summary.products.length" class="answer-products">
        <div
          v-for="(product, index) in result.summary.products"
          :key="`${product.position}-${product.type}-${index}`"
          class="answer-product"
        >
          <strong>{{ [product.position, product.type].filter(Boolean).join(" · ") || "Peça" }}</strong>
          <span v-for="item in product.codes" :key="`${item.brand}-${item.code}`">
            {{ [item.brand, item.code].filter(Boolean).join(" — ") }}
          </span>
        </div>
      </div>
    </header>

    <div v-if="!result.hasResults" class="empty-result" role="status">
      <strong>Nenhuma peça encontrada para esta consulta.</strong>
      <span>Tente informar a peça, o modelo do veículo e o ano.</span>
    </div>

    <div v-if="result.truncated" class="result-alert" role="status">
      Exibindo resultados parciais. A consulta encontrou mais registros do que o limite retornado pela API.
    </div>

    <div v-if="result.parts.length" class="result-toolbar">
      <div>
        <strong>{{ result.parts.length }}</strong>
        {{ result.parts.length === 1 ? "opção encontrada" : "opções encontradas" }}
      </div>
      <span v-if="confirmed.length">{{ confirmed.length }} com aplicação confirmada</span>
      <span v-if="probable.length || ambiguous.length">
        {{ probable.length + ambiguous.length }} para conferir
      </span>
    </div>

    <section
      v-for="section in sections"
      :key="section.status"
      class="compatibility-section"
      :class="section.status.toLowerCase()"
    >
      <header>
        <div>
          <h4>{{ sectionTitle(section.status) }}</h4>
          <p>{{ sectionDescription(section.status) }}</p>
        </div>
        <span>{{ section.parts.length }}</span>
      </header>
      <div class="parts-grid">
        <PartResultCard
          v-for="(part, partIndex) in section.parts"
          :key="part.key"
          :part="part"
          :index="partIndex"
          :assessment="assessmentForPart(part.code)"
        />
      </div>
    </section>
  </section>
</template>
