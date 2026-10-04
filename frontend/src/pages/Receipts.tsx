import { useRef, useState } from 'react'
import { ArrowRight, Check, FileText, Link, ReceiptText, Upload } from 'lucide-react'
import { api, day, money, upload, useLoad } from '../api'
import { Empty, ErrorBox, Loading, Modal } from '../components'
import type { PageProps, Receipt, ReceiptDetail, ReceiptItem, ReceiptPreview } from '../types'

export default function Receipts({revision, changed, notify, categories}: PageProps) {
  const state = useLoad<Receipt[]>('/receipts', revision)
  const input = useRef<HTMLInputElement>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [preview, setPreview] = useState<{file: File; data: ReceiptPreview} | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function choose(file: File) {
    setError(''); setBusy(true)
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('O limite é de 5 MB por arquivo.')
      setPreview({file, data: await upload<ReceiptPreview>('/receipts/preview', file)})
    } catch (e) {setError((e as Error).message)} finally {setBusy(false); if(input.current) input.current.value = ''}
  }
  async function save() {
    if (!preview) return
    setError(''); setBusy(true)
    try {
      const result = await upload<{id: number}>('/receipts', preview.file)
      setPreview(null); changed(); setSelected(result.id); notify('Nota salva. Escolha a compra correspondente para vincular.')
    } catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  return <>
    <section className="receipt-explainer"><div className="receipt-explainer-icon"><ReceiptText size={23}/></div><div><h2>Uma compra, todos os itens.</h2><p>Importe o XML e vincule à compra do extrato. A nota detalha o gasto, sem gerar uma segunda despesa.</p></div><input ref={input} className="sr-only" type="file" accept=".xml" aria-label="XML da nota" onChange={e => e.target.files?.[0] && choose(e.target.files[0])}/><button className="button" disabled={busy} onClick={() => input.current?.click()}><Upload size={16}/>{busy ? 'Lendo…' : 'Importar XML'}</button></section>
    <ErrorBox message={error}/>
    <section className="panel"><div className="panel-heading"><div><h2>Notas cadastradas</h2><p>{state.data?.length || 0} notas · Todos os períodos</p></div></div><ErrorBox message={state.error}/>{state.loading ? <Loading/> : state.data?.length ? <div className="table-scroll"><table><thead><tr><th>Estabelecimento</th><th>Data</th><th>Itens</th><th>Vínculo</th><th className="number">Total</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{state.data.map(r => <tr key={r.id}><td><div className="file-title compact"><FileText size={17}/><strong>{r.merchant}</strong></div></td><td className="nowrap muted">{day(r.date)}</td><td className="muted">{r.item_count}</td><td><span className={`badge ${r.transaction_id ? '' : 'amber'}`}>{r.transaction_id ? <><Check size={12}/> Vinculada</> : 'Aguardando vínculo'}</span></td><td className="number amount">{money(r.total_cents)}</td><td><button className="text-button" onClick={() => setSelected(r.id)}>Conferir <ArrowRight size={14}/></button></td></tr>)}</tbody></table></div> : !state.error && <Empty title="Suas notas aparecem aqui">Use o XML da NF-e ou NFC-e para importar os produtos da compra.</Empty>}</section>
    <p className="footnote">Nesta versão, a leitura funciona por XML. Fotos, PDFs e QR Code ficam para a próxima etapa.</p>
    {preview && <Modal wide title="Conferir nota" subtitle={preview.file.name} close={() => {if(!busy) {setPreview(null); setError('')}}}><div className="form-body"><ErrorBox message={error}/><div className="receipt-summary"><div><h3>{preview.data.merchant}</h3><p>{day(preview.data.date)} · {preview.data.items.length} itens</p></div><strong>{money(preview.data.total_cents)}</strong></div>{preview.data.warnings.map(w => <div className="warning" key={w}>{w}</div>)}<ItemTable items={preview.data.items}/></div><div className="modal-actions"><button className="button secondary" disabled={busy} onClick={() => setPreview(null)}>Cancelar</button><button className="button" disabled={busy} onClick={save}>{busy ? 'Salvando…' : 'Confirmar e salvar nota'}</button></div></Modal>}
    {selected !== null && <ReceiptModal id={selected} categories={categories} close={() => setSelected(null)} changed={changed} revision={revision} notify={notify}/>}
  </>
}

