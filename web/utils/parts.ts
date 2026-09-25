import type {
  AnswerSummary,
  CompatibilityLabel,
  NormalizedAnswerCode,
  NormalizedAnswerProduct,
  NormalizedPartSearch,
  ParsedAnswer,
  PartApiRecord,
  PartApplication,
  PartGroup,
  PartSearchApiResponse,
} from "~/types/part-search"

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function text(value: unknown): string {
  if (value == null) return ""
  if (typeof value === "string" || typeof value === "number") {
    return String(value).trim()
  }
  return ""
}

function numberOrNull(value: unknown): number | null {
  if (value == null || value === "") return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(text).filter(Boolean) : []
}

function compatibilityLabel(value: unknown): CompatibilityLabel {
  const normalized = text(value).toUpperCase()
  if (normalized === "CONFIRMED" || normalized === "PROBABLE" || normalized === "AMBIGUOUS") {
    return normalized
  }
  return "AMBIGUOUS"
}

function conservativeStatus(
  current: CompatibilityLabel,
  next: CompatibilityLabel,
): CompatibilityLabel {
  const order: Record<CompatibilityLabel, number> = {
    CONFIRMED: 0,
    PROBABLE: 1,
    AMBIGUOUS: 2,
  }
  return order[next] > order[current] ? next : current
}

function explicitTrue(value: unknown): boolean {
  if (value === true || value === 1) return true
  const normalized = text(value).toLocaleLowerCase("pt-BR")
  return ["true", "1", "sim", "original", "oem", "genuína", "genuina"].includes(normalized)
}

function isExplicitlyOriginal(row: PartApiRecord): boolean {
  return explicitTrue(row.is_original)
    || explicitTrue(row.supports_oem)
    || /\b(original|oem|genu[ií]na?)\b/i.test(text(row.origem))
    || /\b(original|oem|genu[ií]na?)\b/i.test(text(row.origin))
    || /\b(original|oem|genu[ií]na?)\b/i.test(text(row.marca))
}

function cleanJsonFence(value: string): string {
  const trimmed = value.trim()
  if (!trimmed.startsWith("```")) return trimmed
  return trimmed
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim()
}

function looksLikeSql(value: string): boolean {
  return /\b(select|from|where|join)\b/i.test(value)
}

function normalizeAnswerCode(value: unknown): NormalizedAnswerCode | null {
  if (!isRecord(value)) return null
  const code = text(value.code)
  if (!code) return null
  return { brand: text(value.brand), code }
}

function normalizeAnswerProduct(value: unknown): NormalizedAnswerProduct | null {
  if (!isRecord(value)) return null
  const codes = Array.isArray(value.codes)
    ? value.codes.map(normalizeAnswerCode).filter((item): item is NormalizedAnswerCode => Boolean(item))
    : []

  const position = text(value.position)
  const type = text(value.type)
  const assessment = text(value.assessment)
  if (!position && !type && !assessment && !codes.length) return null
  return { position, type, assessment, codes }
}

function answerSummaryFromObject(value: ParsedAnswer): AnswerSummary | null {
  const products = Array.isArray(value.products)
    ? value.products
        .map(normalizeAnswerProduct)
        .filter((item): item is NormalizedAnswerProduct => Boolean(item))
    : []
  const vehicle = text(value.vehicle)
  const year = text(value.year)
  const assessment = text(value.assessment)
  if (!vehicle && !year && !assessment && !products.length) return null
  return { vehicle, year, assessment, products, text: "" }
}

export function parseAnswer(value: unknown): AnswerSummary | null {
  if (value == null || value === "") return null
  if (isRecord(value)) return answerSummaryFromObject(value)
  if (typeof value !== "string") return null

  const cleaned = cleanJsonFence(value)
  if (!cleaned) return null
  try {
    const parsed: unknown = JSON.parse(cleaned)
    return isRecord(parsed) ? answerSummaryFromObject(parsed) : null
  } catch {
    if (looksLikeSql(cleaned)) return null
    return { vehicle: "", year: "", assessment: "", products: [], text: cleaned }
  }
}

function normalizeCodeKey(code: string): string {
  return code.toLocaleUpperCase("pt-BR").replace(/\s+/g, "")
}

function uniquePush(items: string[], value: string) {
  if (value && !items.some((item) => item.toLocaleLowerCase("pt-BR") === value.toLocaleLowerCase("pt-BR"))) {
    items.push(value)
  }
}

function applicationKey(application: PartApplication): string {
  return [
    application.make,
    application.model,
    application.variant,
    application.yearStart ?? "",
    application.yearEnd ?? "",
    application.engine,
    application.generation,
    application.transmission,
    application.fuel,
    application.body,
  ]
    .join("|")
    .toLocaleLowerCase("pt-BR")
}

