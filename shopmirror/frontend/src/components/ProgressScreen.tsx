import { JobStatusResponse } from '../api/client'

interface Props {
  status: JobStatusResponse
}

const PIPELINE_STEPS = ['Ingesting', 'Auditing', 'Simulating', 'Complete']

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
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md mt-32">
        {/* Logo + Spinner */}
        <div className="flex flex-col items-center gap-4">
          <p className="text-sm text-gray-400 tracking-widest uppercase">ShopMirror</p>
          <div className="w-12 h-12 rounded-full border-4 border-gray-700 border-t-sky-500 animate-spin" />
        </div>

        {/* Status text */}
        <div className="mt-8 text-center">
          <p className="text-xl font-semibold text-white">{status.progress.step}</p>
          <p className="text-gray-400 mt-1 text-sm">
            Analyzing your store's AI commerce readiness...
          </p>
        </div>

        {/* Progress bar */}
        <div className="mt-6">
          <div className="bg-gray-800 rounded-full h-2 w-full overflow-hidden">
            <div
              className="bg-sky-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Percentage + status label */}
        <div className="mt-3 flex justify-between">
          <span className="text-sm text-gray-400">{pct}%</span>
          <span className="text-sm text-gray-500 capitalize">{status.status}</span>
        </div>

        {/* Pipeline step dots */}
        <div className="mt-8 flex items-center justify-center gap-0">
          {PIPELINE_STEPS.map((label, idx) => {
            const isCompleted = idx < activeStep
            const isActive = idx === activeStep
            const dotColor = isCompleted
              ? 'bg-green-500'
              : isActive
              ? 'bg-sky-500'
              : 'bg-gray-600'
            const labelColor = isCompleted
              ? 'text-green-400'
              : isActive
              ? 'text-sky-400'
              : 'text-gray-600'

            return (
              <div key={label} className="flex items-center">
                <div className="flex flex-col items-center gap-1.5">
                  <div className={`w-3 h-3 rounded-full ${dotColor} transition-colors duration-300`} />
                  <span className={`text-xs ${labelColor} transition-colors duration-300`}>
                    {label}
                  </span>
                </div>
                {idx < PIPELINE_STEPS.length - 1 && (
                  <div
                    className={`h-px w-16 mb-4 mx-1 transition-colors duration-300 ${
                      idx < activeStep ? 'bg-green-600' : 'bg-gray-700'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
