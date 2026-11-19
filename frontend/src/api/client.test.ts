import { describe, expect, it } from 'vitest'; import { API_BASE_URL, assetUrl } from './client'
describe('assetUrl', () => {
  it('prefixes relative backend assets', () => expect(assetUrl('/static/products/sofa.jpg')).toBe(`${API_BASE_URL}/static/products/sofa.jpg`))
  it('keeps absolute URLs unchanged', () => expect(assetUrl('https://cdn.example.com/sofa.jpg')).toBe('https://cdn.example.com/sofa.jpg'))
})
