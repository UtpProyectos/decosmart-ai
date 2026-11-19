import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { product } from '../test/fixtures'
import { ProductCard } from './ProductCard'
describe('ProductCard', () => {
  it('renders the API price and low-stock state', () => {
    render(
      <MemoryRouter>
        <ProductCard product={product} />
      </MemoryRouter>,
    )
    expect(screen.getByText('US$ 649.00')).toBeInTheDocument()
    expect(screen.getByText('Últimas unidades')).toBeInTheDocument()
  })
  it('links to the product detail', () => {
    render(
      <MemoryRouter>
        <ProductCard product={product} />
      </MemoryRouter>,
    )
    expect(screen.getAllByRole('link', { name: product.name })[0]).toHaveAttribute(
      'href',
      '/producto/sofa-oslo',
    )
  })
})
