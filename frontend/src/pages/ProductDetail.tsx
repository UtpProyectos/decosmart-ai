import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, assetUrl } from '../api/client'
import { DimensionList } from '../components/DimensionList'
import { ErrorState } from '../components/ErrorState'
import { Loading } from '../components/Loading'
import { PriceTag } from '../components/PriceTag'
import { StockBadge } from '../components/StockBadge'
import { TelegramButton } from '../components/TelegramButton'
import { useApi } from '../hooks/useApi'
import { useCartStore } from '../store/cart'

export function ProductDetail() {
  const { slug = '' } = useParams()
  const { data: product, loading, error, retry } = useApi(() => api.product(slug), [slug])
  const add = useCartStore((state) => state.add)
  const [quantity, setQuantity] = useState(1)
  const [selectedImage, setSelectedImage] = useState(0)
  const [added, setAdded] = useState(false)
  useEffect(() => setSelectedImage(0), [slug])
  if (loading)
    return (
      <div className="container page">
        <Loading label="Cargando producto…" />
      </div>
    )
  if (error || !product)
    return (
      <div className="container page">
        <ErrorState message={error || 'Producto no encontrado.'} onRetry={retry} />
      </div>
    )
  const images = product.images?.length
    ? product.images
    : [{ url: product.primary_image, alt: product.name }]
  const current = images[selectedImage] || images[0]
  const addToCart = () => {
    add({
      productId: product.id,
      slug: product.slug,
      name: product.name,
      price: product.price,
      image: product.primary_image,
      quantity,
      maxStock: product.stock,
    })
    setAdded(true)
  }
  return (
    <div className="container page">
      <Link className="back-link" to={`/catalogo/${product.category.slug}`}>
        ← Volver a {product.category.name}
      </Link>
      <div className="product-detail">
        <div className="gallery">
          <div className="detail-gallery">
            <img src={assetUrl(current.url)} alt={current.alt || product.name} />
          </div>
          {images.length > 1 && (
            <div className="gallery-thumbnails" aria-label="Imágenes del producto">
              {images.map((image, index) => (
                <button
                  className={index === selectedImage ? 'selected' : ''}
                  type="button"
                  key={`${image.url}-${index}`}
                  onClick={() => setSelectedImage(index)}
                  aria-label={`Ver imagen ${index + 1} de ${product.name}`}
                  aria-pressed={index === selectedImage}
                >
                  <img src={assetUrl(image.url)} alt="" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="detail-info">
          <span className="eyebrow">{product.category.name}</span>
          <h1>{product.name}</h1>
          <div className="detail-price">
            <PriceTag value={product.price} />
            <StockBadge inStock={product.in_stock} lowStock={product.low_stock} />
          </div>
          <p>{product.description}</p>
          <h2>Dimensiones</h2>
          <DimensionList dimensions={product.dimensions} />
          <div className="product-spec">
            <strong>Material</strong>
            <span>{product.material || 'No especificado'}</span>
          </div>
          <div>
            <strong>Colores disponibles</strong>
            <div className="color-chips">
              {product.colors.map((color) => (
                <span key={color}>{color}</span>
              ))}
            </div>
          </div>
          <div className="purchase-panel">
            <div className="stepper" aria-label="Cantidad">
              <button
                type="button"
                onClick={() => setQuantity(Math.max(1, quantity - 1))}
                disabled={quantity <= 1}
              >
                −
              </button>
              <output aria-label="Cantidad seleccionada">{quantity}</output>
              <button
                type="button"
                onClick={() => setQuantity(Math.min(product.stock, quantity + 1))}
                disabled={!product.in_stock || quantity >= product.stock}
              >
                +
              </button>
            </div>
            <button className="button" disabled={!product.in_stock} onClick={addToCart}>
              Agregar al carrito
            </button>
            <Link className="button secondary" to="/cotizacion">
              Solicitar cotización
            </Link>
          </div>
          {added && (
            <p className="success-note" role="status">
              Producto agregado. <Link to="/carrito">Ver carrito</Link>
            </p>
          )}
          <TelegramButton sku={product.sku}>Simular en mi ambiente</TelegramButton>
          <p className="disclaimer">La simulación generada por IA es orientativa.</p>
        </div>
      </div>
    </div>
  )
}
