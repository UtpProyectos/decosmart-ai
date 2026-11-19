export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="status-state error-state" role="alert">
      <strong>Algo no salió como esperábamos</strong>
      <p>{message}</p>
      {onRetry && (
        <button className="button secondary" onClick={onRetry}>
          Intentar de nuevo
        </button>
      )}
    </div>
  )
}
