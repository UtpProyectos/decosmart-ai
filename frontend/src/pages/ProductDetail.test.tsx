import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { product } from '../test/fixtures'
import { ProductDetail } from './ProductDetail'

describe('ProductDetail gallery', () => {
  it('switches the main image when a thumbnail is clicked', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...product, description: 'Cómodo', images: [{ id: 1, url: '/front.jpg', alt: 'Vista frontal' }, { id: 2, url: '/side.jpg', alt: 'Vista lateral' }] }) }))
    render(<MemoryRouter initialEntries={['/producto/sofa-oslo']}><Routes><Route path="/producto/:slug" element={<ProductDetail/>}/></Routes></MemoryRouter>)
    await waitFor(() => expect(screen.getByAltText('Vista frontal')).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: `Ver imagen 2 de ${product.name}` }))
    expect(screen.getByAltText('Vista lateral')).toHaveAttribute('src', expect.stringContaining('/side.jpg'))
  })

  it('increments quantity and adds the selected quantity', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...product, description: 'Cómodo' }) }))
    render(<MemoryRouter initialEntries={['/producto/sofa-oslo']}><Routes><Route path="/producto/:slug" element={<ProductDetail/>}/></Routes></MemoryRouter>)
    await waitFor(() => expect(screen.getByRole('heading', { name: product.name })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: '+' })); await userEvent.click(screen.getByRole('button', { name: 'Agregar al carrito' }))
    expect(screen.getByText(/Producto agregado/)).toBeInTheDocument()
  })
})
