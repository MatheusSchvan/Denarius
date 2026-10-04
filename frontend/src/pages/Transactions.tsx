import { useEffect, useState, type FormEvent } from 'react'
import { Download, Plus, Search, Pencil, ReceiptText } from 'lucide-react'
import { api, day, money, parseMoney, today, useLoad } from '../api'
import { Empty, ErrorBox, Loading, Modal, kindLabels } from '../components'
import type { Kind, PageProps, Transaction } from '../types'

export default function Transactions(props: PageProps) {
  const {month, revision, categories, banks, changed, notify} = props
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [bank, setBank] = useState('')
  const [pending, setPending] = useState(false)
  const [editing, setEditing] = useState<Transaction | 'new' | null>(null)
  const [page, setPage] = useState(1)
  useEffect(() => {const timer = setTimeout(() => setQuery(search), 250); return () => clearTimeout(timer)}, [search])
  useEffect(() => setPage(1), [month, query, category, bank, pending])
  const params = new URLSearchParams({month, search: query, category, bank, pending: String(pending)})
  const state = useLoad<Transaction[]>(`/transactions?${params}`, revision)
  const rows = state.data || []
  const pageCount = Math.max(1, Math.ceil(rows.length / 20))
  const activePage = Math.min(page, pageCount)
  return <>
    <div className="toolbar"><div className="toolbar-left"><span className="record-count">{rows.length} lançamentos</span>{pending && <span className="badge amber">Para revisar</span>}</div><div className="toolbar-actions"><a className="button secondary" href="/api/export.csv" download title="Exportar todos os lançamentos, de todos os meses"><Download size={16}/> Exportar tudo</a><button className="button" onClick={() => setEditing('new')}><Plus size={17}/> Novo lançamento</button></div></div>
    <section className="panel">
      <div className="filters"><label className="search-field"><Search size={17}/><input aria-label="Buscar lançamento" value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar na descrição ou observação"/></label><select aria-label="Filtrar categoria" value={category} onChange={e => setCategory(e.target.value)}><option value="">Todas as categorias</option>{categories.map(c => <option key={c}>{c}</option>)}</select><select aria-label="Filtrar banco" value={bank} onChange={e => setBank(e.target.value)}><option value="">Todos os bancos</option>{banks.map(b => <option key={b}>{b}</option>)}</select><label className="checkbox"><input type="checkbox" checked={pending} onChange={e => setPending(e.target.checked)}/> Só pendentes</label></div>
      <ErrorBox message={state.error}/>
      {state.loading ? <Loading/> : rows.length ? <><div className="table-scroll"><table className="transactions-table"><thead><tr><th>Data</th><th>Descrição / banco</th><th>Categoria</th><th>Tipo</th><th className="number">Valor</th><th><span className="sr-only">Ações</span></th></tr></thead><tbody>{rows.slice((activePage - 1) * 20, activePage * 20).map(t => <tr key={t.id} className={t.pending_duplicate ? 'pending-row' : ''}><td className="muted nowrap">{day(t.date)}</td><td><div className="description-cell"><span>{t.description}</span>{t.receipt_id && <ReceiptText size={15} aria-label="Nota vinculada"/>}</div><div className="row-secondary">{t.bank} · {t.origin}{t.pending_duplicate === 1 && <span className="badge amber">Possível duplicata</span>}</div></td><td><span className={`badge ${t.category === 'Não classificado' ? 'neutral' : ''}`}>{t.category}</span></td><td className="small muted">{kindLabels[t.kind]}</td><td className={`number amount ${t.amount_cents > 0 ? 'positive' : ''}`}>{money(t.amount_cents)}</td><td><button className="icon-button" aria-label={`Editar ${t.description}`} onClick={() => setEditing(t)}><Pencil size={16}/></button></td></tr>)}</tbody></table></div><div className="pagination"><span>Mostrando {(activePage - 1) * 20 + 1}–{Math.min(activePage * 20, rows.length)} de {rows.length}</span><div><button className="button secondary small-button" disabled={activePage === 1} onClick={() => setPage(activePage - 1)}>Anterior</button><span>{activePage} / {pageCount}</span><button className="button secondary small-button" disabled={activePage === pageCount} onClick={() => setPage(activePage + 1)}>Próxima</button></div></div></> : !state.error && <Empty title="Nenhum lançamento encontrado">Ajuste os filtros, importe um extrato ou adicione um lançamento.</Empty>}
    </section>
    <p className="footnote">Possíveis duplicatas ficam fora do resumo até você confirmar. Classifique pagamentos de fatura como transferência quando as compras do cartão também estiverem importadas.</p>
    {editing && <TransactionForm transaction={editing === 'new' ? null : editing} categories={categories} close={() => setEditing(null)} done={text => {setEditing(null); changed(); notify(text)}}/>}
  </>
}

