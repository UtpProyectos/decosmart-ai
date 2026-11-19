import { Fragment, useCallback, useEffect, useState } from 'react'
import {
  listOrders,
  listQuotes,
  updateOrderStatus,
  updateQuoteStatus,
  type AdminOrder,
  type AdminQuote,
  type OrderStatus,
  type QuoteStatus,
} from '../../api/admin'
import { ErrorState } from '../../components/ErrorState'
import { Loading } from '../../components/Loading'

type Kind = 'orders' | 'quotes'
type Row = AdminOrder | AdminQuote
type Action = { label: string; status: string; danger?: boolean; hint?: string }

const ORDER_LABELS: Record<OrderStatus, string> = {
  pending: 'Pendiente',
  confirmed: 'Confirmado',
  completed: 'Completado (venta)',
  cancelled: 'Cancelado',
}
const QUOTE_LABELS: Record<QuoteStatus, string> = {
  sent: 'Enviada',
  accepted: 'Aceptada',
  rejected: 'Rechazada',
  expired: 'Vencida',
}
const ORDER_ACTIONS: Record<string, Action[]> = {
  pending: [
    { label: 'Confirmar', status: 'confirmed', hint: 'Descuenta stock' },
    { label: 'Cancelar', status: 'cancelled', danger: true },
  ],
  confirmed: [
    { label: 'Marcar completado', status: 'completed', hint: 'Venta' },
    { label: 'Cancelar', status: 'cancelled', danger: true },
  ],
}
const QUOTE_ACTIONS: Record<string, Action[]> = {
  sent: [
    { label: 'Aceptar', status: 'accepted' },
    { label: 'Rechazar', status: 'rejected', danger: true },
  ],
}

const money = (value: string | number) =>
  Number(value).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const formatDate = (value: string | null) =>
  value ? new Date(value).toLocaleDateString('es-ES', { dateStyle: 'medium' }) : '—'

function customerOf(row: Row) {
  if ('customer' in row) {
    const c = row.customer
    return {
      name: c?.name || c?.telegram_username || 'Sin nombre',
      phone: c?.phone ?? null,
      address: null,
      notes: row.notes,
    }
  }
  return {
    name: row.contact_name || 'Sin nombre',
    phone: row.contact_phone,
    address: row.delivery_address,
    notes: null,
  }
}

function itemsSummary(row: Row) {
  const count = row.items.reduce((sum, item) => sum + item.quantity, 0)
  const names = row.items.map((item) => item.name || `Producto ${item.product_id}`).join(', ')
  return `${count} · ${names}`
}