function ItemTable({items, categories, onCategory, disabled = false}: {items: ReceiptItem[]; categories?: string[]; onCategory?: (id: number, category: string) => void; disabled?: boolean}) {
  return <div className="table-scroll"><table className="items-table"><thead><tr><th>Produto</th><th>Qtd.</th>{categories && <th>Categoria</th>}<th className="number">Total</th></tr></thead><tbody>{items.map((item, i) => <tr key={item.id || i}><td>{item.description}</td><td className="nowrap small">{Number(item.quantity).toLocaleString('pt-BR', {maximumFractionDigits: 6})} {item.unit}</td>{categories && <td><select className="inline-select" disabled={disabled} aria-label={`Categoria de ${item.description}`} value={item.category} onChange={e => item.id && onCategory?.(item.id, e.target.value)}>{categories.map(c => <option key={c}>{c}</option>)}</select></td>}<td className="number amount">{money(item.total_cents)}</td></tr>)}</tbody></table></div>
}

function ReceiptModal({id, categories, close, changed, revision, notify}: {id: number; categories: string[]; close: () => void; changed: () => void; revision: number; notify: (text: string) => void}) {
  const state = useLoad<ReceiptDetail>(`/receipts/${id}`, revision)
  const [candidate, setCandidate] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function act(path: string, method: string, body?: object, success?: string) {
    setBusy(true); setError('')
    try {await api(path, {method, body: body ? JSON.stringify(body) : undefined}); changed(); if(success) notify(success)} catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  const receipt = state.data
  return <Modal wide title="Detalhes da nota" subtitle="Produtos e vínculo com o extrato" close={() => !busy && close()}><div className="form-body"><ErrorBox message={state.error || error}/>{!receipt ? <Loading/> : <>
    <div className="receipt-summary"><div><h3>{receipt.merchant}</h3><p>{day(receipt.date)} · {receipt.items.length} itens</p></div><strong>{money(receipt.total_cents)}</strong></div>
    <ItemTable items={receipt.items} categories={categories} disabled={busy || state.loading} onCategory={(itemId, category) => act(`/receipt-items/${itemId}`, 'PATCH', {category})}/>
    {receipt.difference_cents !== 0 && <div className="warning">Diferença entre total da nota e itens: {money(receipt.difference_cents)}. O vínculo fica bloqueado nesta versão.</div>}
    <section className="link-section"><h3><Link size={17}/> Compra no extrato</h3>{receipt.transaction_id ? <div className="linked-note"><div><Check size={18}/><div><strong>Vinculada ao lançamento #{receipt.transaction_id}</strong><p>A despesa continua contando uma única vez.</p></div></div><button className="text-button" disabled={busy} onClick={() => act(`/receipts/${id}/link`, 'DELETE', undefined, 'Nota desvinculada. O lançamento foi mantido.')}>Desvincular</button></div> : <>
      <p className="help-text">Candidatos com o mesmo valor, em até 3 dias. Confira o estabelecimento antes de confirmar.</p>
      {receipt.candidates.length ? <div className="candidates">{receipt.candidates.map(c => <label key={c.id} className={`candidate ${candidate === c.id ? 'selected' : ''}`}><input type="radio" name="candidate" checked={candidate === c.id} onChange={() => setCandidate(c.id)}/><span><strong>{c.description}</strong><small>{day(c.date)} · {c.bank}</small></span><b>{money(-c.amount_cents)}</b></label>)}</div> : <div className="quiet-empty">Nenhuma compra compatível. Importe o OFX do período e confira a classificação do lançamento.</div>}
      {receipt.candidates.length > 0 && <button className="button" disabled={busy || state.loading || !candidate || receipt.difference_cents !== 0} onClick={() => act(`/receipts/${id}/link`, 'POST', {transaction_id: candidate}, 'Nota vinculada. O total das despesas permaneceu igual.')}><Link size={15}/>{busy ? 'Salvando…' : 'Confirmar vínculo'}</button>}
    </>}</section>
    <p className="help-text">As categorias dos produtos detalham a nota. O resumo mensal usa a categoria do lançamento.</p>
  </>}</div><div className="modal-actions"><button className="button secondary" disabled={busy} onClick={close}>Fechar</button></div></Modal>
}
