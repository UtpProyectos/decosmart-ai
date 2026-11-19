import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AdminProductForm } from './AdminProductForm'

function renderForm() {
  render(
    <MemoryRouter initialEntries={['/admin/productos/nuevo']}>
      <Routes>
        <Route path="/admin/productos/nuevo" element={<AdminProductForm />} />
        <Route path="/admin/productos/:id" element={<div>Producto guardado</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AdminProductForm', () => {
  it('shows client-side validation and does not submit invalid values', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [{ id: 1, slug: 'sofas', name: 'Sofás' }],
      })
    vi.stubGlobal('fetch', fetchMock)
    renderForm()
    await screen.findByRole('option', { name: 'Sofás' })
    await userEvent.click(screen.getByRole('button', { name: /Guardar producto/ }))
    expect(screen.getByText('El SKU es obligatorio.')).toBeInTheDocument()
    expect(screen.getByText('El nombre es obligatorio.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('submits the exact ProductWrite payload', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [{ id: 1, slug: 'sofas', name: 'Sofás' }],
      })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({ id: 9 }) })
    vi.stubGlobal('fetch', fetchMock)
    renderForm()
    const user = userEvent.setup()
    await screen.findByRole('option', { name: 'Sofás' })
    await user.type(screen.getByLabelText('SKU *'), 'DS-SOF-009')
    await user.type(screen.getByLabelText('Nombre *'), 'Sofá Lino')
    await user.type(screen.getByLabelText('Descripción *'), 'Sofá compacto de lino')
    await user.type(screen.getByLabelText('Precio (USD) *'), '499')
    await user.clear(screen.getByLabelText('Stock *'))
    await user.type(screen.getByLabelText('Stock *'), '5')
    for (const [label, amount] of [
      ['Ancho (cm) *', '160'],
      ['Alto (cm) *', '85'],
      ['Profundidad (cm) *', '88'],
    ] as const) {
      await user.clear(screen.getByLabelText(label))
      await user.type(screen.getByLabelText(label), amount)
    }
    await user.type(screen.getByLabelText('Agregar colores *'), 'crudo')
    await user.keyboard('{Enter}')
    await user.click(screen.getByRole('button', { name: /Guardar producto/ }))
    await screen.findByText('Producto guardado')
    const payload = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(payload).toEqual({
      sku: 'DS-SOF-009',
      category_slug: 'sofas',
      name: 'Sofá Lino',
      description: 'Sofá compacto de lino',
      price: '499.00',
      stock: 5,
      width_cm: 160,
      height_cm: 85,
      depth_cm: 88,
      colors: ['crudo'],
      material: null,
      style: null,
      room_types: [],
      active: true,
    })
  })
})
