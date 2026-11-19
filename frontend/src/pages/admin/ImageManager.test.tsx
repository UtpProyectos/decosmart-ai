import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { ProductImage } from '../../api/admin'
import { ImageManager } from './ImageManager'

const first: ProductImage = {
  id: 1,
  url: '/one.jpg',
  alt: 'Frente',
  is_primary: true,
  is_reference: false,
  sort_order: 0,
  width: 800,
  height: 800,
}
const second: ProductImage = {
  id: 2,
  url: '/two.jpg',
  alt: 'Lado',
  is_primary: false,
  is_reference: false,
  sort_order: 1,
  width: 800,
  height: 800,
}

describe('ImageManager', () => {
  it('uploads selected files as multipart field files', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 201, json: async () => ({ images: [first] }) })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<ImageManager productId={7} initialImages={[]} />)
    const file = new File(['image'], 'sofa.webp', { type: 'image/webp' })
    await userEvent.upload(container.querySelector('input[type="file"]') as HTMLInputElement, file)
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = fetchMock.mock.calls[0][1].body as FormData
    expect(body.getAll('files')).toHaveLength(1)
    expect(body.get('is_reference')).toBe('false')
  })

  it('sets primary and reference with the right PATCH bodies', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ...second, is_primary: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ ...second, is_primary: true, is_reference: true }),
      })
    vi.stubGlobal('fetch', fetchMock)
    render(<ImageManager productId={7} initialImages={[first, second]} />)
    await userEvent.click(screen.getAllByRole('button', { name: 'Marcar como principal' })[1])
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ is_primary: true })
    await userEvent.click(screen.getAllByRole('button', { name: 'Alternar Referencia IA' })[1])
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ is_reference: true })
  })

  it('reorders with accessible down control', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({ images: [second, first] }) })
    vi.stubGlobal('fetch', fetchMock)
    render(<ImageManager productId={7} initialImages={[first, second]} />)
    await userEvent.click(screen.getAllByRole('button', { name: 'Mover imagen abajo' })[0])
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ image_ids: [2, 1] })
  })
})