function normalizeApplication(row: PartApiRecord): PartApplication {
  return {
    make: text(row.make),
    model: text(row.model),
    variant: text(row.variant),
    yearStart: numberOrNull(row.year_start),
    yearEnd: numberOrNull(row.year_end),
    engine: text(row.engine),
    generation: text(row.generation),
    transmission: text(row.transmission),
    fuel: text(row.fuel),
    body: text(row.body),
  }
}

function hasApplicationData(application: PartApplication): boolean {
  return Boolean(
    application.make
    || application.model
    || application.variant
    || application.yearStart != null
    || application.yearEnd != null
    || application.engine
    || application.generation
    || application.transmission
    || application.fuel
    || application.body
  )
}

function groupPartRows(rows: PartApiRecord[]): PartGroup[] {
  const groups = new Map<string, PartGroup>()

  rows.forEach((row, index) => {
    if (!isRecord(row)) return
    const code = text(row.codigo)
    const key = code ? normalizeCodeKey(code) : `__sem_codigo_${index}`
    let group = groups.get(key)
    if (!group) {
      group = {
        key,
        code,
        brands: [],
        descriptions: [],
        types: [],
        sources: [],
        equivalents: [],
        origin: "parallel",
        compatibility: compatibilityLabel(row.compatibility),
        confidence: numberOrNull(row.confidence) ?? 0,
        matched: isRecord(row.matched)
          ? row.matched as Record<string, boolean | null>
          : {},
        warnings: stringArray(row.warnings),
        conflicts: stringArray(row.conflicts),
        evidence: Array.isArray(row.evidence)
          ? row.evidence.filter(isRecord)
          : [],
        rank: numberOrNull(row.rank) ?? Number.MAX_SAFE_INTEGER,
        applications: [],
        recordCount: 0,
      }
      groups.set(key, group)
    }

    group.recordCount += 1
    uniquePush(group.brands, text(row.marca))
    uniquePush(group.descriptions, text(row.descricao))
    uniquePush(group.types, text(row.tipo))
    uniquePush(group.sources, text(row.fonte))
    if (isExplicitlyOriginal(row)) group.origin = "original"
    group.compatibility = conservativeStatus(
      group.compatibility,
      compatibilityLabel(row.compatibility),
    )
    const confidence = numberOrNull(row.confidence)
    if (confidence != null) {
      group.confidence = group.confidence
        ? Math.min(group.confidence, confidence)
        : confidence
    }
    const rank = numberOrNull(row.rank)
    if (rank != null) group.rank = Math.min(group.rank, rank)
    for (const warning of stringArray(row.warnings)) uniquePush(group.warnings, warning)
    for (const conflict of stringArray(row.conflicts)) uniquePush(group.conflicts, conflict)
    if (Array.isArray(row.equivalents)) {
      for (const value of row.equivalents) {
        const equivalent = normalizeAnswerCode(value)
        if (!equivalent) continue
        const equivalentKey = normalizeCodeKey(equivalent.code)
        if (
          equivalentKey !== normalizeCodeKey(group.code)
          && !group.equivalents.some((item) => normalizeCodeKey(item.code) === equivalentKey)
        ) {
          group.equivalents.push(equivalent)
        }
      }
    }

    const application = normalizeApplication(row)
    if (hasApplicationData(application)) {
      const key = applicationKey(application)
      if (!group.applications.some((item) => applicationKey(item) === key)) {
        group.applications.push(application)
      }
    }
  })

  const statusOrder: Record<CompatibilityLabel, number> = {
    CONFIRMED: 0,
    PROBABLE: 1,
    AMBIGUOUS: 2,
  }
  return [...groups.values()].sort((a, b) => {
    return statusOrder[a.compatibility] - statusOrder[b.compatibility]
      || (a.origin === "original" ? 0 : 1) - (b.origin === "original" ? 0 : 1)
      || b.confidence - a.confidence
      || a.rank - b.rank
      || a.code.localeCompare(b.code, "pt-BR", { numeric: true })
  })
}

export function normalizePartSearchResponse(payload: PartSearchApiResponse): NormalizedPartSearch {
  const rows = Array.isArray(payload.data) ? payload.data.filter(isRecord) : []
  const parts = groupPartRows(rows)
  const summary = parseAnswer(payload.answer)
  const rowCount = typeof payload.row_count === "number" && Number.isFinite(payload.row_count)
    ? payload.row_count
    : null

  return {
    summary,
    parts,
    rowCount,
    receivedCount: rows.length,
    truncated: payload.truncated === true,
    hasResults: parts.length > 0 || Boolean(summary?.products.length),
    compatibilityQuery: isRecord(payload.compatibility?.query)
      ? payload.compatibility?.query || null
      : null,
    compatibilityMetrics: isRecord(payload.compatibility?.metrics)
      ? payload.compatibility?.metrics || null
      : null,
  }
}
