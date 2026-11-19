export interface Category {
  id: number
  slug: string
  name: string
  product_count: number
}
export interface ProductCategory {
  slug: string
  name: string
}
export interface Dimensions {
  width_cm: number
  height_cm: number
  depth_cm: number
}
export interface ProductImage {
  id?: number
  url: string
  alt: string
  is_primary?: boolean
  is_reference?: boolean
  sort_order?: number
  width?: number | null
  height?: number | null
}
export interface Product {
  id: number
  sku: string
  slug: string
  name: string
  category: ProductCategory
  price: string
  currency: 'USD'
  stock: number
  in_stock: boolean
  low_stock: boolean
  dimensions: Dimensions
  colors: string[]
  material: string | null
  style: string | null
  room_types: string[]
  primary_image: string
  description?: string
  images?: ProductImage[]
}
export interface ProductList {
  items: Product[]
  total: number
  limit: number
  offset: number
}
export interface CustomerInput {
  name: string
  email: string
  phone: string
}
export interface CommerceItemInput {
  product_id: number
  quantity: number
}
export interface QuoteRequest {
  customer: CustomerInput
  items: CommerceItemInput[]
  notes?: string
  channel: 'web'
}
export interface QuoteItem {
  product_id: number
  name: string
  quantity: number
  unit_price: string
  line_total: string
}
export interface Quote {
  code: string
  status: string
  items: QuoteItem[]
  subtotal: string
  total: string
  currency: 'USD'
  valid_until: string
  disclaimer: string
}
export interface OrderRequest {
  quote_code?: string
  customer: CustomerInput
  items?: CommerceItemInput[]
  delivery_address: string
  channel: 'web'
}
export interface Order {
  code: string
  status: string
  total: string
  is_demo: boolean
  message: string
}
export interface PublicConfig {
  telegram_bot_url: string
  store_name: string
  currency: 'USD'
}
