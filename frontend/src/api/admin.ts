import { API_BASE_URL, ApiError } from './client'

export const ADMIN_KEY_STORAGE = 'decosmart-admin-key'
export interface ProductImage {
  id: number
  url: string
  alt: string
  is_primary: boolean
  is_reference: boolean
  sort_order: number
  width: number | null
  height: number | null
}
export interface AdminCategory {
  id: number
  slug: string
  name: string
}
export interface ProductWrite {
  sku: string
  category_slug: string
  name: string
  slug?: string
  description: string
  price: string
  stock: number
  width_cm: number
  height_cm: number
  depth_cm: number
  colors: string[]
  material?: string | null
  style?: string | null
  room_types?: string[]
  active?: boolean
}
export interface ProductAdmin {
  id: number
  sku: string
  slug: string
  name: string
  category: { slug: string; name: string }
  description: string
  price: string
  currency: 'USD'
  stock: number
  in_stock: boolean
  low_stock: boolean
  dimensions: { width_cm: number; height_cm: number; depth_cm: number }
  colors: string[]
  material: string | null
  style: string | null
  room_types: string[]
  primary_image: string
  active: boolean
  images: ProductImage[]
  created_at: string
  updated_at: string
}
export type OrderStatus = 'pending' | 'confirmed' | 'completed' | 'cancelled'
export type QuoteStatus = 'sent' | 'accepted' | 'rejected' | 'expired'
export interface OrderItem {
  product_id: number
  name: string | null
  quantity: number
  unit_price: string
  line_total: string
}
export interface QuoteItem extends OrderItem {
  sku: string | null
}
export interface AdminOrder {
  id: number
  code: string
  status: OrderStatus
  channel: string
  total: string
  currency: 'USD'
  is_demo: boolean
  quote_code: string | null
  items: OrderItem[]
  contact_name: string | null
  contact_email: string | null
  contact_phone: string | null
  delivery_address: string | null
  created_at: string | null
}
export interface AdminQuote {
  id: number
  code: string
  status: QuoteStatus
  channel: string
  total: string
  subtotal: string
  currency: 'USD'
  items: QuoteItem[]
  valid_until: string
  notes: string | null
  customer: {
    id: number
    name: string | null
    email: string | null
    phone: string | null
    telegram_username: string | null
  } | null
  sent_at: string | null
  created_at: string | null
}
type ErrorBody = { error?: { code?: string; message?: string; details?: Record<string, unknown> } }

function headers(contentType = true): HeadersInit {
  const result: Record<string, string> = {}
  const key = sessionStorage.getItem(ADMIN_KEY_STORAGE)
  if (contentType) result['Content-Type'] = 'application/json'
  if (key) result['X-Admin-Key'] = key
  return result
}
async function request<T>(path: string, init: RequestInit = {}, json = true): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...headers(json), ...init.headers },
  })
  if (!response.ok) {
    let body: ErrorBody = {}
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      /* empty/non-json */
    }
    throw new ApiError(
      body.error?.code || 'REQUEST_FAILED',
      body.error?.message || 'No se pudo completar la solicitud.',
      body.error?.details,
      response.status,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const adminApi = {
  products: () =>
    request<{ items: ProductAdmin[]; total: number }>('/admin/products?include_inactive=true'),
  product: (id: number) => request<ProductAdmin>(`/admin/products/${id}`),
  categories: () => request<AdminCategory[]>('/admin/categories'),
  createProduct: (payload: ProductWrite) =>
    request<ProductAdmin>('/admin/products', { method: 'POST', body: JSON.stringify(payload) }),
  updateProduct: (id: number, payload: Partial<ProductWrite>) =>
    request<ProductAdmin>(`/admin/products/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deactivateProduct: (id: number) => request<void>(`/admin/products/${id}`, { method: 'DELETE' }),
  uploadImages: (id: number, files: File[], isReference: boolean) => {
    const body = new FormData()
    files.forEach((file) => body.append('files', file))
    body.append('is_reference', String(isReference))
    return request<{ images: ProductImage[] }>(
      `/admin/products/${id}/images`,
      { method: 'POST', body },
      false,
    )
  },
  updateImage: (
    productId: number,
    imageId: number,
    payload: Partial<Pick<ProductImage, 'alt' | 'is_primary' | 'is_reference' | 'sort_order'>>,
  ) =>
    request<ProductImage>(`/admin/products/${productId}/images/${imageId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  reorderImages: (productId: number, imageIds: number[]) =>
    request<{ images: ProductImage[] }>(`/admin/products/${productId}/images/order`, {
      method: 'PUT',
      body: JSON.stringify({ image_ids: imageIds }),
    }),
  deleteImage: (productId: number, imageId: number) =>
    request<void>(`/admin/products/${productId}/images/${imageId}`, { method: 'DELETE' }),
}

const listPath = (resource: 'orders' | 'quotes', status?: string) =>
  `/admin/${resource}?limit=200${status ? `&status=${status}` : ''}`
const patchStatus = (resource: 'orders' | 'quotes', code: string, status: string) => ({
  path: `/admin/${resource}/${code}`,
  init: { method: 'PATCH', body: JSON.stringify({ status }) },
})

export const listOrders = (status?: OrderStatus) =>
  request<{ items: AdminOrder[]; total: number }>(listPath('orders', status))
export const listQuotes = (status?: QuoteStatus) =>
  request<{ items: AdminQuote[]; total: number }>(listPath('quotes', status))
export function updateOrderStatus(code: string, status: OrderStatus) {
  const { path, init } = patchStatus('orders', code, status)
  return request<AdminOrder>(path, init)
}
export function updateQuoteStatus(code: string, status: QuoteStatus) {
  const { path, init } = patchStatus('quotes', code, status)
  return request<AdminQuote>(path, init)
}
