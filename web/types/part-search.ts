export interface PartApiRecord {
  codigo?: unknown
  descricao?: unknown
  marca?: unknown
  make?: unknown
  model?: unknown
  variant?: unknown
  tipo?: unknown
  fonte?: unknown
  is_original?: unknown
  supports_oem?: unknown
  origem?: unknown
  origin?: unknown
  equivalents?: unknown
  compatibility?: unknown
  confidence?: unknown
  matched?: unknown
  warnings?: unknown
  conflicts?: unknown
  evidence?: unknown
  position?: unknown
  part_family?: unknown
  engine?: unknown
  generation?: unknown
  rank?: unknown
  year_start?: unknown
  year_end?: unknown
  [key: string]: unknown
}

export interface AnswerCode {
  brand?: unknown
  code?: unknown
}

export interface AnswerProduct {
  position?: unknown
  type?: unknown
  assessment?: unknown
  codes?: unknown
}

export interface ParsedAnswer {
  vehicle?: unknown
  year?: unknown
  assessment?: unknown
  products?: unknown
  [key: string]: unknown
}

export interface PartSearchApiResponse {
  success: boolean
  answer?: string | ParsedAnswer | null
  data?: PartApiRecord[] | null
  message?: string | null
  error?: string | null
  row_count?: number | null
  truncated?: boolean | null
  compatibility?: {
    query?: Record<string, unknown>
    metrics?: Record<string, unknown>
  } | null
}

export type CompatibilityLabel = "CONFIRMED" | "PROBABLE" | "AMBIGUOUS"

export interface NormalizedAnswerCode {
  brand: string
  code: string
}

export interface NormalizedAnswerProduct {
  position: string
  type: string
  assessment: string
  codes: NormalizedAnswerCode[]
}

export interface AnswerSummary {
  vehicle: string
  year: string
  assessment: string
  products: NormalizedAnswerProduct[]
  text: string
}

export interface PartApplication {
  make: string
  model: string
  variant: string
  yearStart: number | null
  yearEnd: number | null
  engine: string
  generation: string
  transmission: string
  fuel: string
  body: string
}

export interface PartGroup {
  key: string
  code: string
  brands: string[]
  descriptions: string[]
  types: string[]
  sources: string[]
  equivalents: NormalizedAnswerCode[]
  origin: "original" | "parallel"
  compatibility: CompatibilityLabel
  confidence: number
  matched: Record<string, boolean | null>
  warnings: string[]
  conflicts: string[]
  evidence: Array<Record<string, unknown>>
  rank: number
  applications: PartApplication[]
  recordCount: number
}

export interface NormalizedPartSearch {
  summary: AnswerSummary | null
  parts: PartGroup[]
  rowCount: number | null
  receivedCount: number
  truncated: boolean
  hasResults: boolean
  compatibilityQuery: Record<string, unknown> | null
  compatibilityMetrics: Record<string, unknown> | null
}

export interface ChatHistoryItem {
  role: "user" | "assistant"
  content: string
}
