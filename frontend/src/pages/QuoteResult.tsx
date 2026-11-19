import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ErrorState } from '../components/ErrorState'
import { Loading } from '../components/Loading'
import { PriceTag } from '../components/PriceTag'
import { useApi } from '../hooks/useApi'
export function QuoteResult() {
  const { code = '' } = useParams()
  const { data: quote, loading, error, retry } = useApi(() => api.quote(code), [code])
  if (loading)
    return (
      <div className="container page">
        <Loading />
      </div>
    )
  if (error || !quote)
    return (
      <div className="container page">
        <ErrorState message={error || 'Cotización no encontrada.'} onRetry={retry} />
      </div>
    )
  return (
    <div className="container page narrow">
      <div className="result-card">
        <span className="result-icon" aria-hidden="true">
          ✓
        </span>
        <span className="eyebrow">Cotización creada</span>
        <h1>{quote.code}</h1>
        <p>
          Válida hasta el {new Date(`${quote.valid_until}T12:00:00`).toLocaleDateString('es-PE')}.
        </p>
        <div className="quote-items">
          {quote.items.map((item) => (
            <div key={item.product_id}>
              <span>
                {item.quantity} × {item.name}
              </span>
              <PriceTag value={item.line_total} />
            </div>
          ))}
        </div>
        <div className="result-total">
          <span>Total</span>
          <PriceTag value={quote.total} />
        </div>
        <p className="disclaimer">{quote.disclaimer}</p>
        <Link className="button full" to={`/checkout?quote=${encodeURIComponent(quote.code)}`}>
          Convertir en pedido demo
        </Link>
        <Link className="text-link" to="/catalogo">
          Seguir explorando
        </Link>
      </div>
    </div>
  )
}
