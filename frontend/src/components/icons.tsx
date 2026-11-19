import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement> & { size?: number }
const paths: Record<string, React.ReactNode> = {
  cart: <><circle cx="9" cy="19" r="1"/><circle cx="18" cy="19" r="1"/><path d="M3 4h2l2.2 10.2a2 2 0 0 0 2 1.6h7.7a2 2 0 0 0 2-1.6L20 8H6"/></>,
  heart: <path d="M20.8 4.7a5.5 5.5 0 0 0-7.8 0L12 5.8l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.4 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
  filter: <path d="M4 6h16M7 12h10M10 18h4"/>, close: <path d="m6 6 12 12M18 6 6 18"/>,
  plus: <path d="M12 5v14M5 12h14"/>, trash: <><path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14M10 11v6M14 11v6"/></>,
  upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M5 14v6h14v-6"/></>, edit: <><path d="m4 20 4.5-1 10-10-3.5-3.5-10 10L4 20Z"/><path d="m13.5 6.5 3.5 3.5"/></>,
  star: <path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9L12 3Z"/>,
  image: <><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="9" r="1.5"/><path d="m4 17 5-5 4 4 2-2 5 5"/></>,
  chevron: <path d="m8 10 4 4 4-4"/>, telegram: <path d="m21 4-3 16-6-4-3 3v-5l9-7-11 6-4-2 18-7Z"/>,
  check: <path d="m5 12 4 4L19 6"/>, grip: <path d="M9 5h.01M15 5h.01M9 12h.01M15 12h.01M9 19h.01M15 19h.01"/>,
  eye: <><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></>,
  sparkles: <><path d="m12 3 1.2 3.8L17 8l-3.8 1.2L12 13l-1.2-3.8L7 8l3.8-1.2L12 3Z"/><path d="m19 14 .7 2.3L22 17l-2.3.7L19 20l-.7-2.3L16 17l2.3-.7L19 14ZM5 13l.8 2.2L8 16l-2.2.8L5 19l-.8-2.2L2 16l2.2-.8L5 13Z"/></>,
}

function Icon({ name, size = 20, ...props }: IconProps & { name: keyof typeof paths }) {
  return <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>
}

export const CartIcon = (p: IconProps) => <Icon name="cart" {...p}/>
export const HeartIcon = (p: IconProps) => <Icon name="heart" {...p}/>
export const SearchIcon = (p: IconProps) => <Icon name="search" {...p}/>
export const FilterIcon = (p: IconProps) => <Icon name="filter" {...p}/>
export const CloseIcon = (p: IconProps) => <Icon name="close" {...p}/>
export const PlusIcon = (p: IconProps) => <Icon name="plus" {...p}/>
export const TrashIcon = (p: IconProps) => <Icon name="trash" {...p}/>
export const UploadIcon = (p: IconProps) => <Icon name="upload" {...p}/>
export const EditIcon = (p: IconProps) => <Icon name="edit" {...p}/>
export const StarIcon = (p: IconProps) => <Icon name="star" {...p}/>
export const ImageIcon = (p: IconProps) => <Icon name="image" {...p}/>
export const ChevronIcon = (p: IconProps) => <Icon name="chevron" {...p}/>
export const TelegramIcon = (p: IconProps) => <Icon name="telegram" {...p}/>
export const CheckIcon = (p: IconProps) => <Icon name="check" {...p}/>
export const GripIcon = (p: IconProps) => <Icon name="grip" {...p}/>
export const EyeIcon = (p: IconProps) => <Icon name="eye" {...p}/>
export const SparklesIcon = (p: IconProps) => <Icon name="sparkles" {...p}/>
