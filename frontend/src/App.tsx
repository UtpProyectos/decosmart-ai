import { lazy, Suspense } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Loading } from './components/Loading'
import { Cart } from './pages/Cart'
import { Catalog } from './pages/Catalog'
import { Checkout } from './pages/Checkout'
import { Home } from './pages/Home'
import { NotFound } from './pages/NotFound'
import { OrderConfirmation } from './pages/OrderConfirmation'
import { ProductDetail } from './pages/ProductDetail'
import { QuoteRequestPage } from './pages/QuoteRequest'
import { QuoteResult } from './pages/QuoteResult'

const AdminLayout = lazy(() =>
  import('./pages/admin/AdminLayout').then((module) => ({ default: module.AdminLayout })),
)
const AdminProducts = lazy(() =>
  import('./pages/admin/AdminProducts').then((module) => ({ default: module.AdminProducts })),
)
const AdminProductForm = lazy(() =>
  import('./pages/admin/AdminProductForm').then((module) => ({ default: module.AdminProductForm })),
)
const AdminOrders = lazy(() =>
  import('./pages/admin/AdminOrders').then((module) => ({ default: module.AdminOrders })),
)
const deferred = (element: React.ReactNode) => (
  <Suspense
    fallback={
      <div className="container page">
        <Loading />
      </div>
    }
  >
    {element}
  </Suspense>
)

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: '/', element: <Home /> },
      { path: '/catalogo', element: <Catalog /> },
      { path: '/catalogo/:categoria', element: <Catalog /> },
      { path: '/producto/:slug', element: <ProductDetail /> },
      { path: '/carrito', element: <Cart /> },
      { path: '/cotizacion', element: <QuoteRequestPage /> },
      { path: '/cotizacion/:code', element: <QuoteResult /> },
      { path: '/checkout', element: <Checkout /> },
      { path: '/pedido/:code', element: <OrderConfirmation /> },
      {
        path: '/admin',
        element: deferred(<AdminLayout />),
        children: [
          { index: true, element: deferred(<AdminProducts />) },
          { path: 'pedidos', element: deferred(<AdminOrders />) },
          { path: 'productos/nuevo', element: deferred(<AdminProductForm />) },
          { path: 'productos/:id', element: deferred(<AdminProductForm />) },
        ],
      },
      { path: '*', element: <NotFound /> },
    ],
  },
])
export function App() {
  return <RouterProvider router={router} />
}
