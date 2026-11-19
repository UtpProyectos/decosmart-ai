import { FormEvent, KeyboardEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { adminApi, type AdminCategory, type ProductAdmin, type ProductWrite } from '../../api/admin'
import { ApiError } from '../../api/client'
import { CheckIcon, CloseIcon, PlusIcon } from '../../components/icons'
import { Loading } from '../../components/Loading'
import { ImageManager } from './ImageManager'

const emptyProduct: ProductWrite = {
  sku: '',
  category_slug: '',
  name: '',
  slug: '',
  description: '',
  price: '',
  stock: 0,
  width_cm: 0,
  height_cm: 0,
  depth_cm: 0,
  colors: [],
  material: '',
  style: '',
  room_types: [],
  active: true,
}
type Errors = Partial<Record<keyof ProductWrite | 'form', string>>

function ChipInput({
  label,
  values,
  onChange,
}: {
  label: string
  values: string[]
  onChange: (values: string[]) => void
}) {
  const [draft, setDraft] = useState('')
  const add = () => {
    const value = draft.trim()
    if (value && !values.includes(value)) onChange([...values, value])
    setDraft('')
  }
  const keyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      add()
    }
  }
  return (
    <label className="field chip-input">
      <span>{label}</span>
      <div className="chip-input-box">
        {values.map((value) => (
          <span className="chip active" key={value}>
            {value}
            <button
              type="button"
              onClick={() => onChange(values.filter((item) => item !== value))}
              aria-label={`Quitar ${value}`}
            >
              <CloseIcon size={13} />
            </button>
          </span>
        ))}
        <input
          aria-label={`Agregar ${label.toLowerCase()}`}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={keyDown}
          onBlur={add}
          placeholder="Escribe y pulsa Enter"
        />
      </div>
    </label>
  )
}

