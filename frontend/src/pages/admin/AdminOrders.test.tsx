import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AdminOrders } from './AdminOrders'

const item = {
  product_id: 1,
  name: 'Sofá Nórdico',
  quantity: 2,
  unit_price: '100.00',
  line_total: '200.00',
}
const order = (code: string, status: string) => ({
  id: 1,
  code,
  status,
  channel: 'web',
  total: '200.00',
  currency: 'USD',
  is_demo: true,
  quote_code: null,
  items: [item],
  contact_name: 'Ana Pérez',
  contact_email: null,
  contact_phone: '555-1234',
  delivery_address: 'Calle 1',
  created_at: '2026-11-18T10:00:00',
})
const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

function mockApi(orders: unknown[]) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'PATCH') return ok(order('PED-1', 'confirmed'))
    if (url.includes('/admin/orders')) return ok({ items: orders, total: orders.length })
    return ok({ items: [], total: 0 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

afterEach(() => vi.restoreAllMocks())

describe('AdminOrders', () => {
  it('renders the orders list', async () => {
    mockApi([order('PED-1', 'pending')])
    render(<AdminOrders />)
    expect(await screen.findByText('PED-1')).toBeInTheDocument()
    expect(screen.getByText('Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText(/Los pedidos son de demostración/)).toBeInTheDocument()
  })

  it('queries by status when a filter chip is clicked', async () => {
    const fetchMock = mockApi([order('PED-1', 'pending')])
    render(<AdminOrders />)
    await screen.findByText('PED-1')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmado' }))
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes('status=confirmed'))).toBe(
        true,
      ),
    )
  })

  it('confirms a pending order with PATCH', async () => {
    const fetchMock = mockApi([order('PED-1', 'pending')])
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    render(<AdminOrders />)
    await userEvent.click(await screen.findByText('PED-1'))
    await userEvent.click(screen.getByRole('button', { name: /^Confirmar/ }))
    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(([, init]) => init?.method === 'PATCH')
      expect(patch?.[0]).toContain('/admin/orders/PED-1')
      expect(patch?.[1]?.body).toBe(JSON.stringify({ status: 'confirmed' }))
    })
  })

  it('shows only valid actions per status', async () => {
    mockApi([order('PED-1', 'confirmed'), order('PED-2', 'completed')])
    render(<AdminOrders />)
    await userEvent.click(await screen.findByText('PED-1'))
    expect(screen.getByRole('button', { name: /Marcar completado/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Confirmar/ })).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('PED-1'))
    await userEvent.click(screen.getByText('PED-2'))
    expect(screen.queryByRole('button', { name: /Cancelar/ })).not.toBeInTheDocument()
  })
})
