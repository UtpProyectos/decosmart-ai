import type { Category, Order, OrderRequest, Product, ProductList, PublicConfig, Quote, QuoteRequest } from '../types'

export const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export class ApiError extends Error {
  constructor(public code: string, message: string, public details: Record<string, unknown> = {}, public status = 0) { super(message); this.name = 'ApiError' }
}
type ErrorBody = { error?: { code?: string; message?: string; details?: Record<string, unknown> } }
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) {
    let body: ErrorBody = {}
    try { body = await response.json() as ErrorBody } catch { /* non-JSON error */ }
    throw new ApiError(body.error?.code || 'REQUEST_FAILED', body.error?.message || 'No pudimos completar la solicitud.', body.error?.details, response.status)
  }
  return response.json() as Promise<T>
}
export function assetUrl(url: string): string { return url.startsWith('/') ? `${API_BASE_URL}${url}` : url }
export interface ProductFilters { category?: string; q?: string; min_price?: number; max_price?: number; room?: string; in_stock?: boolean; limit?: number; offset?: number }
export const api = {
  categories: () => request<Category[]>('/api/categories'),
  products: (filters: ProductFilters = {}) => { const params = new URLSearchParams(); Object.entries(filters).forEach(([key, value]) => { if (value !== undefined && value !== '') params.set(key, String(value)) }); return request<ProductList>(`/api/products${params.size ? `?${params}` : ''}`) },
  product: (slug: string) => request<Product>(`/api/products/${encodeURIComponent(slug)}`),
  createQuote: (payload: QuoteRequest) => request<Quote>('/api/quotes', { method: 'POST', body: JSON.stringify(payload) }),
  quote: (code: string) => request<Quote>(`/api/quotes/${encodeURIComponent(code)}`),
  createOrder: (payload: OrderRequest) => request<Order>('/api/orders', { method: 'POST', body: JSON.stringify(payload) }),
  order: (code: string) => request<Order>(`/api/orders/${encodeURIComponent(code)}`),
  config: () => request<PublicConfig>('/api/config/public'),
}
