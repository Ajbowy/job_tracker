import { useEffect, useMemo, useState } from 'react'
import './App.css'

type Job = {
  id: number
  company: string
  position: string
  date_applied: string
  status: string
  notes: string
  follow_up_date?: string | null
}

type ReminderItem = {
  id: number
  company: string
  position: string
  status: string
  follow_up_date: string
  days_until: number
}

type ActivityData = {
  labels: string[]
  values: number[]
}

type View = 'dashboard' | 'settings'

type Preferences = {
  defaultFilter: string
  defaultSort: string
  compactLayout: boolean
}

const STATUS_OPTIONS = ['all', 'applied', 'interview', 'offer', 'rejected'] as const
const DEFAULT_PREFERENCES: Preferences = {
  defaultFilter: 'all',
  defaultSort: 'date_applied',
  compactLayout: false,
}

const DEFAULT_FORM = {
  company: '',
  position: '',
  date_applied: new Date().toISOString().slice(0, 10),
  status: 'applied',
  notes: '',
  follow_up_date: '',
}

function formatStatus(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function App() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [reminders, setReminders] = useState<{ upcoming: ReminderItem[]; overdue: ReminderItem[] }>({
    upcoming: [],
    overdue: [],
  })
  const [activity, setActivity] = useState<ActivityData>({ labels: [], values: [] })
  const [view, setView] = useState<View>('dashboard')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date_applied')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const loadData = async () => {
    try {
      setLoading(true)
      const [jobsResponse, remindersResponse, activityResponse] = await Promise.all([
        fetch('/api/jobs'),
        fetch('/api/reminders'),
        fetch('/api/activity'),
      ])

      if (!jobsResponse.ok || !remindersResponse.ok || !activityResponse.ok) {
        throw new Error('Unable to load the application data.')
      }

      const jobsData = await jobsResponse.json()
      const remindersData = await remindersResponse.json()
      const activityData = await activityResponse.json()
      setJobs(jobsData)
      setReminders(remindersData)
      setActivity(activityData)
      setError('')
    } catch (loadError) {
      setError(
        loadError instanceof Error ? loadError.message : 'Unable to load the application data.',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const savedPreferences = localStorage.getItem('jobTrackerPreferences')
    if (savedPreferences) {
      try {
        const parsed = JSON.parse(savedPreferences) as Partial<Preferences>
        const merged = { ...DEFAULT_PREFERENCES, ...parsed }
        setPreferences(merged)
        setStatusFilter(merged.defaultFilter)
        setSortBy(merged.defaultSort)
      } catch {
        setPreferences(DEFAULT_PREFERENCES)
      }
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('jobTrackerPreferences', JSON.stringify(preferences))
  }, [preferences])

  useEffect(() => {
    void loadData()
  }, [])

  useEffect(() => {
    setStatusFilter(preferences.defaultFilter)
    setSortBy(preferences.defaultSort)
  }, [preferences.defaultFilter, preferences.defaultSort])

  const visibleJobs = useMemo(() => {
    const query = search.trim().toLowerCase()
    const filtered = jobs.filter((job) => {
      const matchesStatus = statusFilter === 'all' || job.status === statusFilter
      const matchesSearch =
        query.length === 0 ||
        [job.company, job.position, job.notes, job.status].some((value) =>
          value.toLowerCase().includes(query),
        )
      return matchesStatus && matchesSearch
    })

    filtered.sort((first, second) => {
      const firstValue = first[sortBy as keyof Job] ?? ''
      const secondValue = second[sortBy as keyof Job] ?? ''
      const firstCompare = typeof firstValue === 'string' ? firstValue.toLowerCase() : String(firstValue)
      const secondCompare = typeof secondValue === 'string' ? secondValue.toLowerCase() : String(secondValue)

      const comparison = firstCompare.localeCompare(secondCompare)
      return sortDirection === 'asc' ? comparison : -comparison
    })

    return filtered
  }, [jobs, search, statusFilter, sortBy, sortDirection])

  const summary = useMemo(
    () => ({
      total: jobs.length,
      applied: jobs.filter((job) => job.status === 'applied').length,
      interview: jobs.filter((job) => job.status === 'interview').length,
      offer: jobs.filter((job) => job.status === 'offer').length,
      rejected: jobs.filter((job) => job.status === 'rejected').length,
    }),
    [jobs],
  )

  const maxActivity = activity.values.length ? Math.max(...activity.values, 1) : 1

  const handleFieldChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
  ) => {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const response = await fetch('/api/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })

      if (!response.ok) {
        const result = await response.json().catch(() => ({}))
        throw new Error(result.detail || 'The application could not be saved.')
      }

      setForm(DEFAULT_FORM)
      await loadData()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to save this application.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (jobId: number) => {
    const confirmed = window.confirm('Remove this application from the tracker?')
    if (!confirmed) {
      return
    }

    try {
      const response = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' })
      if (!response.ok) {
        const result = await response.json().catch(() => ({}))
        throw new Error(result.detail || 'The application could not be removed.')
      }
      await loadData()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : 'The application could not be removed.')
    }
  }

  const handleExport = async () => {
    try {
      const response = await fetch('/api/jobs/export')
      if (!response.ok) {
        throw new Error('The CSV export is unavailable right now.')
      }

      const blob = await response.blob()
      const href = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = href
      link.download = 'job_tracker_export.csv'
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(href)
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : 'The CSV export failed.')
    }
  }

  if (view === 'settings') {
    return (
      <div className={`app-shell ${preferences.compactLayout ? 'compact' : ''}`}>
        <header className="topbar">
          <div>
            <p className="eyebrow">Preferences</p>
            <h1>Settings</h1>
          </div>
          <div className="topbar-actions">
            <button type="button" className="secondary-button" onClick={() => setView('dashboard')}>
              Back to tracker
            </button>
          </div>
        </header>

        <main className="settings-page">
          <section className="panel settings-panel">
            <div className="panel-header">
              <div>
                <p className="kicker">Overview</p>
                <h2>User preferences</h2>
              </div>
            </div>

            <div className="settings-grid">
              <label>
                Default status filter
                <select
                  value={preferences.defaultFilter}
                  onChange={(event) =>
                    setPreferences((current) => ({
                      ...current,
                      defaultFilter: event.target.value,
                    }))
                  }
                >
                  {STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {status === 'all' ? 'All statuses' : formatStatus(status)}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Default sorting
                <select
                  value={preferences.defaultSort}
                  onChange={(event) =>
                    setPreferences((current) => ({
                      ...current,
                      defaultSort: event.target.value,
                    }))
                  }
                >
                  <option value="date_applied">Date applied</option>
                  <option value="company">Company</option>
                  <option value="position">Position</option>
                  <option value="status">Status</option>
                </select>
              </label>

              <label className="checkbox-field">
                <input
                  type="checkbox"
                  checked={preferences.compactLayout}
                  onChange={(event) =>
                    setPreferences((current) => ({
                      ...current,
                      compactLayout: event.target.checked,
                    }))
                  }
                />
                Use compact layout
              </label>
            </div>
          </section>
        </main>
      </div>
    )
  }

  return (
    <div className={`app-shell ${preferences.compactLayout ? 'compact' : ''}`}>
      <header className="topbar">
        <div>
          <p className="eyebrow">Portfolio project</p>
          <h1>Job Tracker</h1>
        </div>

        <div className="topbar-actions">
          <button type="button" className="secondary-button" onClick={() => setView('settings')}>
            Settings
          </button>
          <button type="button" className="secondary-button" onClick={() => void loadData()}>
            Refresh
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="stats-grid" aria-label="job statistics">
          <article className="stat-card">
            <span>Total</span>
            <strong>{summary.total}</strong>
          </article>
          <article className="stat-card">
            <span>Applied</span>
            <strong>{summary.applied}</strong>
          </article>
          <article className="stat-card">
            <span>Interview</span>
            <strong>{summary.interview}</strong>
          </article>
          <article className="stat-card">
            <span>Offers</span>
            <strong>{summary.offer}</strong>
          </article>
        </section>

        <section className="overview-grid">
          <article className="panel chart-panel">
            <div className="panel-header">
              <div>
                <p className="kicker">Overview</p>
                <h2>Weekly activity</h2>
              </div>
            </div>

            <div className="chart" aria-label="weekly application activity">
              {activity.labels.map((label, index) => { 
                const value = activity.values[index] ?? 0
                const height = `${Math.max((value / maxActivity) * 100, value > 0 ? 18 : 8)}%`
                return (
                  <div key={`${label}-${index}`} className="chart-column">
                    <div className="chart-bar-wrap">
                      <div className="chart-bar" style={{ height }} />
                    </div>
                    <span>{label}</span>
                  </div>
                )
              })}
            </div>
          </article>

          <article className="panel reminders-panel">
            <div className="panel-header">
              <div>
                <p className="kicker">Follow-ups</p>
                <h2>Reminders</h2>
              </div>
            </div>

            <div className="reminder-list">
              <div>
                <h3>Upcoming</h3>
                {reminders.upcoming.length === 0 ? (
                  <p className="empty-state small">No upcoming follow-ups.</p>
                ) : (
                  reminders.upcoming.map((item) => (
                    <div key={`upcoming-${item.id}`} className="reminder-item">
                      <div>
                        <strong>{item.company}</strong>
                        <span>{item.position}</span>
                      </div>
                      <small>{item.follow_up_date} · {item.days_until}d</small>
                    </div>
                  ))
                )}
              </div>

              <div>
                <h3>Overdue</h3>
                {reminders.overdue.length === 0 ? (
                  <p className="empty-state small">No overdue reminders.</p>
                ) : (
                  reminders.overdue.map((item) => (
                    <div key={`overdue-${item.id}`} className="reminder-item overdue">
                      <div>
                        <strong>{item.company}</strong>
                        <span>{item.position}</span>
                      </div>
                      <small>{item.follow_up_date} · {Math.abs(item.days_until)}d</small>
                    </div>
                  ))
                )}
              </div>
            </div>
          </article>
        </section>

        <div className="content-grid">
          <section className="panel app-table-panel">
            <div className="panel-header">
              <div>
                <p className="kicker">Pipeline</p>
                <h2>Applications</h2>
              </div>
              <button type="button" className="secondary-button" onClick={handleExport}>
                Export CSV
              </button>
            </div>

            <div className="table-toolbar">
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search applications"
              />

              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {status === 'all' ? 'All statuses' : formatStatus(status)}
                  </option>
                ))}
              </select>

              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="date_applied">Sort by date</option>
                <option value="company">Sort by company</option>
                <option value="position">Sort by position</option>
                <option value="status">Sort by status</option>
              </select>

              <button
                type="button"
                className="secondary-button"
                onClick={() => setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'))}
              >
                {sortDirection === 'asc' ? 'Ascending' : 'Descending'}
              </button>
            </div>

            {error && <p className="error-banner">{error}</p>}

            {loading ? (
              <p className="empty-state">Loading applications…</p>
            ) : visibleJobs.length === 0 ? (
              <p className="empty-state">No results match your current filters.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Position</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th>Follow-up</th>
                      <th>Notes</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleJobs.map((job) => (
                      <tr key={job.id}>
                        <td>{job.company}</td>
                        <td>{job.position}</td>
                        <td>{job.date_applied}</td>
                        <td>
                          <span className="table-status">{formatStatus(job.status)}</span>
                        </td>
                        <td>{job.follow_up_date || '—'}</td>
                        <td>{job.notes || '—'}</td>
                        <td>
                          <button type="button" className="delete-button" onClick={() => void handleDelete(job.id)}>
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <aside className="panel form-panel">
            <div className="panel-header">
              <div>
                <p className="kicker">Add</p>
                <h2>New application</h2>
              </div>
            </div>

            <form className="job-form" onSubmit={handleSubmit}>
              <label>
                Company
                <input
                  name="company"
                  value={form.company}
                  onChange={handleFieldChange}
                  placeholder="Northstar Labs"
                />
              </label>

              <label>
                Position
                <input
                  name="position"
                  value={form.position}
                  onChange={handleFieldChange}
                  placeholder="Product Designer"
                />
              </label>

              <div className="split-fields">
                <label>
                  Date applied
                  <input
                    type="date"
                    name="date_applied"
                    value={form.date_applied}
                    onChange={handleFieldChange}
                  />
                </label>

                <label>
                  Status
                  <select name="status" value={form.status} onChange={handleFieldChange}>
                    <option value="applied">Applied</option>
                    <option value="interview">Interview</option>
                    <option value="offer">Offer</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </label>
              </div>

              <label>
                Follow-up date
                <input
                  type="date"
                  name="follow_up_date"
                  value={form.follow_up_date}
                  onChange={handleFieldChange}
                />
              </label>

              <label>
                Notes
                <textarea
                  name="notes"
                  value={form.notes}
                  onChange={handleFieldChange}
                  rows={5}
                  placeholder="Recruiter notes, interview details, or follow-up actions."
                />
              </label>

              <button type="submit" className="primary-button" disabled={submitting}>
                {submitting ? 'Saving…' : 'Save application'}
              </button>
            </form>
          </aside>
        </div>
      </main>
    </div>
  )
}

export default App
