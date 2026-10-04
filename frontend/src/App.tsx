import { useEffect, useRef, useState } from 'react'
import { ArrowDownToLine, ArrowUpRight, Check, ChevronDown, Circle, LayoutDashboard, List, ReceiptText, Upload, X } from 'lucide-react'
import { api, monthLabel, today, useLoad } from './api'
import { ErrorBox, Loading } from './components'
import type {Bootstrap, Page, PageProps} from './types'
import Overview from './pages/Overview'
import Transactions from './pages/Transactions'
import Imports from './pages/Imports'
import Receipts from './pages/Receipts'
import { Balances, Settings } from './pages/Management'
import { Wallet, Settings as SettingsIcon, ChartColumn } from 'lucide-react'
import Reports from './pages/Reports'
import { useTheme, type Theme } from './theme'

const pages = [
  {id: 'overview' as Page, label: 'Visão geral', icon: LayoutDashboard, description: 'Um resumo do que entrou e do que saiu.'},
  {id: 'balances' as Page, label: 'Saldos', icon: Wallet, description: 'Saldos reportados, com a data de referência de cada conta.'},
  {id: 'transactions' as Page, label: 'Lançamentos', icon: List, description: 'Confira os movimentos e ajuste as categorias.'},
  {id: 'imports' as Page, label: 'Importações', icon: Upload, description: 'Traga os extratos da sua conta e do seu cartão.'},
  {id: 'receipts' as Page, label: 'Notas de compra', icon: ReceiptText, description: 'Veja os produtos por trás de cada compra.'},
  {id: 'settings' as Page, label: 'Configurações', icon: SettingsIcon, description: 'Lixeira, backup e limpeza dos dados.'},
  {id: 'reports' as Page, label: 'Relatórios', icon: ChartColumn, description: 'Consulte e exporte o resumo dos seus gastos.'},
]

export default function App() {
  const {theme, setTheme} = useTheme()
  const [page, setPage] = useState<Page>('overview')
  const [month, setMonth] = useState(today().slice(0, 7))
  const [revision, setRevision] = useState(0)
  const [message, setMessage] = useState('')
  const [demoBusy, setDemoBusy] = useState(false)
  const [demoError, setDemoError] = useState('')
  const initialized = useRef(false)
  const bootstrap = useLoad<Bootstrap>('/bootstrap', revision)
  useEffect(() => {
    if (bootstrap.data && !initialized.current) {
      if (bootstrap.data.months.length) setMonth(bootstrap.data.months[0])
      initialized.current = true
    }
  }, [bootstrap.data])
  const changed = () => setRevision(r => r + 1)
  const navigate = (id: Page) => {setPage(id); setMessage('')}
  const current = pages.find(p => p.id === page)!
  async function loadDemo() {
    setDemoBusy(true); setDemoError('')
    try {
      const data = await api<{month: string}>('/demo', {method: 'POST', body: '{}'})
      setMonth(data.month); changed(); setMessage('Exemplos carregados. Todos os dados são fictícios.')
    } catch (e) {setDemoError((e as Error).message)} finally {setDemoBusy(false)}
  }
  const props: PageProps = {month, revision, categories: bootstrap.data?.categories || [], banks: bootstrap.data?.banks || [], changed, notify: setMessage, navigate}
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => {e.preventDefault(); navigate('overview')}}><span className="brand-mark">f.</span><span>financeiro<span className="brand-sub">PESSOAL</span></span></a>
      <div className="nav-caption">MEU CONTROLE</div>
      <nav aria-label="Navegação principal">{pages.map(({id, label, icon: Icon}) => <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} aria-current={page === id ? 'page' : undefined} onClick={() => navigate(id)}><Icon size={18}/>{label}</button>)}</nav>
      <div className="sidebar-bottom"><a className="backup-link" href="/api/backup" download><ArrowDownToLine size={17}/> Fazer backup <ArrowUpRight size={14}/></a><div className="local-label"><Circle size={7} fill="currentColor"/> Salvo neste computador</div><span className="version">Projeto acadêmico · v0.3</span></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><span>Controle financeiro pessoal</span><label className="theme-picker">Tema<select aria-label="Tema" value={theme} onChange={e => setTheme(e.target.value as Theme)}><option value="light">Claro</option><option value="dark">Escuro</option><option value="system">Sistema</option></select></label></header>
      <main>
        <div className="page-heading"><div><div className="eyebrow">{page === 'overview' ? 'ACOMPANHAMENTO' : 'ORGANIZAÇÃO'}</div><h1>{current.label}</h1><p>{current.description}</p></div>
          {(page === 'overview' || page === 'transactions' || page === 'reports') && <label className="month-picker"><span className="sr-only">Mês de referência</span><select value={month} onChange={e => setMonth(e.target.value)}>{Array.from(new Set([today().slice(0, 7), month, ...(bootstrap.data?.months || [])])).sort().reverse().map(m => <option value={m} key={m}>{monthLabel(m)}</option>)}</select><ChevronDown size={15}/></label>}
        </div>
        {message && <div className="notice" role="status"><Check size={17}/><span>{message}</span><button onClick={() => setMessage('')} className="icon-button" aria-label="Fechar aviso"><X size={16}/></button></div>}
        <ErrorBox message={bootstrap.error || demoError}/>
        {!bootstrap.data ? (bootstrap.error ? <button className="button secondary" onClick={changed}>Tentar novamente</button> : <Loading/>) : <>
          {bootstrap.data.transaction_count === 0 && page === 'overview' && <div className="welcome"><div><h2>Comece com um extrato.</h2><p>Importe um OFX ou use os exemplos para conhecer o projeto.</p></div><button className="button secondary" disabled={demoBusy} onClick={loadDemo}>{demoBusy ? 'Carregando…' : 'Usar dados de exemplo'}</button><button className="button" onClick={() => navigate('imports')}>Importar OFX <ArrowUpRight size={16}/></button></div>}
          {page === 'overview' && <Overview {...props}/>}
          {page === 'transactions' && <Transactions {...props}/>}
          {page === 'imports' && <Imports {...props}/>}
          {page === 'receipts' && <Receipts {...props}/>}
          {page === 'balances' && <Balances {...props}/>}
          {page === 'settings' && <Settings {...props}/>}
          {page === 'reports' && <Reports {...props}/>}
        </>}
        <footer className="page-footer"><span>Financeiro pessoal</span><span>Valores em reais · Seus arquivos ficam no computador</span></footer>
      </main>
    </div>
  </div>
}
