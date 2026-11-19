import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useCartStore } from '../store/cart'
import { QuoteRequestPage } from './QuoteRequest'
function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>
}
describe('QuoteRequest', () => {
  beforeEach(() =>
    useCartStore.setState({
      items: [
        {
          productId: 7,
          slug: 'mesa',
          name: 'Mesa',
          price: '149.00',
          image: '/mesa.jpg',
          quantity: 2,
          maxStock: 5,
        },
      ],
    }),
  )
  it('posts customer and cart items then navigates', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ code: 'COT-20261118-0001' }) })
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/cotizacion']}>
        <Routes>
          <Route path="/cotizacion" element={<QuoteRequestPage />} />
          <Route path="/cotizacion/:code" element={<Location />} />
        </Routes>
      </MemoryRouter>,
    )
    await user.type(screen.getByLabelText('Nombre completo'), 'Ana Pérez')
    await user.type(screen.getByLabelText('Correo electrónico'), 'ana@example.com')
    await user.type(screen.getByLabelText('Teléfono'), '+51999999999')
    await user.click(screen.getByRole('button', { name: 'Enviar solicitud' }))
    await waitFor(() =>
      expect(screen.getByTestId('location')).toHaveTextContent('/cotizacion/COT-20261118-0001'),
    )
    const [, init] = fetchMock.mock.calls[0]
    expect(JSON.parse(init.body)).toEqual({
      customer: { name: 'Ana Pérez', email: 'ana@example.com', phone: '+51999999999' },
      items: [{ product_id: 7, quantity: 2 }],
      channel: 'web',
    })
  })
})
