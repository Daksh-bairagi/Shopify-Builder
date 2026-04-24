import { cn } from '@/lib/utils'

export interface BentoItem {
  title: string
  description: string
  icon: React.ReactNode
  status?: string
  tags?: string[]
  meta?: string
  cta?: string
  colSpan?: number
  hasPersistentHover?: boolean
}

interface BentoGridProps {
  items: BentoItem[]
}

function BentoGrid({ items }: BentoGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 max-w-7xl mx-auto">
      {items.map((item, index) => (
        <div
          key={index}
          className={cn(
            'group relative p-4 rounded-xl overflow-hidden transition-all duration-300',
            'border border-border bg-card',
            'hover:shadow-[0_2px_12px_rgba(169,149,201,0.08)]',
            'hover:-translate-y-0.5 will-change-transform',
            item.colSpan === 2 ? 'md:col-span-2' : 'col-span-1',
            item.hasPersistentHover && 'shadow-[0_2px_12px_rgba(169,149,201,0.08)] -translate-y-0.5',
          )}
        >
          {/* Dot-grid hover overlay */}
          <div
            className={cn(
              'absolute inset-0 transition-opacity duration-300',
              item.hasPersistentHover ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
            )}
          >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(169,149,201,0.04)_1px,transparent_1px)] bg-[length:4px_4px]" />
          </div>

          <div className="relative flex flex-col space-y-3">
            {/* Icon + Status */}
            <div className="flex items-center justify-between">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-primary/10 group-hover:bg-primary/20 transition-all duration-300">
                {item.icon}
              </div>
              {item.status && (
                <span className="text-xs font-medium px-2 py-1 rounded-lg bg-muted text-muted-foreground transition-colors duration-300 group-hover:bg-primary/10 group-hover:text-primary">
                  {item.status}
                </span>
              )}
            </div>

            {/* Title + Description */}
            <div className="space-y-2">
              <h3 className="font-medium text-foreground tracking-tight text-[15px]">
                {item.title}
                {item.meta && (
                  <span className="ml-2 text-xs text-muted-foreground font-normal">{item.meta}</span>
                )}
              </h3>
              <p className="text-sm text-muted-foreground leading-snug">{item.description}</p>
            </div>

            {/* Tags + CTA */}
            <div className="flex items-center justify-between mt-2">
              <div className="flex items-center gap-1.5 flex-wrap text-xs text-muted-foreground">
                {item.tags?.map((tag, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 rounded-md bg-muted hover:bg-primary/10 hover:text-primary transition-all duration-200 cursor-default"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
              <span className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2">
                {item.cta ?? 'Explore →'}
              </span>
            </div>
          </div>

          {/* Gradient border overlay */}
          <div
            className={cn(
              'absolute inset-0 -z-10 rounded-xl p-px bg-gradient-to-br from-transparent via-primary/10 to-transparent transition-opacity duration-300',
              item.hasPersistentHover ? 'opacity-100' : 'opacity-0 group-hover:opacity-100',
            )}
          />
        </div>
      ))}
    </div>
  )
}

export { BentoGrid }