export function AdminOrders() {
  const [kind, setKind] = useState<Kind>('orders')
  const [filter, setFilter] = useState('')
  const [rows, setRows] = useState<Row[]>([])
  const [summary, setSummary] = useState<{ orders: AdminOrder[]; quotes: AdminQuote[] }>({
    orders: [],
    quotes: [],
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setError('')
    const request =
      kind === 'orders'
        ? listOrders((filter || undefined) as OrderStatus | undefined)
        : listQuotes((filter || undefined) as QuoteStatus | undefined)
    return request
      .then((data) => setRows(data.items))
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'No se pudo cargar el listado.'),
      )
      .finally(() => setLoading(false))
  }, [kind, filter])
  const loadSummary = useCallback(() => {
    Promise.all([listOrders(), listQuotes()])
      .then(([orders, quotes]) => setSummary({ orders: orders.items, quotes: quotes.items }))
      .catch(() => undefined)
  }, [])
  useEffect(() => {
    void load()
  }, [load])
  useEffect(loadSummary, [loadSummary])

  function changeKind(next: Kind) {
    setKind(next)
    setFilter('')
    setExpanded(null)
    setActionError('')
  }

  async function apply(row: Row, action: Action) {
    const noun = kind === 'orders' ? 'el pedido' : 'la cotización'
    if (!window.confirm(`¿${action.label} ${noun} ${row.code}?`)) return
    setBusy(true)
    setActionError('')
    try {
      const updated =
        kind === 'orders'
          ? await updateOrderStatus(row.code, action.status as OrderStatus)
          : await updateQuoteStatus(row.code, action.status as QuoteStatus)
      setRows((current) =>
        filter && updated.status !== filter
          ? current.filter((item) => item.code !== row.code)
          : current.map((item) => (item.code === row.code ? updated : item)),
      )
      loadSummary()
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'No se pudo actualizar el estado.')
    } finally {
      setBusy(false)
    }
  }

  const labels: Record<string, string> = kind === 'orders' ? ORDER_LABELS : QUOTE_LABELS
  const actionsFor = (status: string) =>
    (kind === 'orders' ? ORDER_ACTIONS : QUOTE_ACTIONS)[status] ?? []
  const sales = summary.orders
    .filter((order) => order.status === 'completed')
    .reduce((sum, order) => sum + Number(order.total), 0)
  const count = (items: { status: string }[], status: string) =>
    items.filter((item) => item.status === status).length
  const cards = [
    { label: 'Pedidos pendientes', value: count(summary.orders, 'pending') },
    { label: 'Pedidos confirmados', value: count(summary.orders, 'confirmed') },
    { label: 'Ventas completadas', value: `US$ ${money(sales)}` },
    { label: 'Cotizaciones enviadas', value: count(summary.quotes, 'sent') },
  ]
  const filters = [['', kind === 'orders' ? 'Todos' : 'Todas'], ...Object.entries(labels)]

  return (
    <div className="container page admin-page">
      <header className="admin-heading">
        <div>
          <span className="eyebrow">Panel administrativo</span>
          <h1>Pedidos y cotizaciones</h1>
          <p>Los pedidos son de demostración: no hay cobro real.</p>
        </div>
      </header>
      <div className="order-summary">
        {cards.map((card) => (
          <div key={card.label}>
            <strong>{card.value}</strong>
            <span>{card.label}</span>
          </div>
        ))}
      </div>
      <div className="order-tabs" role="tablist">
        {(['orders', 'quotes'] as Kind[]).map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={kind === tab}
            className={`chip${kind === tab ? ' active' : ''}`}
            onClick={() => changeKind(tab)}
          >
            {tab === 'orders' ? 'Pedidos demo' : 'Cotizaciones'}
          </button>
        ))}
      </div>
      <div className="order-filters">
        {filters.map(([value, label]) => (
          <button
            key={value}
            className={`chip${filter === value ? ' active' : ''}`}
            aria-pressed={filter === value}
            onClick={() => setFilter(value)}
          >
            {label}
          </button>
        ))}
      </div>
      {actionError && (
        <p className="form-error" role="alert">
          {actionError}
        </p>
      )}
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : rows.length === 0 ? (
        <p className="admin-helper">No hay registros para este filtro.</p>
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Fecha</th>
                <th>Cliente</th>
                <th>Canal</th>
                <th>Ítems</th>
                <th>Total</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const info = customerOf(row)
                const open = expanded === row.code
                return (
                  <Fragment key={row.code}>
                    <tr
                      className="order-row"
                      onClick={() => setExpanded(open ? null : row.code)}
                      aria-expanded={open}
                    >
                      <td>{row.code}</td>
                      <td>{formatDate(row.created_at)}</td>
                      <td>{info.name}</td>
                      <td>{row.channel}</td>
                      <td>{itemsSummary(row)}</td>
                      <td>US$ {money(row.total)}</td>
                      <td>
                        <span className={`status-pill ${row.status}`}>{labels[row.status]}</span>
                      </td>
                    </tr>
                    {open && (
                      <tr className="order-detail">
                        <td colSpan={7}>
                          <div className="order-detail-grid">
                            <ul>
                              {row.items.map((item) => (
                                <li key={item.product_id}>
                                  {item.name || `Producto ${item.product_id}`} — {item.quantity} x
                                  US$ {money(item.unit_price)} = US$ {money(item.line_total)}
                                </li>
                              ))}
                            </ul>
                            <ul>
                              <li>Teléfono: {info.phone || '—'}</li>
                              {kind === 'orders' && <li>Dirección: {info.address || '—'}</li>}
                              {kind === 'quotes' && <li>Notas: {info.notes || '—'}</li>}
                            </ul>
                          </div>
                          <div className="button-row">
                            {actionsFor(row.status).map((action) => (
                              <button
                                key={action.status}
                                className={`small-button${action.danger ? ' danger' : ''}`}
                                disabled={busy}
                                onClick={() => void apply(row, action)}
                              >
                                {action.label}
                                {action.hint ? ` (${action.hint.toLowerCase()})` : ''}
                              </button>
                            ))}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