export function AdminProductForm() {
  const { id } = useParams()
  const productId = id ? Number(id) : undefined
  const editing = Number.isFinite(productId)
  const navigate = useNavigate()
  const [value, setValue] = useState<ProductWrite>(emptyProduct)
  const [product, setProduct] = useState<ProductAdmin>()
  const [categories, setCategories] = useState<AdminCategory[]>([])
  const [errors, setErrors] = useState<Errors>({})
  const [loading, setLoading] = useState(editing)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  useEffect(() => {
    adminApi
      .categories()
      .then((items) => {
        setCategories(items)
        if (!editing && items[0])
          setValue((current) => ({
            ...current,
            category_slug: current.category_slug || items[0].slug,
          }))
      })
      .catch(() => setErrors({ form: 'No se pudieron cargar las categorías.' }))
    if (editing && productId)
      adminApi
        .product(productId)
        .then((item) => {
          setProduct(item)
          setValue({
            sku: item.sku,
            category_slug: item.category.slug,
            name: item.name,
            slug: item.slug,
            description: item.description || '',
            price: item.price,
            stock: item.stock,
            width_cm: item.dimensions.width_cm,
            height_cm: item.dimensions.height_cm,
            depth_cm: item.dimensions.depth_cm,
            colors: item.colors,
            material: item.material || '',
            style: item.style || '',
            room_types: item.room_types,
            active: item.active,
          })
        })
        .catch((reason: unknown) =>
          setErrors({
            form: reason instanceof Error ? reason.message : 'No se pudo cargar el producto.',
          }),
        )
        .finally(() => setLoading(false))
  }, [editing, productId])
  const set = <K extends keyof ProductWrite>(key: K, next: ProductWrite[K]) =>
    setValue((current) => ({ ...current, [key]: next }))
  const validate = () => {
    const next: Errors = {}
    if (!value.sku.trim()) next.sku = 'El SKU es obligatorio.'
    if (!value.name.trim()) next.name = 'El nombre es obligatorio.'
    if (!value.description.trim()) next.description = 'La descripción es obligatoria.'
    if (!value.category_slug) next.category_slug = 'Selecciona una categoría.'
    if (!/^\d+(\.\d{1,2})?$/.test(value.price) || Number(value.price) <= 0)
      next.price = 'Ingresa un precio válido con hasta 2 decimales.'
    if (value.stock < 0) next.stock = 'El stock no puede ser negativo.'
    if (value.width_cm <= 0) next.width_cm = 'Ingresa el ancho.'
    if (value.height_cm <= 0) next.height_cm = 'Ingresa el alto.'
    if (value.depth_cm <= 0) next.depth_cm = 'Ingresa la profundidad.'
    if (!value.colors.length) next.colors = 'Agrega al menos un color.'
    setErrors(next)
    return !Object.keys(next).length
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaved(false)
    if (!validate()) return
    setSaving(true)
    setErrors({})
    const payload: ProductWrite = {
      ...value,
      sku: value.sku.trim(),
      name: value.name.trim(),
      slug: value.slug?.trim() || undefined,
      description: value.description.trim(),
      price: Number(value.price).toFixed(2),
      material: value.material?.trim() || null,
      style: value.style?.trim() || null,
    }
    try {
      const result =
        editing && productId
          ? await adminApi.updateProduct(productId, payload)
          : await adminApi.createProduct(payload)
      setProduct(result)
      setSaved(true)
      if (!editing) navigate(`/admin/productos/${result.id}`, { replace: true })
    } catch (reason) {
      if (reason instanceof ApiError) {
        if (reason.code === 'SKU_TAKEN') setErrors({ sku: reason.message })
        else if (reason.code === 'SLUG_TAKEN') setErrors({ slug: reason.message })
        else if (reason.code === 'VALIDATION_ERROR') {
          const details = reason.details as Record<string, string>
          setErrors({ ...details, form: reason.message })
        } else setErrors({ form: reason.message })
      } else setErrors({ form: 'No se pudo guardar el producto.' })
    } finally {
      setSaving(false)
    }
  }
  if (loading)
    return (
      <div className="container page">
        <Loading label="Cargando producto…" />
      </div>
    )
  return (
    <div className="container page admin-page">
      <header className="admin-heading">
        <div>
          <Link className="back-link" to="/admin">
            ← Productos
          </Link>
          <span className="eyebrow">Panel administrativo</span>
          <h1>{editing ? 'Editar producto' : 'Nuevo producto'}</h1>
        </div>
      </header>
      <form className="admin-product-form" onSubmit={submit} noValidate>
        <section className="admin-form-section">
          <div className="admin-section-heading">
            <div>
              <h2>Información del producto</h2>
              <p>Los datos públicos del catálogo y del agente de DecoSmart.</p>
            </div>
            <label className="switch labeled">
              <span>Producto activo</span>
              <input
                type="checkbox"
                checked={value.active}
                onChange={(event) => set('active', event.target.checked)}
              />
              <i />
            </label>
          </div>
          <div className="form-grid">
            <label className="field">
              <span>SKU *</span>
              <input
                value={value.sku}
                onChange={(event) => set('sku', event.target.value)}
                aria-invalid={Boolean(errors.sku)}
              />
              {errors.sku && <small className="field-error">{errors.sku}</small>}
            </label>
            <label className="field">
              <span>Categoría *</span>
              <select
                value={value.category_slug}
                onChange={(event) => set('category_slug', event.target.value)}
                aria-invalid={Boolean(errors.category_slug)}
              >
                <option value="">Selecciona una categoría</option>
                {categories.map((category) => (
                  <option value={category.slug} key={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              {errors.category_slug && (
                <small className="field-error">{errors.category_slug}</small>
              )}
            </label>
            <label className="field">
              <span>Nombre *</span>
              <input
                value={value.name}
                onChange={(event) => set('name', event.target.value)}
                aria-invalid={Boolean(errors.name)}
              />
              {errors.name && <small className="field-error">{errors.name}</small>}
            </label>
            <label className="field">
              <span>Slug</span>
              <input
                value={value.slug}
                onChange={(event) => set('slug', event.target.value)}
                placeholder="Se genera desde el nombre"
              />
              {errors.slug && <small className="field-error">{errors.slug}</small>}
            </label>
            <label className="field full-span">
              <span>Descripción *</span>
              <textarea
                rows={5}
                value={value.description}
                onChange={(event) => set('description', event.target.value)}
                aria-invalid={Boolean(errors.description)}
              />
              {errors.description && <small className="field-error">{errors.description}</small>}
            </label>
            <label className="field">
              <span>Precio (USD) *</span>
              <input
                inputMode="decimal"
                value={value.price}
                onChange={(event) => set('price', event.target.value)}
                aria-invalid={Boolean(errors.price)}
              />
              {errors.price && <small className="field-error">{errors.price}</small>}
            </label>
            <label className="field">
              <span>Stock *</span>
              <input
                type="number"
                min="0"
                value={value.stock}
                onChange={(event) => set('stock', Number(event.target.value))}
              />
              {errors.stock && <small className="field-error">{errors.stock}</small>}
            </label>
          </div>
        </section>
        <section className="admin-form-section">
          <h2>Características</h2>
          <div className="form-grid three-columns">
            <label className="field">
              <span>Ancho (cm) *</span>
              <input
                type="number"
                min="1"
                value={value.width_cm}
                onChange={(event) => set('width_cm', Number(event.target.value))}
              />
              {errors.width_cm && <small className="field-error">{errors.width_cm}</small>}
            </label>
            <label className="field">
              <span>Alto (cm) *</span>
              <input
                type="number"
                min="1"
                value={value.height_cm}
                onChange={(event) => set('height_cm', Number(event.target.value))}
              />
              {errors.height_cm && <small className="field-error">{errors.height_cm}</small>}
            </label>
            <label className="field">
              <span>Profundidad (cm) *</span>
              <input
                type="number"
                min="1"
                value={value.depth_cm}
                onChange={(event) => set('depth_cm', Number(event.target.value))}
              />
              {errors.depth_cm && <small className="field-error">{errors.depth_cm}</small>}
            </label>
            <label className="field">
              <span>Material</span>
              <input
                value={value.material || ''}
                onChange={(event) => set('material', event.target.value)}
              />
            </label>
            <label className="field">
              <span>Estilo</span>
              <input
                value={value.style || ''}
                onChange={(event) => set('style', event.target.value)}
              />
            </label>
          </div>
          <ChipInput
            label="Colores *"
            values={value.colors}
            onChange={(items) => set('colors', items)}
          />
          {errors.colors && <small className="field-error">{errors.colors}</small>}
          <ChipInput
            label="Ambientes"
            values={value.room_types || []}
            onChange={(items) => set('room_types', items)}
          />
        </section>
        {errors.form && (
          <p className="form-error" role="alert">
            {errors.form}
          </p>
        )}
        <div className="admin-save-bar">
          <Link className="button secondary" to="/admin">
            Cancelar
          </Link>
          {saved && (
            <span className="save-success">
              <CheckIcon /> Cambios guardados
            </span>
          )}
          <button className="button" disabled={saving}>
            {saving ? (
              'Guardando…'
            ) : (
              <>
                <PlusIcon /> Guardar producto
              </>
            )}
          </button>
        </div>
      </form>
      {editing && productId && product && (
        <ImageManager productId={productId} initialImages={product.images} />
      )}{' '}
      {!editing && <p className="admin-helper">Guarda el producto para poder añadir imágenes.</p>}
    </div>
  )
}
