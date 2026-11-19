import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export interface CartItem {
  productId: number
  slug: string
  name: string
  price: string
  image: string
  quantity: number
  maxStock: number
}
interface CartState {
  items: CartItem[]
  add: (item: CartItem) => void
  update: (productId: number, quantity: number) => void
  remove: (productId: number) => void
  clear: () => void
}
export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      add: (item) =>
        set((state) => {
          const current = state.items.find((entry) => entry.productId === item.productId)
          return {
            items: current
              ? state.items.map((entry) =>
                  entry.productId === item.productId
                    ? {
                        ...entry,
                        quantity: Math.min(entry.maxStock, entry.quantity + item.quantity),
                      }
                    : entry,
                )
              : [
                  ...state.items,
                  { ...item, quantity: Math.min(item.maxStock, Math.max(1, item.quantity)) },
                ],
          }
        }),
      update: (productId, quantity) =>
        set((state) => ({
          items: state.items.map((item) =>
            item.productId === productId
              ? { ...item, quantity: Math.min(item.maxStock, Math.max(1, quantity)) }
              : item,
          ),
        })),
      remove: (productId) =>
        set((state) => ({ items: state.items.filter((item) => item.productId !== productId) })),
      clear: () => set({ items: [] }),
    }),
    { name: 'decosmart-cart', storage: createJSONStorage(() => localStorage) },
  ),
)
export const selectCartCount = (state: CartState) =>
  state.items.reduce((total, item) => total + item.quantity, 0)
export const selectCartSubtotal = (state: CartState) =>
  state.items.reduce((total, item) => total + Number(item.price) * item.quantity, 0)
