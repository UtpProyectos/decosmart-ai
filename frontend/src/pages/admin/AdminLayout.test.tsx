import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AdminLayout } from './AdminLayout'

describe('AdminLayout authentication', () => {
  it('shows the key prompt after 401 and retries with X-Admin-Key', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ error: { code: 'UNAUTHORIZED', message: 'Clave requerida' } }) }).mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ items: [], total: 0 }) })
    vi.stubGlobal('fetch', fetchMock)
    render(<MemoryRouter initialEntries={['/admin']}><Routes><Route path="/admin" element={<AdminLayout/>}><Route index element={<div>Panel listo</div>}/></Route></Routes></MemoryRouter>)
    await screen.findByRole('heading', { name: 'Acceso administrativo' }); await userEvent.type(screen.getByLabelText('Clave de administración'), 'secreta'); await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    await screen.findByText('Panel listo'); await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2)); expect(fetchMock.mock.calls[1][1].headers['X-Admin-Key']).toBe('secreta')
  })
})
