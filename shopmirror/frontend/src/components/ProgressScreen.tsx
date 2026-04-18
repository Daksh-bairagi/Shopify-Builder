import { JobStatusResponse } from '../api/client'

interface Props {
  status: JobStatusResponse
}

const PIPELINE_STEPS = [
  { label: 'Ingesting', icon: (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  )},
  { label: 'Auditing', icon: (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )},
  { label: 'Simulating', icon: (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
    </svg>
  )},
  { label: 'Complete', icon: (
    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  )},
]

function getActiveStepIndex(status: JobStatusResponse['status']): number {
  switch (status) {
    case 'pending':
    case 'ingesting':
      return 0
    case 'auditing':
      return 1
    case 'simulating':
      return 2
    case 'complete':
    case 'awaiting_approval':
      return 3
    default:
      return 0
  }
}

export default function ProgressScreen({ status }: Props) {
  const activeStep = getActiveStepIndex(status.status)
  const pct = status.progress.pct

  return (
    <div className="min-h-screen bg-[#0A0E27] flex items-center justify-center px-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo + Spinner */}
        <div className="flex flex-col items-center gap-5">
          <span className="font-code text-sm font-bold text-[#6B7DB3] tracking-[0.3em] uppercase">
            ShopMirror
          </span>

          {/* Glow spinner */}
          <div className="relative w-14 h-14">
            <div className="absolute inset-0 rounded-full bg-blue-500/20 blur-xl animate-pulse" />
            <div className="relative w-14 h-14 rounded-full border-4 border-[#1E2545] border-t-blue-500 animate-spin" />
          </div>
        </div>

        {/* Status text */}
        <div className="mt-8 text-center">
          <p className="text-xl font-semibold text-white font-sans">
            {status.progress.step || 'Starting analysis...'}
          </p>
          <p className="text-[#6B7DB3] mt-1.5 text-sm">
            Analyzing your store's AI commerce readiness
          </p>
        </div>

        {/* Progress bar */}
        <div className="mt-7">
          <div className="bg-[#141830] border border-[#1E2545] rounded-full h-2 w-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${pct}%`,
                background: 'linear-gradient(90deg, #3B82F6, #60A5FA)',
                boxShadow: '0 0 12px rgba(59,130,246,0.5)',
              }}
            />
          </div>
        </div>

        {/* Percentage + status label */}
        <div className="mt-2 flex justify-between">
          <span className="font-code text-sm text-blue-400">{pct}%</span>
          <span className="text-sm text-[#4B5A8A] capitalize">{status.status}</span>
        </div>

        {/* Pipeline step indicators */}
        <div className="mt-10 card p-5">
          <div className="flex items-center justify-between">
            {PIPELINE_STEPS.map((step, idx) => {
              const isCompleted = idx < activeStep
              const isActive = idx === activeStep

              return (
                <div key={step.label} className="flex items-center">
                  <div className="flex flex-col items-center gap-2">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
                        isCompleted
                          ? 'bg-blue-600 text-white'
                          : isActive
                          ? 'bg-amber-500/20 border-2 border-amber-500 text-amber-400'
                          : 'bg-[#0F1535] border border-[#1E2545] text-[#2D3A5E]'
                      }`}
                    >
                      {step.icon}
                    </div>
                    <span
                      className={`text-xs font-medium transition-colors duration-300 ${
                        isCompleted
                          ? 'text-blue-400'
                          : isActive
                          ? 'text-amber-400'
                          : 'text-[#2D3A5E]'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>

                  {idx < PIPELINE_STEPS.length - 1 && (
                    <div
                      className={`h-px w-12 mb-5 mx-2 transition-colors duration-500 ${
                        idx < activeStep ? 'bg-blue-600' : 'bg-[#1E2545]'
                      }`}
                    />
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
