import { useState, useEffect, useRef } from 'react'
import { api, AuditReport, JobStatusResponse, AnalyzeRequest } from './api/client'
import LandingPage from './components/LandingPage'
import InputScreen from './components/InputScreen'
import ProgressScreen from './components/ProgressScreen'
import Dashboard from './components/Dashboard'

type Screen = 'landing' | 'input' | 'progress' | 'dashboard' | 'executing'

export default function App() {
  const [screen, setScreen] = useState<Screen>('landing')
  const [jobId, setJobId] = useState<string | null>(null)
  const [adminToken, setAdminToken] = useState<string | null>(null)
  const [merchantIntent, setMerchantIntent] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null)
  const [report, setReport] = useState<AuditReport | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [prefillUrl, setPrefillUrl] = useState<string | null>(null)
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
          if (status.status === 'failed') {
            setError(status.error ?? 'Analysis failed')
            if (status.report) {
              // Execution failed but we have an audit report — keep the user on the dashboard.
              setReport(status.report)
              setScreen('dashboard')
            } else if (report) {
              // Execution failed mid-flight; we already had a report in memory — keep them on it.
              setScreen('dashboard')
            } else {
              setScreen('input')
            }
          } else {
            if (status.report) setReport(status.report)
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
    // Defensive resets: clear any prior report/job state so a failed re-run can never
    // surface stale data from a previous analysis through the polling closure.
    setError(null)
    setReport(null)
    setJobStatus(null)
    setAdminToken(req.admin_token ?? null)
    setMerchantIntent(req.merchant_intent ?? null)
    try {
      const { job_id } = await api.analyze(req)
      setJobId(job_id)
      setScreen('progress')
      startPolling(job_id, ['complete', 'awaiting_approval', 'failed'])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start analysis')
    }
  }

  const handleExecute = async (approvedFixIds: string[]) => {
    if (!jobId || !adminToken) return
    setError(null)
    try {
      await api.execute(jobId, {
        approved_fix_ids: approvedFixIds,
        admin_token: adminToken,
        merchant_intent: merchantIntent ?? undefined,
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start fix execution')
      throw e
    }
    setScreen('executing')
    startPolling(jobId, ['complete', 'failed'])
  }

  const handleReportRefresh = async () => {
    if (!jobId) return
    try {
      const status = await api.getJob(jobId)
      if (status.report) {
        setReport(status.report)
        setJobStatus(status)
      }
    } catch {
      // Non-fatal: refresh failures shouldn't break the dashboard.
    }
  }

  const handleRestart = (prefilledUrl?: string) => {
    stopPolling()
    setScreen('input')
    setJobId(null)
    setJobStatus(null)
    setReport(null)
    setError(null)
    if (prefilledUrl) {
      setPrefillUrl(prefilledUrl)
    }
  }

  const handleReset = () => {
    stopPolling()
    setScreen('landing')
    setJobId(null)
    setAdminToken(null)
    setMerchantIntent(null)
    setJobStatus(null)
    setReport(null)
    setError(null)
    setPrefillUrl(null)
  }

  useEffect(() => {
    return stopPolling
  }, [])

  // While the agent is executing, only trust the live polling state once the
  // backend has actually flipped to 'executing'. Otherwise we'd leak the previous
  // analysis step ("Assembling report") into the executing screen during the gap
  // between POST /execute and the agent's first status update.
  const executingStatus: JobStatusResponse = jobStatus && jobStatus.status === 'executing'
    ? jobStatus
    : {
        status: 'executing' as const,
        progress: { step: 'Starting fix agent…', pct: 5 },
        report: null,
        error: null,
      }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {screen === 'landing' && (
        <LandingPage onGetStarted={() => setScreen('input')} />
      )}
      {screen === 'input' && (
        <InputScreen onSubmit={handleSubmit} error={error} prefillUrl={prefillUrl} />
      )}
      {screen === 'progress' && (
        <ProgressScreen status={jobStatus ?? { status: 'ingesting' as const, progress: { step: 'Starting analysis...', pct: 0 }, report: null, error: null }} />
      )}
      {screen === 'executing' && (
        <ProgressScreen status={executingStatus} />
      )}
      {screen === 'dashboard' && report && (
        <Dashboard
          report={report}
          jobId={jobId!}
          adminToken={adminToken}
          error={error}
          onReset={handleReset}
          onRestartWithUrl={handleRestart}
          onExecute={handleExecute}
          onReportRefresh={handleReportRefresh}
        />
      )}
    </div>
  )
}
