import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark' | 'system'
const key = 'financeiro.theme'
export function readTheme(): Theme {
  try {
    const stored = localStorage.getItem(key)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch { /* O app continua utilizável se o navegador bloquear armazenamento. */ }
  return 'light'
}
function apply(theme: Theme) {
  const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.dataset.theme = dark ? 'dark' : 'light'
}
// Executado antes da primeira renderização para respeitar a preferência salva.
apply(readTheme())

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(readTheme)
  useEffect(() => {
    apply(theme)
    try { localStorage.setItem(key, theme) } catch { /* Preferência só nesta sessão. */ }
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const refresh = () => apply(theme)
    media.addEventListener('change', refresh)
    return () => media.removeEventListener('change', refresh)
  }, [theme])
  return {theme, setTheme}
}
