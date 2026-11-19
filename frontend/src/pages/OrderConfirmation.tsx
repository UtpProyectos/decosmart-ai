import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ErrorState } from '../components/ErrorState'
import { Loading } from '../components/Loading'
import { PriceTag } from '../components/PriceTag'
import { useApi } from '../hooks/useApi'
export function OrderConfirmation() {
  const { code = '' } = useParams()
  const { data: order, loading, error, retry } = useApi(() => api.order(code), [code])
  if (loading)
    return (
      <div className="container page">
        <Loading />
      </div>
    )
  if (error || !order)
    return (
      <div className="container page">
        <ErrorState message={error || 'Pedido no encontrado.'} onRetry={retry} />
      </div>
    )
  return (
    <div className="container page narrow">
      <div className="result-card">
        <span className="result-icon" aria-hidden="true">
          ✓
        </span>
        <span className="eyebrow">Pedido registrado</span>
        <h1>{order.code}</h1>
        <p>
          Estado: <strong>{order.status === 'pending' ? 'Pendiente' : order.status}</strong>
        </p>
        <div className="result-total">
          <span>Total referencial</span>
          <PriceTag value={order.total} />
        </div>
        <div className="demo-warning">
          <strong>Pedido de demostración. No se realizó ningún cobro.</strong>
          <p>{order.message}</p>
        </div>
        <Link className="button full" to="/catalogo">
          Volver al catálogo
        </Link>
      </div>
    </div>
  )
}
