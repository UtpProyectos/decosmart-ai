import { FormEvent, useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { ADMIN_KEY_STORAGE, adminApi } from '../../api/admin'
import { ApiError } from '../../api/client'
import { Loading } from '../../components/Loading'

export function AdminLayout() {
  const [status, setStatus] = useState<'checking' | 'ready' | 'auth'>('checking')
  const [error, setError] = useState('')
  const check = () => {
    setStatus('checking')
    setError('')
    adminApi
      .products()
      .then(() => setStatus('ready'))
      .catch((reason: unknown) => {
        if (reason instanceof ApiError && reason.status === 401) setStatus('auth')
        else {
          setError(reason instanceof Error ? reason.message : 'No se pudo abrir el panel.')
          setStatus('auth')
        }
      })
  }
  useEffect(check, [])
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const key = String(new FormData(event.currentTarget).get('admin_key') || '')
    sessionStorage.setItem(ADMIN_KEY_STORAGE, key)
    check()
  }
  if (status === 'checking')
    return (
      <div className="container page">
        <Loading label="Verificando acceso…" />
      </div>
    )
  if (status === 'auth')
    return (
      <div className="container page admin-auth">
        <form className="form-card" onSubmit={submit}>
          <span className="logo-mark">DS</span>
          <h1>Acceso administrativo</h1>
          <p>Ingresa la clave configurada para gestionar el catálogo.</p>
          <label className="field">
            <span>Clave de administración</span>
            <input name="admin_key" type="password" autoFocus required />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="button full">Continuar</button>
        </form>
      </div>
    )
  return <Outlet />
}
