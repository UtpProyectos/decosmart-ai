import { Link } from 'react-router-dom'
import { assetUrl } from '../api/client'
import { PriceTag } from '../components/PriceTag'
import { selectCartSubtotal, useCartStore } from '../store/cart'
export function Cart() {
  const items = useCartStore((state) => state.items)
  const update = useCartStore((state) => state.update)
  const remove = useCartStore((state) => state.remove)
  const subtotal = useCartStore(selectCartSubtotal)
  return (
    <div className="container page">
      <header className="page-header">
        <span className="eyebrow">Tu selección</span>
        <h1>Carrito</h1>
      </header>
      {!items.length ? (
        <div className="empty-state">
          <h2>Tu carrito está vacío</h2>
          <p>Explora el catálogo y guarda los muebles que te gustan.</p>
          <Link className="button" to="/catalogo">
            Ir al catálogo
          </Link>
        </div>
      ) : (
        <div className="cart-layout">
          <div className="cart-list">
            {items.map((item) => (
              <article className="cart-item" key={item.productId}>
                <img src={assetUrl(item.image)} alt={item.name} />
                <div>
                  <h2>
                    <Link to={`/producto/${item.slug}`}>{item.name}</Link>
                  </h2>
                  <PriceTag value={item.price} />
                </div>
                <label className="quantity">
                  <span>Cantidad</span>
                  <input
                    aria-label={`Cantidad de ${item.name}`}
                    type="number"
                    min="1"
                    max={item.maxStock}
                    value={item.quantity}
                    onChange={(event) => update(item.productId, Number(event.target.value))}
                  />
                </label>
                <button className="text-button" onClick={() => remove(item.productId)}>
                  Quitar
                </button>
              </article>
            ))}
          </div>
          <aside className="summary-card">
            <h2>Resumen</h2>
            <div>
              <span>Subtotal</span>
              <strong>US$ {subtotal.toFixed(2)}</strong>
            </div>
            <p>El stock y los precios se validarán al solicitar la cotización.</p>
            <Link className="button full" to="/cotizacion">
              Solicitar cotización
            </Link>
            <Link className="button secondary full" to="/checkout">
              Crear pedido demo
            </Link>
          </aside>
        </div>
      )}
    </div>
  )
}
