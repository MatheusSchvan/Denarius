import { useRef, useState } from 'react'
import { Download, Printer } from 'lucide-react'
import { money, monthLabel, useLoad } from '../api'
import { ErrorBox, Loading } from '../components'
import type { PageProps, Summary } from '../types'

const green = '#315e4d', clay = '#ad705b', ink = '#26322c', muted = '#647269'

// Cores e dimensões explícitas: a imagem exportada não depende do tema ou do CSS.
export function ReportGraphic({data, month, svgRef}: {data: Summary; month: string; svgRef?: React.Ref<SVGSVGElement>}) {
  const categoryHeight = Math.max(95, data.categories.length * 42)
  const trendTop = 350 + categoryHeight
  const height = trendTop + 400
  const maxCategory = Math.max(1, ...data.categories.map(c => c.amount_cents))
  const maxTrend = Math.max(1, ...data.trend.flatMap(t => [t.income, t.expense]))
  const cellWidth = 880 / Math.max(1, data.trend.length)
  return <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" width="1000" height={height} viewBox={`0 0 1000 ${height}`} role="img" aria-label={`Relatório financeiro de ${monthLabel(month)}`} style={{fontFamily: 'Arial, sans-serif'}}>
    <title>{`Financeiro pessoal — ${monthLabel(month)}`}</title>
    <desc>Entradas {money(data.income_cents)}, despesas {money(data.expense_cents)}, resultado {money(data.result_cents)}. A tabela abaixo contém os valores dos gráficos.</desc>
    <rect width="1000" height={height} fill="#ffffff"/>
    <text x="50" y="55" fill={green} fontSize="15" fontWeight="700">FINANCEIRO PESSOAL</text>
    <text x="50" y="99" fill={ink} fontSize="30" fontWeight="700">Relatório de {monthLabel(month)}</text>
    <text x="50" y="129" fill={muted} fontSize="14">Valores em reais · Registros confirmados · Resultado não é saldo bancário</text>
    {[['Entradas', data.income_cents], ['Despesas', data.expense_cents], ['Resultado do mês', data.result_cents]].map(([label, amount], index) => <g key={String(label)}>
      <rect x={50 + index * 305} y="159" width="290" height="91" rx="7" fill="#f1f5f1"/>
      <text x={67 + index * 305} y="185" fill={muted} fontSize="14">{label}</text>
      <text x={67 + index * 305} y="222" fill={index === 1 ? clay : green} fontSize="25" fontWeight="700">{money(Number(amount))}</text>
    </g>)}
    <text x="50" y="296" fill={ink} fontSize="20" fontWeight="700">Despesas por categoria</text>
    {data.categories.length ? data.categories.map((row, i) => <g key={row.category}>
      <text x="50" y={329 + i * 42} fill={ink} fontSize="14">{row.category}</text>
      <rect x="250" y={315 + i * 42} width="510" height="20" rx="3" fill="#edf1ed"/>
      <rect x="250" y={315 + i * 42} width={row.amount_cents / maxCategory * 510} height="20" rx="3" fill={green}/>
      <text x="950" y={330 + i * 42} textAnchor="end" fill={ink} fontSize="15">{money(row.amount_cents)}</text>
    </g>) : <text x="50" y="339" fill={muted} fontSize="15">Sem despesas confirmadas neste mês.</text>}
    <text x="50" y={trendTop} fill={ink} fontSize="20" fontWeight="700">Entradas e despesas por mês</text>
    <text x="50" y={trendTop + 27} fill={muted} fontSize="13">Até 6 meses com movimentação, até o período selecionado.</text>
    {data.trend.length ? <>
      <line x1="50" x2="950" y1={trendTop + 230} y2={trendTop + 230} stroke="#dce4dc"/>
      {data.trend.map((row, i) => {
        const center = 60 + cellWidth * (i + .5)
        return <g key={row.month}>
          <rect x={center - 33} y={trendTop + 230 - row.income / maxTrend * 162} width="29" height={row.income / maxTrend * 162} rx="2" fill={green}/>
          <rect x={center + 4} y={trendTop + 230 - row.expense / maxTrend * 162} width="29" height={row.expense / maxTrend * 162} rx="2" fill={clay}/>
          <text x={center} y={trendTop + 251} textAnchor="middle" fill={ink} fontSize="13">{row.month.slice(5)}/{row.month.slice(0, 4)}</text>
          <text x={center} y={trendTop + 274} textAnchor="middle" fill={green} fontSize="12">{money(row.income)}</text>
          <text x={center} y={trendTop + 293} textAnchor="middle" fill={clay} fontSize="12">{money(row.expense)}</text>
        </g>
      })}
    </> : <text x="50" y={trendTop + 100} fill={muted} fontSize="15">Sem movimentações confirmadas para comparar.</text>}
    <rect x="50" y={trendTop + 319} width="10" height="10" fill={green}/><text x="67" y={trendTop + 329} fill={muted} fontSize="13">Entradas</text>
    <rect x="156" y={trendTop + 319} width="10" height="10" fill={clay}/><text x="173" y={trendTop + 329} fill={muted} fontSize="13">Despesas</text>
    <text x="50" y={height - 33} fill={muted} fontSize="12">{data.pending_duplicates} possíveis duplicatas pendentes no mês. Transferências, investimentos e ajustes fora do resultado.</text>
    <text x="50" y={height - 14} fill={muted} fontSize="12">Notas detalham os lançamentos e não são somadas novamente. Dados locais, sem consulta online ao banco.</text>
  </svg>
}

