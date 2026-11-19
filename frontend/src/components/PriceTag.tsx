export function PriceTag({ value, className = '' }: { value: string; className?: string }) {
  return <span className={`price ${className}`}>US$ {Number(value).toFixed(2)}</span>
}
