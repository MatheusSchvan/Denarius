import { useState, type FormEvent } from 'react'
import { api, day, money, today, useLoad } from '../api'
import { Empty, ErrorBox, Loading } from '../components'
import type { PageProps, Transaction } from '../types'

type Snapshot = {id: number; as_of: string; amount_cents: number; source: string; balance_type: string; label: string}
type Account = {account_key: string; bank: string; origin: string; label: string; ledger: Snapshot | null; available: Snapshot | null}
type BalancesData = {accounts: Account[]; total_ledger_cents: number; account_count_with_ledger: number; history: Snapshot[]}

export function Balances({revision, changed, notify}: PageProps) {
  const state = useLoad<BalancesData>('/manage/balances', revision)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError('')
    const values = new FormData(event.currentTarget)
    try {
      const text = String(values.get('value')).trim()
      if (!/^-?\d+(,\d{1,2})?$/.test(text)) throw new Error('Use vírgula para centavos e não use separador de milhares. Ex.: -120,50 ou 0,00.')
      const [whole, fraction = ''] = text.replace('-', '').split(',')
      const amount = (Number(whole) * 100 + Number(fraction.padEnd(2, '0'))) * (text.startsWith('-') ? -1 : 1)
      await api('/manage/balances', {method: 'POST', body: JSON.stringify({account_key: values.get('account'), date: values.get('date'), balance_type: values.get('type'), amount_cents: amount})})
      changed(); notify('Saldo informado salvo no histórico. Nenhum lançamento foi criado.')
    } catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  if (!state.data) return state.error ? <ErrorBox message={state.error}/> : <Loading/>
  const data = state.data
  return <>
    <ErrorBox message={state.error || error}/>
    <section className="panel form-body"><h2>Saldo contábil das contas</h2><h1>{data.account_count_with_ledger ? money(data.total_ledger_cents) : 'Não informado'}</h1><p className="help-text">Soma do último saldo contábil de cada conta, que pode ter datas diferentes. Cartões ficam fora. Não representa consulta ao banco em tempo real.</p></section>
    <section className="panel"><div className="panel-heading"><h2>Contas e cartões</h2></div>{data.accounts.length ? <div className="table-scroll"><table><thead><tr><th>Conta</th><th>Saldo contábil</th><th>Saldo disponível</th></tr></thead><tbody>{data.accounts.map(a => <tr key={a.account_key}><td>{a.label}{a.origin === 'Cartão' && <div className="help-text">Saldo do extrato do cartão; não é limite disponível.</div>}</td>{(['ledger', 'available'] as const).map(type => <td key={type}>{a[type] ? <><strong>{money(a[type]!.amount_cents)}</strong><div className="help-text">{day(a[type]!.as_of)} · {a[type]!.source}</div></> : 'Não informado no OFX'}</td>)}</tr>)}</tbody></table></div> : <Empty title="Importe um OFX para cadastrar a conta">O saldo só aparece se estiver no arquivo ou se você o informar depois.</Empty>}</section>
    {data.accounts.length > 0 && <section className="panel"><div className="panel-heading"><h2>Informar saldo manualmente</h2></div><form className="form-body" onSubmit={submit}><div className="form-grid"><label>Conta<select aria-label="Conta do saldo" name="account">{data.accounts.map(a => <option key={a.account_key} value={a.account_key}>{a.label}</option>)}</select></label><label>Data de referência<input type="date" name="date" defaultValue={today()} required/></label></div><div className="form-grid"><label>Tipo de saldo<select name="type" aria-label="Tipo de saldo"><option value="ledger">Contábil</option><option value="available">Disponível</option></select></label><label>Valor em reais<input name="value" required placeholder="Ex.: 1250,00" inputMode="decimal"/></label></div><button className="button" disabled={busy}>{busy ? 'Salvando…' : 'Salvar saldo'}</button></form></section>}
    <section className="panel"><div className="panel-heading"><h2>Histórico de saldos</h2></div><div className="table-scroll"><table><thead><tr><th>Referência</th><th>Conta</th><th>Tipo</th><th>Origem</th><th className="number">Saldo</th></tr></thead><tbody>{data.history.map(s => <tr key={s.id}><td>{day(s.as_of)}</td><td>{s.label}</td><td>{s.balance_type === 'ledger' ? 'Contábil' : 'Disponível'}</td><td>{s.source}</td><td className="number">{money(s.amount_cents)}</td></tr>)}</tbody></table></div></section>
    <p className="footnote">Um extrato sem saldo não substitui o saldo anterior por zero. Na atualização da parte 1 para a 2, reimporte o OFX: os saldos serão lidos sem duplicar lançamentos.</p>
  </>
}