async function downloadPng(svg: SVGSVGElement, month: string) {
  const source = new XMLSerializer().serializeToString(svg)
  const image = new Image()
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve()
    image.onerror = () => reject(new Error('Não foi possível gerar a imagem do relatório.'))
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(source)}`
  })
  const canvas = document.createElement('canvas')
  canvas.width = svg.viewBox.baseVal.width * 2
  canvas.height = svg.viewBox.baseVal.height * 2
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Este navegador não conseguiu preparar a imagem.')
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error('Falha ao salvar o PNG.')), 'image/png'))
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url; link.download = `financeiro-${month}.png`
  document.body.append(link); link.click(); link.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export default function Reports({month, revision}: PageProps) {
  const state = useLoad<Summary>(`/summary?month=${month}`, revision)
  const svg = useRef<SVGSVGElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function exportPng() {
    if (!svg.current) return
    setBusy(true); setError('')
    try { await downloadPng(svg.current, month) }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }
  if (state.loading) return <Loading/>
  if (state.error) return <ErrorBox message={state.error}/>
  if (!state.data) return null
  const data = state.data
  return <div className="reports">
    <ErrorBox message={error}/>
    <div className="toolbar report-tools"><div className="toolbar-actions">
      <button className="button" onClick={exportPng} disabled={busy}><Download size={16}/>{busy ? 'Gerando…' : 'Baixar PNG'}</button>
      <a className="button secondary" href={`/api/export.csv?month=${month}`} download>CSV do mês</a>
      <button className="button secondary" onClick={() => window.print()}><Printer size={16}/>Imprimir / PDF</button>
    </div></div>
    <p className="help-text report-help">O relatório usa fundo claro para facilitar a impressão. Em Imprimir / PDF, escolha “Salvar como PDF” no navegador. O CSV inclui os lançamentos ativos do mês, inclusive pendências identificadas na coluna de revisão.</p>
    <div className="report-paper"><ReportGraphic data={data} month={month} svgRef={svg}/></div>
    <details className="panel report-values"><summary>Consultar os valores dos gráficos</summary>
      <div className="table-scroll"><table><caption>Despesas de {monthLabel(month)}</caption><thead><tr><th>Categoria</th><th className="number">Valor</th></tr></thead><tbody>{data.categories.map(c => <tr key={c.category}><td>{c.category}</td><td className="number">{money(c.amount_cents)}</td></tr>)}</tbody></table></div>
      <div className="table-scroll"><table><caption>Comparação mensal</caption><thead><tr><th>Mês</th><th className="number">Entradas</th><th className="number">Despesas</th></tr></thead><tbody>{data.trend.map(t => <tr key={t.month}><td>{monthLabel(t.month)}</td><td className="number">{money(t.income)}</td><td className="number">{money(t.expense)}</td></tr>)}</tbody></table></div>
    </details>
  </div>
}
