import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi, type ProductAdmin } from '../../api/admin'
import { assetUrl } from '../../api/client'
import { EditIcon, PlusIcon, TrashIcon } from '../../components/icons'
import { ErrorState } from '../../components/ErrorState'
import { Loading } from '../../components/Loading'
import { PriceTag } from '../../components/PriceTag'

export function AdminProducts() {
  const [products, setProducts] = useState<ProductAdmin[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = () => {
    setLoading(true)
    adminApi
      .products()
      .then((data) => setProducts(data.items))
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'No se pudieron cargar los productos.'),
      )
      .finally(() => setLoading(false))
  }
  useEffect(load, [])
  async function toggle(product: ProductAdmin) {
    const updated = await adminApi.updateProduct(product.id, { active: !product.active })
    setProducts((items) => items.map((item) => (item.id === updated.id ? updated : item)))
  }
  async function deactivate(product: ProductAdmin) {
    if (!window.confirm(`¿Desactivar ${product.name}?`)) return
    await adminApi.deactivateProduct(product.id)
    setProducts((items) =>
      items.map((item) => (item.id === product.id ? { ...item, active: false } : item)),
    )
  }
  return (
    <div className="container page admin-page">
      <header className="admin-heading">
        <div>
          <span className="eyebrow">Panel administrativo</span>
          <h1>Productos</h1>
          <p>{products.length} productos, incluidos los inactivos.</p>
        </div>
        <Link className="button" to="/admin/productos/nuevo">
          <PlusIcon /> Nuevo producto
        </Link>
      </header>
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Producto</th>
                <th>SKU</th>
                <th>Categoría</th>
                <th>Precio</th>
                <th>Stock</th>
                <th>Activo</th>
                <th>
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {products.map((product) => (
                <tr key={product.id} className={!product.active ? 'inactive' : ''}>
                  <td>
                    <div className="admin-product-cell">
                      <div className="admin-thumb">
                        {product.primary_image && (
                          <img src={assetUrl(product.primary_image)} alt="" />
                        )}
                      </div>
                      <strong>{product.name}</strong>
                    </div>
                  </td>
                  <td>{product.sku}</td>
                  <td>{product.category.name}</td>
                  <td>
                    <PriceTag value={product.price} />
                  </td>
                  <td>
                    <span className={product.low_stock ? 'low-stock-text' : ''}>
                      {product.stock}
                    </span>
                  </td>
                  <td>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={product.active}
                        onChange={() => void toggle(product)}
                        aria-label={`${product.active ? 'Desactivar' : 'Activar'} ${product.name}`}
                      />
                      <span />
                    </label>
                  </td>
                  <td>
                    <div className="table-actions">
                      <Link className="small-button" to={`/admin/productos/${product.id}`}>
                        <EditIcon size={16} /> Editar
                      </Link>
                      <button
                        className="small-button danger"
                        onClick={() => void deactivate(product)}
                        disabled={!product.active}
                      >
                        <TrashIcon size={16} /> Desactivar
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
