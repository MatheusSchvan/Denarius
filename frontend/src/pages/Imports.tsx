import { useRef, useState } from 'react'
import { Check, FileText, Upload, X, ArrowRight } from 'lucide-react'
import { day, money, upload, useLoad } from '../api'
import { Empty, ErrorBox, Loading } from '../components'
import type { ImportLog, ImportPreview, ImportResult, PageProps } from '../types'

type Selection = {file: File; preview?: ImportPreview; result?: ImportResult; error?: string}

export default function Imports({revision, changed, notify, navigate}: PageProps) {
  const state = useLoad<ImportLog[]>('/imports', revision)
  const [selection, setSelection] = useState<Selection[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  async function choose(files: FileList | File[]) {
    if (busy) return
    setError('')
    if (files.length > 10) {setError('Selecione no máximo 10 arquivos por vez.'); return}
    setBusy(true)
    const previews: Selection[] = []
    for (const file of Array.from(files)) {
      try {
        if (file.size > 5 * 1024 * 1024) throw new Error('O limite é de 5 MB por arquivo.')
        const preview = await upload<ImportPreview>('/imports/preview', file)
        previews.push({file, preview})
      } catch (e) {previews.push({file, error: (e as Error).message})}
    }
    setSelection(previews); setBusy(false)
    if (input.current) input.current.value = ''
  }
  async function confirm() {
    setBusy(true)
    const updated = [...selection]
    for (let i = 0; i < updated.length; i++) {
      const item = updated[i]
      if (!item.preview || item.result) continue
      try {updated[i] = {...item, error: undefined, result: await upload<ImportResult>('/imports', item.file)}} catch (e) {updated[i] = {...item, error: (e as Error).message}}
      setSelection([...updated])
    }
    changed(); setBusy(false)
    const completed = updated.filter(x => x.result)
    if (completed.length) notify(`${completed.length} arquivo(s) processado(s). Confira o resultado da importação abaixo.`)
  }
  const ready = selection.some(s => s.preview && !s.result)
  return <>
    <section className="panel upload-panel"><div className="upload-layout"><div className="upload-icon"><Upload size={25}/></div><div><h2>Importar extratos OFX</h2><p>Exporte o arquivo no aplicativo do banco e selecione aqui.</p><span className="help-text">Conta e cartão · Até 10 arquivos de 5 MB · Formatos OFX 1.x e 2.x</span></div><input ref={input} type="file" multiple accept=".ofx" className="sr-only" aria-label="Arquivos OFX" onChange={e => e.target.files && choose(e.target.files)}/><button className="button" disabled={busy} onClick={() => input.current?.click()}><Upload size={16}/>{busy ? 'Processando…' : 'Selecionar arquivos'}</button></div></section>
    <div className="import-tip"><Check size={16}/><span>Você revisa a prévia antes de gravar. Reimportar o mesmo arquivo mantém os lançamentos existentes.</span></div>
    <ErrorBox message={error}/>
    {selection.length > 0 && <section className="panel preview-panel"><div className="panel-heading"><div><h2>Conferir importação</h2><p>Os números são recalculados ao confirmar cada arquivo.</p></div><button className="icon-button" disabled={busy} onClick={() => setSelection([])} aria-label="Limpar seleção"><X size={19}/></button></div>
      {selection.map((item, index) => <div className="file-preview" key={index}><div className="file-title"><FileText size={19}/><strong>{item.file.name}</strong>{item.result && <span className="badge">Concluído</span>}</div><ErrorBox message={item.error || ''}/>{(item.result || item.preview) && <><div className="import-counts"><span><strong>{(item.result || item.preview)!.new}</strong> novos</span><span><strong>{(item.result || item.preview)!.duplicates}</strong> já existentes</span><span><strong>{(item.result || item.preview)!.pending}</strong> para revisar</span><span className="muted">{(item.result || item.preview)!.bank}</span></div>{!item.result && item.preview && <details><summary>Ver prévia dos lançamentos (até 100)</summary><div className="table-scroll"><table><thead><tr><th>Data</th><th>Descrição</th><th className="number">Valor</th><th>Situação</th></tr></thead><tbody>{item.preview.rows.map((r, i) => <tr key={i}><td className="nowrap">{day(r.date)}</td><td>{r.description}</td><td className="number">{money(r.amount_cents)}</td><td className="small">{{new: 'Novo', duplicate: 'Já existe', review: 'Revisar'}[r.action]}</td></tr>)}</tbody></table></div></details>}</>}</div>)}
      <div className="panel-actions">{ready ? <button className="button" disabled={busy} onClick={confirm}>{busy ? 'Importando…' : 'Confirmar importação'}</button> : <button className="button secondary" onClick={() => navigate('transactions')}>Ver lançamentos <ArrowRight size={16}/></button>}</div>
    </section>}
    <section className="panel"><div className="panel-heading"><div><h2>Histórico de importações</h2><p>Últimos 100 arquivos processados</p></div></div><ErrorBox message={state.error}/>{state.loading ? <Loading/> : state.data?.length ? <div className="table-scroll"><table><thead><tr><th>Arquivo</th><th>Importado em</th><th className="number">Novos</th><th className="number">Existentes</th><th className="number">Revisar</th></tr></thead><tbody>{state.data.map(log => <tr key={log.id}><td><span className="file-title compact"><FileText size={16}/>{log.filename}</span><div className="row-secondary">{log.bank}</div></td><td className="small muted nowrap">{new Date(log.created_at).toLocaleString('pt-BR')}</td><td className="number">{log.added}</td><td className="number muted">{log.duplicates}</td><td className="number">{log.pending > 0 ? <span className="badge amber">{log.pending}</span> : '—'}</td></tr>)}</tbody></table></div> : !state.error && <Empty title="Nenhum extrato importado">Selecione seu primeiro OFX para começar.</Empty>}</section>
    <p className="footnote">O aplicativo lê os arquivos que você escolhe. Não há conexão direta com sua conta bancária.</p>
  </>
}