function TransactionForm({transaction, categories, close, done}: {transaction: Transaction | null; categories: string[]; close: () => void; done: (text: string) => void}) {
  const [kind, setKind] = useState<Kind>(transaction?.kind || 'expense')
  const [category, setCategory] = useState(transaction?.category || 'Não classificado')
  const [notes, setNotes] = useState(transaction?.notes || '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError(''); setBusy(true)
    const form = new FormData(e.currentTarget)
    try {
      if (transaction) {
        await api(`/transactions/${transaction.id}`, {method: 'PATCH', body: JSON.stringify({category, kind, notes, pending_duplicate: false})})
        done(transaction.pending_duplicate ? 'Lançamento confirmado e incluído no resumo.' : 'Classificação salva.')
      } else {
        let value = parseMoney(String(form.get('amount')))
        if (kind === 'expense' || (kind !== 'income' && form.get('direction') !== 'in')) value = -value
        await api('/transactions', {method: 'POST', body: JSON.stringify({date: form.get('date'), bank: form.get('bank'), description: form.get('description'), amount_cents: value, kind, category, notes})})
        done('Lançamento adicionado. Se a data for de outro mês, selecione o período correspondente.')
      }
    } catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  async function discard() {
    if (!window.confirm('Mover este lançamento para a lixeira? Ele sai do resumo e pode ser restaurado em Configurações. Notas vinculadas precisam ser desvinculadas antes.')) return
    setBusy(true); setError('')
    try {await api(`/transactions/${transaction!.id}`, {method: 'DELETE'}); done('Lançamento movido para a lixeira. Você pode restaurá-lo em Configurações.')} catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  return <Modal title={transaction ? 'Conferir lançamento' : 'Novo lançamento'} subtitle={transaction ? 'Ajuste a classificação e a observação.' : 'Registre uma entrada ou saída que não está no extrato.'} close={() => !busy && close()}>
    <form onSubmit={submit}><div className="form-body"><ErrorBox message={error}/>
      {transaction ? <div className="transaction-summary"><strong>{transaction.description}</strong><span>{day(transaction.date)} · {transaction.bank} · {transaction.origin}</span><b>{money(transaction.amount_cents)}</b>{transaction.pending_duplicate === 1 && <div className="warning">Sem identificador bancário e semelhante a outro registro. Se for uma compra diferente, confirme; se for a mesma, descarte a cópia.</div>}</div> : <>
        <label>Descrição<input name="description" required maxLength={500} placeholder="Ex.: almoço, venda de um livro…" autoFocus/></label>
        <div className="form-grid"><label>Data<input type="date" name="date" required defaultValue={today()}/></label><label>Valor (R$)<input name="amount" inputMode="decimal" placeholder="0,00" required pattern="[0-9.,]+"/></label></div>
        <label>Banco ou carteira<input name="bank" required maxLength={100} defaultValue="Carteira"/></label>
      </>}
      <div className="form-grid"><label>Tipo<select aria-label="Tipo" value={kind} onChange={e => setKind(e.target.value as Kind)}>{Object.entries(kindLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label><label>Categoria<select aria-label="Categoria" value={category} onChange={e => setCategory(e.target.value)}>{categories.map(c => <option key={c}>{c}</option>)}</select></label></div>
      {!transaction && !['expense', 'income'].includes(kind) && <label>Direção do movimento<select name="direction"><option value="out">Saída de dinheiro</option><option value="in">Entrada de dinheiro</option></select></label>}
      {!['expense', 'income'].includes(kind) && <p className="help-text">Esse movimento fica registrado, mas não entra nas receitas e despesas do resumo.</p>}
      <label>Observação <span className="optional">opcional</span><textarea value={notes} maxLength={2000} onChange={e => setNotes(e.target.value)} rows={3} placeholder="Algo que você queira lembrar sobre este lançamento"/></label>
    </div><div className="modal-actions">{transaction && <button type="button" className="button danger" disabled={busy} onClick={discard}>Excluir lançamento</button>}<button type="button" className="button secondary" disabled={busy} onClick={close}>Cancelar</button><button className="button" disabled={busy}>{busy ? 'Salvando…' : transaction?.pending_duplicate ? 'Confirmar lançamento' : 'Salvar'}</button></div></form>
  </Modal>
}
