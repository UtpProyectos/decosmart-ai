import { Link } from 'react-router-dom'
export function NotFound() {
  return (
    <div className="container page">
      <div className="empty-state not-found">
        <span>404</span>
        <h1>Esta página no está en nuestro catálogo</h1>
        <p>Puede que el enlace haya cambiado o ya no esté disponible.</p>
        <Link className="button" to="/">
          Volver al inicio
        </Link>
      </div>
    </div>
  )
}
