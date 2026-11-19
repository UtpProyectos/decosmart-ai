import { Link } from 'react-router-dom'
export function Footer() {
  return (
    <footer className="site-footer" id="contacto">
      <div className="container footer-grid">
        <div>
          <strong className="footer-logo">DS / DecoSmart</strong>
          <p>Muebles para espacios reales, con medidas claras y asistencia visual.</p>
        </div>
        <div>
          <h2>Explora</h2>
          <Link to="/catalogo">Catálogo</Link>
          <Link to="/carrito">Tu carrito</Link>
          <Link className="admin-link" to="/admin">
            Admin
          </Link>
        </div>
        <div>
          <h2>Una nota importante</h2>
          <p>
            Las simulaciones con IA son orientativas y pueden variar en escala, color y acabado.
          </p>
        </div>
      </div>
      <p className="container copyright">
        © {new Date().getFullYear()} DecoSmart · Precios en dólares estadounidenses.
      </p>
    </footer>
  )
}
