import { ArrowDownLeft, ArrowRight, ArrowUpRight, CircleAlert, ReceiptText, Wallet } from 'lucide-react'
import { day, money, useLoad } from '../api'
import { Empty, ErrorBox, Loading } from '../components'
import type { PageProps, Summary, Transaction } from '../types'

const colors = ['#476f5c', '#77947d', '#a9b6a0', '#c0ae90', '#7d8f9a', '#b4bbc0']

export default function Overview({month, revision, navigate}: PageProps) {
  const state = useLoad<Summary>(`/summary?month=${month}`, revision)
  const latest = useLoad<Transaction[]>(`/transactions?month=${month}`, revision)
  if (state.error) return <ErrorBox message={state.error}/>
  if (!state.data || state.loading) return <Loading/>
  const data = state.data
  const maxCategory = Math.max(1, ...data.categories.map(c => c.amount_cents))
  const maxTrend = Math.max(1, ...data.trend.flatMap(t => [t.income, t.expense]))
  return <>
    <section className="stats" aria-label="Resumo do mês">
      <div className="stat"><div className="stat-label">Entradas <span className="stat-icon green"><ArrowDownLeft size={17}/></span></div><strong>{money(data.income_cents)}</strong><span className="stat-note">Recebimentos do mês</span></div>
      <div className="stat"><div className="stat-label">Despesas <span className="stat-icon clay"><ArrowUpRight size={17}/></span></div><strong>{money(data.expense_cents)}</strong><span className="stat-note">Gastos confirmados</span></div>
      <div className="stat result"><div className="stat-label">Resultado do mês <span className="stat-icon"><Wallet size={17}/></span></div><strong>{money(data.result_cents)}</strong><span className="stat-note">Entradas menos despesas</span></div>
    </section>
    <div className="metrics-note">{data.count} lançamentos no período · Transferências, investimentos e ajustes ficam fora do resultado.</div>
    <div className="overview-grid">
      <section className="panel category-panel"><div className="panel-heading"><div><h2>Para onde foi o dinheiro</h2><p>Despesas por categoria</p></div><span className="small muted">Neste mês</span></div>
        {data.categories.length === 0 ? <Empty title="Nenhuma despesa por aqui">Os gastos do período vão aparecer nesta área.</Empty> : <div className="category-chart">{data.categories.map((c, i) => <div className="category-row" key={c.category}><div className="category-name"><span className="color-dot" style={{background: colors[i % colors.length]}}/>{c.category}<strong>{money(c.amount_cents)}</strong></div><div className="bar-track"><div style={{width: `${c.amount_cents / maxCategory * 100}%`, background: colors[i % colors.length]}}/></div></div>)}</div>}
      </section>
      <div className="overview-right"><section className="panel review-panel"><div className="panel-heading"><div><h2>Para conferir</h2><p>Pequenos ajustes no seu controle</p></div><CircleAlert size={19} className="muted"/></div>
        <button className="review-row" onClick={() => navigate('transactions')}><span><span className="count-box">{data.unclassified}</span>Sem categoria</span><ArrowRight size={17}/></button>
        <button className="review-row" onClick={() => navigate('transactions')}><span><span className="count-box">{data.pending_duplicates}</span>Possíveis duplicatas</span><ArrowRight size={17}/></button>
        <button className="review-row" onClick={() => navigate('receipts')}><span><span className="count-box">{data.unlinked_receipts}</span>Notas sem vínculo <small>total</small></span><ArrowRight size={17}/></button>
      </section>
      <section className="panel trend-panel"><div className="panel-heading"><div><h2>Entradas e despesas</h2><p>Até 6 meses com movimentação</p></div></div>
        {!data.trend.length ? <p className="muted small">Importe um extrato para ver a comparação.</p> : <><div className="trend-chart" role="img" aria-label="Comparação mensal de entradas e despesas">{data.trend.map(t => <div className="trend-column" key={t.month}><div className="trend-bars"><div title={`Entradas: ${money(t.income)}`} style={{height: `${t.income / maxTrend * 100}%`}}/><div title={`Despesas: ${money(t.expense)}`} style={{height: `${t.expense / maxTrend * 100}%`}}/></div><span>{t.month.slice(5)}/{t.month.slice(2,4)}</span><span className="sr-only">Entradas {money(t.income)}; despesas {money(t.expense)}</span></div>)}</div><div className="chart-key"><span><i/> Entradas</span><span><i/> Despesas</span></div></>}
      </section></div>
    </div>
    <section className="panel recent-panel"><div className="panel-heading"><div><h2>Últimos lançamentos</h2><p>Movimentos do período selecionado</p></div><button className="text-button" onClick={() => navigate('transactions')}>Ver todos <ArrowRight size={15}/></button></div>
      <ErrorBox message={latest.error}/>
      {latest.data?.length ? <div className="table-scroll"><table><thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Banco</th><th className="number">Valor</th></tr></thead><tbody>{latest.data.slice(0, 5).map(t => <tr key={t.id}><td className="muted nowrap">{day(t.date)}</td><td className="description-cell">{t.description}{t.receipt_id && <ReceiptText size={14} aria-label="Possui nota vinculada"/>}{t.pending_duplicate === 1 && <span className="badge amber">Revisar</span>}</td><td><span className={`badge ${t.category === 'Não classificado' ? 'neutral' : ''}`}>{t.category}</span></td><td className="muted small">{t.bank}</td><td className={`number amount ${t.amount_cents > 0 ? 'positive' : ''}`}>{money(t.amount_cents)}</td></tr>)}</tbody></table></div> : <Empty title="Nenhum lançamento neste mês">Selecione outro mês ou importe um extrato.</Empty>}
    </section>
    <div className="footnote">O resultado considera apenas os lançamentos importados e manuais. Ele não representa o saldo disponível no banco.</div>
  </>
}
