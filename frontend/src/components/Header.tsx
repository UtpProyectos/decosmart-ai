import { NavLink } from 'react-router-dom'
import { selectCartCount, useCartStore } from '../store/cart'
export function Header() { const count = useCartStore(selectCartCount); return <header className="site-header"><div className="container header-inner"><NavLink className="logo" to="/" aria-label="DecoSmart, inicio"><span className="logo-mark">D</span>DecoSmart</NavLink><nav aria-label="Navegación principal"><NavLink to="/catalogo">Catálogo</NavLink><NavLink to="/carrito">Carrito <span className="cart-count" aria-label={`${count} productos`}>{count}</span></NavLink></nav></div></header> }
