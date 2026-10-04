import { useEffect, useRef, type ReactNode } from 'react'
import { X, Inbox, LoaderCircle, CircleAlert } from 'lucide-react'

export function ErrorBox({message}: {message: string}) {
  return message ? <div className="error" role="alert"><CircleAlert size={17}/><span>{message}</span></div> : null
}
export function Loading() { return <div className="loading"><LoaderCircle size={19} className="spin"/> Carregando…</div> }
export function Empty({title, children}: {title: string; children?: ReactNode}) {
  return <div className="empty"><Inbox size={30}/><h3>{title}</h3><div>{children}</div></div>
}
export function Modal({title, subtitle, children, close, wide = false}: {title: string; subtitle?: string; children: ReactNode; close: () => void; wide?: boolean}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current!
    const previous = document.activeElement as HTMLElement | null
    dialog.showModal()
    return () => { dialog.close(); previous?.focus() }
  }, [])
  return <dialog ref={ref} className={wide ? 'modal wide' : 'modal'} aria-label={title} onCancel={e => {e.preventDefault(); close()}}>
    <div className="modal-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-button" onClick={close} aria-label="Fechar"><X size={20}/></button></div>
    {children}
  </dialog>
}
export const kindLabels = {income: 'Entrada', expense: 'Despesa', transfer: 'Transferência / fatura', investment: 'Investimento', adjustment: 'Ajuste'}
