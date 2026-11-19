export function Loading({ label = 'Cargando…' }: { label?: string }) { return <div className="status-state" role="status"><span className="spinner" aria-hidden="true" />{label}</div> }
