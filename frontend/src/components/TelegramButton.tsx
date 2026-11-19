import { TelegramIcon } from './icons'
const defaultUrl = import.meta.env.VITE_TELEGRAM_BOT_URL || 'https://t.me/DecoSmartBot'
export function TelegramButton({ sku, floating = false, children }: { sku?: string; floating?: boolean; children?: React.ReactNode }) {
  const separator = defaultUrl.includes('?') ? '&' : '?'
  const href = sku ? `${defaultUrl}${separator}start=sim_${encodeURIComponent(sku)}` : defaultUrl
  return <a className={floating ? 'telegram-button floating' : 'button telegram-button'} href={href} target="_blank" rel="noreferrer" aria-label={floating ? 'Hablar con DecoSmart por Telegram' : undefined}><TelegramIcon/>{children ?? <span className="sr-only">Telegram</span>}</a>
}