export function Settings({revision, changed, notify}: PageProps) {
  const trash = useLoad<Transaction[]>('/manage/trash', revision)
  const [scope, setScope] = useState('transactions')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function restore(id: number) {
    setBusy(true); setError('')
    try {await api(`/manage/trash/${id}/restore`, {method: 'POST', body: '{}'}); changed(); notify('Lançamento restaurado.')} catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  async function clear(event: FormEvent) {
    event.preventDefault()
    if (!window.confirm('Confirmar a limpeza selecionada? Um backup será salvo em data/backups antes de remover os dados. A recuperação será feita por esse backup.')) return
    setBusy(true); setError('')
    try {
      const result = await api<{backup: string}>('/manage/clear', {method: 'POST', body: JSON.stringify({scope, confirmation})})
      setConfirmation(''); changed(); notify(`Limpeza concluída. Backup recuperável na pasta de dados/backups: ${result.backup}`)
    } catch (e) {setError((e as Error).message)} finally {setBusy(false)}
  }
  return <><ErrorBox message={error || trash.error}/>
    <section className="panel form-body"><h2>Backup</h2><p className="help-text">Guarde uma cópia antes de trocar de versão ou fazer testes. O backup inclui lançamentos, notas e saldos.</p><a className="button secondary" href="/api/backup" download>Baixar backup completo</a><p className="footnote">Para restaurar: feche o aplicativo, guarde o banco atual e copie o backup para data/financeiro.sqlite3. A restauração por tela ainda não está implementada.</p></section>
    <section className="panel"><div className="panel-heading"><h2>Lixeira de lançamentos</h2><span className="muted">{trash.data?.length || 0} registros</span></div>{trash.loading ? <Loading/> : trash.data?.length ? <div className="table-scroll"><table><thead><tr><th>Data</th><th>Descrição</th><th className="number">Valor</th><th>Ação</th></tr></thead><tbody>{trash.data.map(row => <tr key={row.id}><td>{day(row.date)}</td><td>{row.description}</td><td className="number">{money(row.amount_cents)}</td><td><button disabled={busy} className="text-button" onClick={() => restore(row.id)}>Restaurar</button></td></tr>)}</tbody></table></div> : <Empty title="Lixeira vazia">Ao excluir um lançamento individual, ele poderá ser restaurado aqui.</Empty>}<p className="form-body help-text">Reimportar um OFX não restaura automaticamente registros da lixeira. Use Restaurar ou faça a limpeza de todos para começar novamente.</p></section>
    <section className="panel"><div className="panel-heading"><h2>Limpar dados</h2></div><form onSubmit={clear} className="form-body"><label>O que apagar<select aria-label="O que apagar" value={scope} onChange={e => setScope(e.target.value)}><option value="transactions">Todos os lançamentos e histórico de importações</option><option value="everything">Toda a base: lançamentos, notas, contas e saldos</option></select></label><div className="warning">{scope === 'transactions' ? 'Remove também a lixeira. As notas e os saldos são preservados; os vínculos das notas são removidos. Depois, você pode reimportar os mesmos OFX.' : 'Remove todos os dados do aplicativo, incluindo notas e saldos. As preferências visuais do navegador não são apagadas.'} Um backup local será criado antes. Se ele falhar, a limpeza não acontece.</div><label>Digite APAGAR<input aria-label="Confirmar limpeza" value={confirmation} onChange={e => setConfirmation(e.target.value)} autoComplete="off"/></label><button className="button danger" disabled={busy || confirmation !== 'APAGAR'}>{busy ? 'Processando…' : 'Apagar dados selecionados'}</button></form></section>
  </>
}
