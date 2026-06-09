import React, { useEffect, useRef, useState } from 'react'

// Friendly labels for the request status.
const STATUS_LABELS = {
  new: 'New',
  calling: 'Calling…',
  ended: 'Call ended',
  completed: 'Completed',
}

// Field labels/wording adopted from the "Vivant Downtime Check" design.
const FIELDS = [
  { name: 'business_name', label: 'Location Name', placeholder: 'e.g. Vivant Corp' },
  { name: 'location_phone', label: 'Location Phone Number', placeholder: '+1469…' },
  { name: 'isp_name', label: 'Internet Service Provider (ISP)', placeholder: 'e.g. AT&T Internet' },
  { name: 'isp_phone', label: 'Provider Phone Number (Number to Call)', placeholder: 'e.g. +18002882020', required: true },
  { name: 'business_address', label: 'Location Address', placeholder: '2727 Lyndon B Johnson Fwy…', wide: true },
  { name: 'account_number', label: 'Account Number', placeholder: '123456789', required: true, secret: true },
  { name: 'pin', label: 'Security PIN', placeholder: 'Passcode (optional)', secret: true },
  { name: 'caller_name', label: 'Your Name', placeholder: 'John Doe' },
  { name: 'circuit_id', label: 'Circuit ID', placeholder: 'optional — some ISPs require it' },
  { name: 'callback_number', label: 'Callback Phone', placeholder: '+1469…' },
  { name: 'symptoms', label: 'Symptoms / notes', placeholder: 'Internet completely down', wide: true },
  { name: 'troubleshooting_done', label: 'Troubleshooting already done', placeholder: 'Modem power-cycled' },
  { name: 'modem_light_status', label: 'Modem light status', placeholder: 'Solid red' },
]

const EMPTY = Object.fromEntries(FIELDS.map((f) => [f.name, '']))

// Friendly label + color for each report outcome.
const OUTCOMES = {
  outage_confirmed_with_eta: { label: 'Outage confirmed — ETA given', tone: 'bad' },
  outage_confirmed_no_eta: { label: 'Outage confirmed — no ETA', tone: 'bad' },
  no_outage_found: { label: 'No outage found', tone: 'good' },
  equipment_issue: { label: 'Equipment issue', tone: 'warn' },
  no_rep_reached: { label: 'No rep reached', tone: 'warn' },
  needs_review: { label: 'Needs review', tone: 'warn' },
}

