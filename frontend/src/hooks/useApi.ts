import { useCallback, useEffect, useState } from 'react'
/* Callers pass inline loaders and an explicit dependency list defining when to reload. */
/* eslint-disable react-hooks/exhaustive-deps */
export function useApi<T>(loader: () => Promise<T>, dependencies: React.DependencyList = []) {
  const [data, setData] = useState<T>()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = useCallback(() => {
    setLoading(true)
    setError('')
    loader()
      .then(setData)
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : 'Error inesperado'),
      )
      .finally(() => setLoading(false))
  }, dependencies)
  useEffect(load, [load])
  return { data, error, loading, retry: load }
}
