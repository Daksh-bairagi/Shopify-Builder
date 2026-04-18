import { useState, useEffect, useRef } from 'react'
import { api, AuditReport, JobStatusResponse, AnalyzeRequest } from './api/client'
import InputScreen from './components/InputScreen'
import ProgressScreen from './components/ProgressScreen'
import Dashboard from './components/Dashboard'

type Screen = 'input' | 'progress' | 'dashboard' | 'executing'

export default function App() {
  const [screen, setScreen] = useState<Screen>('input')
  const [jobId, setJobId] = useState<string | null>(null)
  const [adminToken, setAdminToken] = useState<string | null>(null)
  const [merchantIntent, setMerchantIntent] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null)
  const [report, setReport] = useState<AuditReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const POLL_MS = Number(import.meta.env.VITE_POLLING_INTERVAL_MS ?? 2000)

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }

  const startPolling = (id: string, terminalStatuses: string[]) => {
    stopPolling()
    const poll = async () => {
      try {
        const status = await api.getJob(id)
        setJobStatus(status)
        if (terminalStatuses.includes(status.status)) {
          stopPolling()
          if (status.status === 'error') {
            setError(status.error ?? 'Analysis failed')
            setScreen('input')
          } else {
            setReport(status.report)
            setScreen('dashboard')
          }
        }
      } catch {
        // network hiccup — keep polling
      }
    }
    poll()
    pollingRef.current = setInterval(poll, POLL_MS)
  }

  const handleSubmit = async (req: AnalyzeRequest) => {
    setError(null)
    setAdminToken(req.admin_token ?? null)
    setMerchantIntent(req.merchant_intent ?? null)
    try {
      const { job_id } = await api.analyze(req)
      setJobId(job_id)
      setScreen('progress')
      startPolling(job_id, ['complete', 'awaiting_approval', 'error'])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start analysis')
    }
  }

  const handleExecute = async (approvedFixIds: string[]) => {
    if (!jobId || !adminToken) return
    await api.execute(jobId, {
      approved_fix_ids: approvedFixIds,
      admin_token: adminToken,
      merchant_intent: merchantIntent ?? undefined,
    })
    setScreen('executing')
    startPolling(jobId, ['complete', 'error'])
  }

  const handleReset = () => {
    stopPolling()
    setScreen('input')
    setJobId(null)
    setAdminToken(null)
    setMerchantIntent(null)
    setJobStatus(null)
    setReport(null)
    setError(null)
  }

  useEffect(() => {
    return stopPolling
  }, [])

  const executingStatus: JobStatusResponse = {
    status: 'simulating' as const,
    progress: { step: 'Agent running fixes...', pct: 50 },
    report: null,
    error: null,
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {screen === 'input' && (
        <InputScreen onSubmit={handleSubmit} error={error} />
      )}
      {screen === 'progress' && jobStatus && (
        <ProgressScreen status={jobStatus} />
      )}
      {screen === 'executing' && (
        <ProgressScreen status={executingStatus} />
      )}
      {screen === 'dashboard' && report && (
        <Dashboard
          report={report}
          jobId={jobId!}
          adminToken={adminToken}
          onReset={handleReset}
          onExecute={handleExecute}
        />
      )}
    </div>
  )
}
