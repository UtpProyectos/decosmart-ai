import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { product } from '../test/fixtures'
import { Catalog } from './Catalog'
describe('Catalog', () => {
  it('renders products returned by the API', async () => {
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
          json: async () => ({ items: [product], total: 1, limit: 20, offset: 0 }),
        }),
    )
    render(
      <MemoryRouter initialEntries={['/catalogo']}>
        <Routes>
          <Route path="/catalogo" element={<Catalog />} />
        </Routes>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText(product.name)).toBeInTheDocument())
    expect(screen.getByText('1 productos')).toBeInTheDocument()
  })
})
