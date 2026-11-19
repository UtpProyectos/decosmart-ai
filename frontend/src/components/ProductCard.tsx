import { Link } from 'react-router-dom'
import { assetUrl } from '../api/client'
import type { Product } from '../types'
import { PriceTag } from './PriceTag'
import { StockBadge } from './StockBadge'
export function ProductCard({ product }: { product: Product }) { return <article className="product-card"><Link to={`/producto/${product.slug}`} className="product-image-wrap"><img src={assetUrl(product.primary_image)} alt={product.name} className="product-image" /></Link><div className="product-card-body"><span className="eyebrow">{product.category.name}</span><h3><Link to={`/producto/${product.slug}`}>{product.name}</Link></h3><div className="card-meta"><PriceTag value={product.price} /><StockBadge inStock={product.in_stock} lowStock={product.low_stock} /></div></div></article> }
