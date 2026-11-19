import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { product } from '../test/fixtures'
import { Catalog } from './Catalog'

const chair = {
  ...product,
  id: 2,
  sku: 'DS-SIL-001',
  slug: 'silla',
  name: 'Silla Ada',
  price: '199.00',
  material: 'Madera',
  category: { slug: 'sillas', name: 'Sillas' },
}
const sofa = {
  ...product,
  id: 3,
  slug: 'sofa-zeta',
  name: 'Sofá Zeta',
  price: '899.00',
  material: 'Tela',
}
function mockCatalog() {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [{ id: 1, slug: 'sofas', name: 'Sofás', product_count: 1 }],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [sofa, chair], total: 2, limit: 50, offset: 0 }),
      }),
  )
}
function renderCatalog() {
  render(
    <MemoryRouter initialEntries={['/catalogo']}>
      <Routes>
        <Route path="/catalogo" element={<Catalog />} />
        <Route path="/catalogo/:categoria" element={<Catalog />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Catalog filters and sort', () => {
  it('sorts rendered products by ascending price', async () => {
    mockCatalog()
    renderCatalog()
    await screen.findByText('Silla Ada')
    await userEvent.selectOptions(screen.getByLabelText('Ordenar productos'), 'price-asc')
    const grid = document.querySelector<HTMLElement>('.product-grid')!
    const names = within(grid)
      .getAllByRole('heading')
      .map((node) => node.textContent)
    expect(names).toEqual(['Silla Ada', 'Sofá Zeta'])
  })
  it('filters products with a material chip', async () => {
    mockCatalog()
    renderCatalog()
    await screen.findByText('Silla Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Madera' }))
    await waitFor(() => expect(screen.queryByText('Sofá Zeta')).not.toBeInTheDocument())
    expect(screen.getByText('Silla Ada')).toBeInTheDocument()
  })
})
