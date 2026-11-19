import { Link, NavLink } from 'react-router-dom'
import { selectCartCount, useCartStore } from '../store/cart'
import { CartIcon } from './icons'

export function Header() {
  const count = useCartStore(selectCartCount)
  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link className="logo" to="/" aria-label="DecoSmart, inicio">
          <span className="logo-mark">DS</span>
          <span>DecoSmart</span>
        </Link>
        <nav aria-label="Navegación principal">
          <NavLink to="/">Inicio</NavLink>
          <NavLink to="/catalogo">Catálogo</NavLink>
          <a href="#simulacion">Simular con IA</a>
          <a href="#contacto">Contacto</a>
        </nav>
        <Link className="cart-pill" to="/carrito">
          <CartIcon size={17} /> <span>Carrito ({count})</span>
        </Link>
      </div>
    </header>
  )
}
