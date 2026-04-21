import type { ProductSummary, Finding } from '../api/client'

interface Props {
  products: ProductSummary[]
  findings: Finding[]
}

// The check IDs displayed as columns — ordered by pillar
const COLUMNS: { id: string; label: string }[] = [
  { id: 'D1b', label: 'Catalog' },
  { id: 'D2',  label: 'Sitemap' },
  { id: 'C1',  label: 'Prod Type' },
  { id: 'C2',  label: 'Title' },
  { id: 'C3',  label: 'Variants' },
  { id: 'C4',  label: 'GTIN' },
  { id: 'C5',  label: 'Metafields' },
  { id: 'C6',  label: 'Alt Text' },
  { id: 'Con1', label: 'Price ≡' },
  { id: 'Con2', label: 'Stock ≡' },
  { id: 'T1',  label: 'Returns' },
  { id: 'A1',  label: 'Tracked' },
  { id: 'A2',  label: 'Oversell' },
]

function cellColor(failing: boolean): string {
  return failing
    ? 'bg-red-500/80 border-red-600/50'
    : 'bg-blue-500/20 border-blue-600/20'
}

export default function HeatmapGrid({ products, findings }: Props) {
  if (products.length === 0) return null

  // Build a set: product_id → set of failing check_ids from findings
  const failingByProduct: Record<string, Set<string>> = {}
  for (const finding of findings) {
    for (const pid of finding.affected_products) {
      if (!failingByProduct[pid]) failingByProduct[pid] = new Set()
      failingByProduct[pid].add(finding.check_id)
    }
  }

  // Show up to 25 products, already sorted by gap_score desc
  const rows = products.slice(0, 25)

  // Which columns actually have any failures (to avoid showing all-green columns)
  const activeColumns = COLUMNS.filter(col =>
    rows.some(p => failingByProduct[p.product_id]?.has(col.id))
  )
  const displayColumns = activeColumns.length >= 3 ? activeColumns : COLUMNS

  const totalIssues = rows.reduce(
    (acc, p) => acc + (failingByProduct[p.product_id]?.size ?? 0),
    0
  )
  const cellsTotal = rows.length * displayColumns.length
  const redPct = cellsTotal > 0 ? Math.round((totalIssues / cellsTotal) * 100) : 0

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs font-code text-[#4B5A8A]">
            {rows.length} products × {displayColumns.length} fields
          </span>
          <span className="text-xs font-code text-red-400">
            {redPct}% cells failing
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="flex items-center gap-1 text-[#6B7DB3]">
            <span className="w-2.5 h-2.5 rounded-sm bg-red-500/80 inline-block" />
            Failing
          </span>
          <span className="flex items-center gap-1 text-[#6B7DB3]">
            <span className="w-2.5 h-2.5 rounded-sm bg-blue-500/20 border border-blue-600/20 inline-block" />
            Passing
          </span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="text-left font-code text-[#4B5A8A] font-normal pb-2 pr-3 min-w-[140px] max-w-[180px]">
                Product
              </th>
              {displayColumns.map(col => (
                <th
                  key={col.id}
                  className="font-code text-[#4B5A8A] font-normal pb-2 px-0.5 text-center min-w-[52px]"
                  title={col.id}
                >
                  <div className="flex flex-col items-center gap-0.5">
                    <span className="text-[10px] text-[#2D3A5E]">{col.id}</span>
                    <span>{col.label}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((product) => {
              const failing = failingByProduct[product.product_id] ?? new Set()
              return (
                <tr key={product.product_id} className="group">
                  <td className="py-0.5 pr-3">
                    <span
                      className="text-[#A8B4D8] group-hover:text-white transition-colors truncate block max-w-[176px]"
                      title={product.title}
                    >
                      {product.title}
                    </span>
                  </td>
                  {displayColumns.map(col => {
                    const isFailing = failing.has(col.id)
                    return (
                      <td key={col.id} className="py-0.5 px-0.5 text-center">
                        <div
                          className={`mx-auto w-8 h-5 rounded border ${cellColor(isFailing)} transition-all`}
                          title={isFailing ? `${col.id}: failing` : `${col.id}: passing`}
                        />
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {products.length > 25 && (
        <p className="text-xs text-[#2D3A5E] font-code text-center">
          Showing worst 25 of {products.length} products
        </p>
      )}
    </div>
  )
}
