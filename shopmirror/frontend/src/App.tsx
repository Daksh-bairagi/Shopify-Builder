import { useState, useEffect, useRef } from 'react'
import { api, AuditReport, JobStatusResponse, AnalyzeRequest } from './api/client'
import InputScreen from './components/InputScreen'
import ProgressScreen from './components/ProgressScreen'
import Dashboard from './components/Dashboard'

type Screen = 'input' | 'progress' | 'dashboard'

export default function App() {
  const [screen, setScreen] = useState<Screen>('input')
  const [jobId, setJobId] = useState<string | null>(null)
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

  const handleSubmit = async (req: AnalyzeRequest) => {
    setError(null)
    try {
      const { job_id } = await api.analyze(req)
      setJobId(job_id)
      setScreen('progress')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start analysis')
    }
  }

  useEffect(() => {
    if (screen !== 'progress' || !jobId) return

    const poll = async () => {
      try {
        const status = await api.getJob(jobId)
        setJobStatus(status)
        if (status.status === 'complete' || status.status === 'awaiting_approval') {
          stopPolling()
          setReport(status.report)
          setScreen('dashboard')
        } else if (status.status === 'error') {
          stopPolling()
          setError(status.error ?? 'Analysis failed')
          setScreen('input')
        }
      } catch (e) {
        // network hiccup — keep polling
      }
    }

    poll()
    pollingRef.current = setInterval(poll, POLL_MS)
    return stopPolling
  }, [screen, jobId])

  const handleReset = () => {
    stopPolling()
    setScreen('input')
    setJobId(null)
    setJobStatus(null)
    setReport(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {screen === 'input' && (
        <InputScreen onSubmit={handleSubmit} error={error} />
      )}
      {screen === 'progress' && jobStatus && (
        <ProgressScreen status={jobStatus} />
      )}
      {screen === 'dashboard' && report && (
        <Dashboard report={report} jobId={jobId!} onReset={handleReset} />
      )}
    </div>
  )
}