function formatWhen(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

// Capitalize the first letter of each word (leaves the rest as-is, so "PM" stays "PM").
function titleCase(s) {
  if (!s) return s
  return String(s)
    .split(' ')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

// Consistent display for a report value: blank or "not provided" -> "Not provided";
// otherwise capitalize the first letter and keep the rest as written.
function fieldValue(s) {
  const v = String(s || '').trim()
  if (!v || v.toLowerCase() === 'not provided') return 'Not provided'
  return v[0].toUpperCase() + v.slice(1)
}

export default function App() {
  const [form, setForm] = useState({ ...EMPTY, use_equipment_checked_opening: false })
  const [requests, setRequests] = useState([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [operational, setOperational] = useState(null)
  const [report, setReport] = useState(null) // { ...report, requestName }
  const [busyId, setBusyId] = useState(null)
  const [shown, setShown] = useState({}) // which secret fields are revealed
  const [activeField, setActiveField] = useState(null) // which field's dropdown is open
  const [showOlder, setShowOlder] = useState(false) // expand older requests

  async function loadHealth() {
    try {
      const body = await (await fetch('/health')).json()
      setOperational(body.database === 'connected')
    } catch {
      setOperational(false)
    }
  }

  async function loadRequests() {
    try {
      setRequests(await (await fetch('/requests')).json())
    } catch {
      setError('Could not reach the backend. Is it running on port 8000?')
    }
  }

  useEffect(() => {
    loadHealth()
    loadRequests()
  }, [])

  // Keep the latest requests in a ref so the polling timer can read them.
  const requestsRef = useRef(requests)
  requestsRef.current = requests

  // While any call is in progress, quietly ask the backend to check its real
  // status every few seconds, then refresh the list (no webhook needed).
  useEffect(() => {
    const timer = setInterval(async () => {
      const calling = requestsRef.current.filter((r) => r.status === 'calling')
      if (calling.length === 0) return
      await Promise.all(
        calling.map((r) =>
          fetch(`/requests/${r.id}/refresh`, { method: 'POST' }).catch(() => {})
        )
      )
      await loadRequests()
    }, 4000)
    return () => clearInterval(timer)
  }, [])

  function update(name, value) {
    setForm((prev) => ({ ...prev, [name]: value }))
    // Starting a new request: close the old (now stale) report card.
    if (report) setReport(null)
  }

  // Previous values entered for a field, for autocomplete suggestions.
  function suggestions(name) {
    const seen = new Set()
    for (const r of requests) {
      const v = r[name]
      if (v && typeof v === 'string') seen.add(v)
    }
    return [...seen]
  }

  // Suggestions filtered by what's typed so far (max 6).
  function fieldSuggestions(name, current) {
    const q = (current || '').toLowerCase()
    return suggestions(name)
      .filter((v) => v.toLowerCase() !== q && (!q || v.toLowerCase().includes(q)))
      .slice(0, 6)
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      const resp = await fetch('/requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!resp.ok) {
        setError('Save failed — please check the required fields are filled.')
        return
      }
      setForm({ ...EMPTY, use_equipment_checked_opening: false })
      await loadRequests()
    } catch {
      setError('Could not reach the backend. Is it running on port 8000?')
    } finally {
      setSaving(false)
    }
  }

  async function dispatch(id) {
    setError('')
    try {
      const resp = await fetch(`/requests/${id}/call`, { method: 'POST' })
      if (!resp.ok) {
        let msg = 'Could not start the call.'
        if (resp.status === 409) {
          msg = 'A call is already in progress for that request.'
        } else {
          try {
            const body = await resp.json()
            if (body.detail) msg = body.detail
          } catch {
            /* keep default */
          }
        }
        setError(msg)
      }
      await loadRequests()
    } catch {
      setError('Could not reach the backend.')
    }
  }

  // Show the report card. Uses the SAVED report if one exists (free);
  // only generates a new one (real Claude call) the first time.
  async function getReport(row) {
    setError('')
    setBusyId(row.id)
    try {
      // 1) Try the already-saved report — no AI call, no cost.
      let resp = await fetch(`/requests/${row.id}/report`)
      // 2) None yet → generate it once (this is the only step that costs).
      if (resp.status === 404) {
        resp = await fetch(`/requests/${row.id}/report`, { method: 'POST' })
      }
      if (!resp.ok) {
        setError('Could not get a report (is there a finished call for this request?).')
        return
      }
      const data = await resp.json()
      // Also pull the call's recording + transcript to show in the card.
      let call = null
      try {
        const c = await fetch(`/requests/${row.id}/call`)
        if (c.ok) call = await c.json()
      } catch {
        /* recording is optional */
      }
      setReport({
        ...data,
        requestName: row.business_name,
        recordingUrl: call?.recording_url,
        transcript: call?.transcript,
      })
      await loadRequests()
    } catch {
      setError('Could not reach the backend.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>
            Vivant <span className="accent">Downtime Check</span>
          </h1>
          <p className="subtitle">Automated Outage Verification Agent</p>
        </div>
        <span className={`status ${operational ? 'up' : 'down'}`}>
          STATUS: {operational === null ? '…' : operational ? 'OPERATIONAL' : 'OFFLINE'}
        </span>
      </header>

      <form onSubmit={submit} className="card">
        <h2 className="section">▍Site Triage Input</h2>
        <div className="grid">
          {FIELDS.map((f) => (
            <label key={f.name} className={`field ${f.wide ? 'wide' : ''}`}>
              <span>
                {f.label} {f.required && <em className="req">*</em>}
              </span>
              <div className="input-wrap">
                <input
                  type={f.secret && !shown[f.name] ? 'password' : 'text'}
                  placeholder={f.placeholder}
                  value={form[f.name]}
                  onChange={(e) => update(f.name, e.target.value)}
                  onFocus={() => setActiveField(f.name)}
                  onBlur={() =>
                    setTimeout(
                      () => setActiveField((a) => (a === f.name ? null : a)),
                      120
                    )
                  }
                  autoComplete="off"
                />
                {f.secret && (
                  <button
                    type="button"
                    className="reveal"
                    onClick={() => setShown((s) => ({ ...s, [f.name]: !s[f.name] }))}
                  >
                    {shown[f.name] ? 'Hide' : 'Show'}
                  </button>
                )}
                {!f.secret &&
                  activeField === f.name &&
                  fieldSuggestions(f.name, form[f.name]).length > 0 && (
                    <ul className="suggest">
                      {fieldSuggestions(f.name, form[f.name]).map((v) => (
                        <li
                          key={v}
                          onMouseDown={() => {
                            update(f.name, v)
                            setActiveField(null)
                          }}
                        >
                          {v}
                        </li>
                      ))}
                    </ul>
                  )}
              </div>
            </label>
          ))}
        </div>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={form.use_equipment_checked_opening}
            onChange={(e) => update('use_equipment_checked_opening', e.target.checked)}
          />
          <span>Use "equipment already checked" opening (skip troubleshooting)</span>
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save request'}
        </button>
      </form>

      {report && <ReportCard report={report} onClose={() => setReport(null)} />}

      <h2 className="section">Saved requests</h2>
      {requests.length === 0 ? (
        <p className="empty">No requests yet.</p>
      ) : (
        <table className="list">
          <thead>
            <tr>
              <th>Date &amp; Time</th>
              <th>Location</th>
              <th>Service</th>
              <th>Account</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {/* Most recent request, always shown */}
            <SiteRow r={requests[0]} busyId={busyId} onDispatch={dispatch} onReport={getReport} />

            {/* Toggle row for the older requests (same table → columns line up) */}
            {requests.length > 1 && (
              <tr className="older-toggle">
                <td colSpan={6}>
                  <button type="button" onClick={() => setShowOlder((v) => !v)}>
                    {showOlder ? '▾ Hide older requests' : '▸ Show older requests'}
                  </button>
                </td>
              </tr>
            )}

            {/* Older requests */}
            {showOlder &&
              requests
                .slice(1)
                .map((r) => (
                  <SiteRow
                    key={r.id}
                    r={r}
                    busyId={busyId}
                    onDispatch={dispatch}
                    onReport={getReport}
                  />
                ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function SiteRow({ r, busyId, onDispatch, onReport }) {
  return (
    <tr>
      <td className="when">{formatWhen(r.created_at)}</td>
      <td>{r.business_name}</td>
      <td>{r.isp_name || '—'}</td>
      <td className="mono">{r.account_number}</td>
      <td>
        <span className={`badge status-${r.status}`}>
          {STATUS_LABELS[r.status] || r.status}
        </span>
      </td>
      <td className="actions">
        <button
          type="button"
          className="dispatch"
          disabled={r.status === 'calling'}
          onClick={() => onDispatch(r.id)}
        >
          Dispatch Agent
        </button>
        <button
          type="button"
          className="report-btn"
          disabled={busyId === r.id || r.status === 'calling'}
          onClick={() => onReport(r)}
        >
          {busyId === r.id
            ? 'Reading…'
            : r.status === 'completed'
              ? 'View Report'
              : 'Get Report'}
        </button>
      </td>
    </tr>
  )
}

function ReportCard({ report, onClose }) {
  const meta = OUTCOMES[report.outcome] || { label: report.outcome, tone: 'warn' }
  const noOutage = report.outcome === 'no_outage_found'
  return (
    <div className="report card">
      <div className="report-head">
        <div>
          <h2 className="section">
            Report{report.requestName ? ` — ${report.requestName}` : ''}
          </h2>
          <span className={`outcome ${meta.tone}`}>{meta.label}</span>
          {report.needs_review && <span className="review">⚠ Needs review</span>}
        </div>
        <button type="button" className="dispatch" onClick={onClose}>
          Close
        </button>
      </div>
      <dl className="report-grid">
        <div><dt>Spoke with</dt><dd>{titleCase(report.responder)} — {titleCase(report.spoke_with)}</dd></div>
        <div><dt>Outage reason</dt><dd>{noOutage ? 'No outage reported' : fieldValue(report.outage_reason)}</dd></div>
        <div><dt>Estimated restoration (ETA)</dt><dd>{fieldValue(report.estimated_restoration)}</dd></div>
        <div><dt>Reference / ticket #</dt><dd>{fieldValue(report.reference_ticket)}</dd></div>
      </dl>
      <p className="summary">{report.summary}</p>

      {report.recordingUrl && (
        <div className="recording">
          <dt>Call recording</dt>
          <audio controls src={report.recordingUrl} />
        </div>
      )}

      {report.transcript && (
        <details className="transcript">
          <summary>Show full transcript</summary>
          <div className="transcript-body">
            {report.transcript
              .split('\n')
              .filter((l) => l.trim())
              .map((line, i) => {
                let who = ''
                let rest = line
                if (line.startsWith('AI:')) {
                  who = 'AI'
                  rest = line.slice(3)
                } else if (line.startsWith('User:')) {
                  who = 'Provider'
                  rest = line.slice(5)
                }
                return (
                  <p key={i}>
                    {who && <strong>{who}:</strong>} {rest.trim()}
                  </p>
                )
              })}
          </div>
        </details>
      )}
    </div>
  )
}
