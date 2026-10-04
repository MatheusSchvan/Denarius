import { useEffect, useState } from 'react'

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {...options, headers: options.body instanceof FormData ? options.headers : {'Content-Type': 'application/json', ...options.headers}})
  } catch {
    throw new Error('Não consegui conectar ao aplicativo. Confira se o servidor está aberto e tente novamente.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => null)
    const detail = data?.detail
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: {msg: string}) => e.msg).join(' · ') : 'Não foi possível concluir a operação.')
  }
  return response.json()
}

export function upload<T>(path: string, file: File) {
  const data = new FormData()
  data.append('file', file)
  return api<T>(path, {method: 'POST', body: data})
}

export function useLoad<T>(path: string, revision = 0) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    api<T>(path).then(value => { if (active) setData(value) }).catch(err => { if (active) setError(err.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [path, revision])
  return {data, error, loading}
}

export const money = (cents: number) => (cents / 100).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'})
export const day = (value: string) => value.slice(0, 10).split('-').reverse().join('/')
export const monthLabel = (value: string) => new Date(`${value}-02T12:00:00`).toLocaleDateString('pt-BR', {month: 'long', year: 'numeric'})
export const today = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function parseMoney(input: string) {
  const clean = input.trim().replace(/\./g, '')
  if (!/^\d+(,\d{1,2})?$/.test(clean)) throw new Error('Digite o valor como 120,50, usando vírgula para os centavos.')
  const [whole, fraction = ''] = clean.split(',')
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
  if (!Number.isSafeInteger(cents) || cents <= 0 || cents >= 10_000_000_000) throw new Error('Informe um valor positivo menor que R$ 100 milhões.')
  return cents
}
