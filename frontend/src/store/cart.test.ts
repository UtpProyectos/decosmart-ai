import { beforeEach, describe, expect, it } from 'vitest'; import { selectCartCount, selectCartSubtotal, useCartStore } from './cart'
const item = { productId: 1, slug: 'sofa', name: 'Sofá', price: '100.50', image: '/sofa.jpg', quantity: 1, maxStock: 3 }
describe('cart store', () => {
  beforeEach(() => useCartStore.setState({ items: [] }))
  it('adds products and merges quantities', () => { useCartStore.getState().add(item); useCartStore.getState().add({ ...item, quantity: 2 }); expect(useCartStore.getState().items[0].quantity).toBe(3); expect(selectCartCount(useCartStore.getState())).toBe(3) })
  it('updates with stock bounds', () => { useCartStore.getState().add(item); useCartStore.getState().update(1, 12); expect(useCartStore.getState().items[0].quantity).toBe(3) })
  it('removes products', () => { useCartStore.getState().add(item); useCartStore.getState().remove(1); expect(useCartStore.getState().items).toEqual([]) })
  it('computes subtotal with decimal prices', () => { useCartStore.getState().add({ ...item, quantity: 2 }); expect(selectCartSubtotal(useCartStore.getState())).toBe(201) })
  it('persists under the expected localStorage key', () => { useCartStore.getState().add(item); expect(localStorage.getItem('decosmart-cart')).toContain('Sofá') })
})
