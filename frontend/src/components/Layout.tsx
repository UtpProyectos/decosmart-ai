import { Outlet, ScrollRestoration } from 'react-router-dom'
import { Footer } from './Footer'
import { Header } from './Header'
import { TelegramButton } from './TelegramButton'
export function Layout() {
  return (
    <>
      <Header />
      <main>
        <Outlet />
      </main>
      <Footer />
      <TelegramButton floating />
      <ScrollRestoration />
    </>
  )
}
