import { useState } from 'react'
import { Link } from 'react-router-dom'
import { assetUrl } from '../api/client'
import { useCartStore } from '../store/cart'
import type { Product } from '../types'
import { CartIcon, HeartIcon } from './icons'
import { PriceTag } from './PriceTag'
import { StockBadge } from './StockBadge'

const favoriteKey = 'decosmart-favorites'
function getFavorites(): number[] { try { return JSON.parse(localStorage.getItem(favoriteKey) || '[]') as number[] } catch { return [] } }

export function ProductCard({ product }: { product: Product }) {
  const add = useCartStore((state) => state.add)
  const [favorite, setFavorite] = useState(() => getFavorites().includes(product.id))
  const toggleFavorite = () => { const next = favorite ? getFavorites().filter((id) => id !== product.id) : [...new Set([...getFavorites(), product.id])]; localStorage.setItem(favoriteKey, JSON.stringify(next)); setFavorite(!favorite) }
  const quickAdd = () => add({ productId: product.id, slug: product.slug, name: product.name, price: product.price, image: product.primary_image, quantity: 1, maxStock: product.stock })
  return <article className="product-card">
    <div className="product-image-wrap"><Link to={`/producto/${product.slug}`} aria-label={product.name}><img src={assetUrl(product.primary_image)} alt="" className="product-image" /></Link><StockBadge inStock={product.in_stock} lowStock={product.low_stock}/><div className="card-actions"><button className={`icon-button${favorite ? ' active' : ''}`} type="button" aria-label={favorite ? `Quitar ${product.name} de favoritos` : `Guardar ${product.name} en favoritos`} onClick={toggleFavorite}><HeartIcon/></button><button className="icon-button" type="button" aria-label={`Agregar ${product.name} al carrito`} disabled={!product.in_stock} onClick={quickAdd}><CartIcon/></button></div></div>
    <div className="product-card-body"><h3><Link to={`/producto/${product.slug}`}>{product.name}</Link></h3><PriceTag value={product.price}/></div>
  </article>
}
