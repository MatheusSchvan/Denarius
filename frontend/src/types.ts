export type Page = 'overview' | 'transactions' | 'imports' | 'receipts' | 'balances' | 'settings' | 'reports'
export type Kind = 'income' | 'expense' | 'transfer' | 'investment' | 'adjustment'
export type Bootstrap = { categories: string[]; months: string[]; banks: string[]; transaction_count: number }
export type Transaction = {
  id: number; date: string; description: string; original_description: string;
  amount_cents: number; kind: Kind; category: string; bank: string;
  origin: string; notes: string; pending_duplicate: number; receipt_id: number | null; import_id: number | null
}
export type Summary = {
  income_cents: number; expense_cents: number; result_cents: number;
  count: number; unclassified: number; pending_duplicates: number;
  unlinked_receipts: number; excluded_count: number;
  categories: {category: string; amount_cents: number}[];
  trend: {month: string; income: number; expense: number}[]
}
export type ImportResult = { bank: string; total: number; new: number; duplicates: number; pending: number }
export type ImportPreview = ImportResult & {rows: (Transaction & {action: string})[]}
export type ImportLog = {id: number; filename: string; bank: string; added: number; duplicates: number; pending: number; row_count: number; created_at: string}
export type ReceiptItem = {id?: number; description: string; quantity: string; unit: string; unit_price_cents: number; total_cents: number; category: string}
export type Receipt = {id: number; merchant: string; date: string; total_cents: number; transaction_id: number | null; item_count: number; transaction_description?: string; filename?: string}
export type ReceiptDetail = Receipt & {items: ReceiptItem[]; candidates: Transaction[]; difference_cents: number}
export type ReceiptPreview = {merchant: string; date: string; total_cents: number; items: ReceiptItem[]; warnings: string[]; difference_cents: number}
export type PageProps = { month: string; revision: number; categories: string[]; banks: string[]; changed: () => void; notify: (text: string) => void; navigate: (page: Page) => void }
