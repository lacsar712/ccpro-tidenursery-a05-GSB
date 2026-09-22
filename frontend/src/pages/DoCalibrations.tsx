import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { DoCalibration, Pond } from '../types'

function nowLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

const empty = {
  pondId: 0,
  calibratedAt: nowLocal(),
  standardReading: 6.8,
  deviceReading: 6.8,
  validHours: 720,
  operatorName: '水质技术员',
}

export default function DoCalibrations() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<DoCalibration[]>([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')

  async function load() {
    const [ps, cs] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<DoCalibration[]>('/api/do-calibrations'),
    ])
    setPonds(ps)
    setRows(cs)
    if (!form.pondId && ps[0]) {
      setForm((f) => ({ ...f, pondId: ps[0].id }))
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/do-calibrations', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          calibratedAt: new Date(form.calibratedAt).toISOString(),
        }),
      })
      setForm((f) => ({ ...empty, pondId: f.pondId, calibratedAt: nowLocal() }))
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认作废（删除）该张校准票？作废后该塘可能立即失去有效校准。')) return
    try {
      await api(`/api/do-calibrations/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} · ${p.species}` : `#${id}`
  }

  const diff = Math.abs(form.deviceReading - form.standardReading)

  return (
    <div>
      <header className="page-header">
        <h1>溶氧探头校准票</h1>
        <p className="muted">
          实机读数与标准液读数偏差不得超过 0.5 mg/L，否则登记失败；
          自校准时刻起有效小时数内视为有效，过期后该塘禁止新建水质样。
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          所属塘口
          <select
            value={form.pondId}
            onChange={(e) => setForm({ ...form, pondId: Number(e.target.value) })}
            required
          >
            {ponds.map((p) => (
              <option key={p.id} value={p.id}>
                {p.pondCode} · {p.species}
                {p.calibrationValid ? '（当前校准有效）' : '（当前校准失效）'}
              </option>
            ))}
          </select>
        </label>
        <label>
          校准时刻
          <input
            type="datetime-local"
            value={form.calibratedAt}
            onChange={(e) => setForm({ ...form, calibratedAt: e.target.value })}
            required
          />
        </label>
        <label>
          标准液读数 mg/L
          <input
            type="number"
            step="0.01"
            value={form.standardReading}
            onChange={(e) => setForm({ ...form, standardReading: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          实机读数 mg/L
          <input
            type="number"
            step="0.01"
            value={form.deviceReading}
            onChange={(e) => setForm({ ...form, deviceReading: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          有效小时数（正整数）
          <input
            type="number"
            step="1"
            min="1"
            value={form.validHours}
            onChange={(e) => setForm({ ...form, validHours: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          校准人
          <input
            value={form.operatorName}
            onChange={(e) => setForm({ ...form, operatorName: e.target.value })}
            required
          />
        </label>
        <div className={`span-2 hint ${diff > 0.5 ? 'hint-bad' : ''}`}>
          读数偏差：{diff.toFixed(2)} mg/L
          {diff > 0.5 ? '（超过 0.5，登记将失败 400）' : '（≤ 0.5，允许登记）'}
        </div>
        <button type="submit" className="btn primary">
          开具校准票
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>票号</th>
              <th>塘口</th>
              <th>校准时刻</th>
              <th>标准液读数</th>
              <th>实机读数</th>
              <th>偏差</th>
              <th>有效小时数</th>
              <th>校准人</th>
              <th>当前状态</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>#{r.id}</td>
                <td>{pondLabel(r.pondId)}</td>
                <td>{new Date(r.calibratedAt).toLocaleString()}</td>
                <td>{r.standardReading}</td>
                <td>{r.deviceReading}</td>
                <td>{Math.abs(r.deviceReading - r.standardReading).toFixed(2)}</td>
                <td>{r.validHours}</td>
                <td>{r.operatorName}</td>
                <td>
                  <span className={`badge ${r.valid ? 'stocked' : 'quarantine'}`}>
                    {r.valid ? '有效' : '已过期'}
                  </span>
                </td>
                <td>
                  <button className="btn ghost" onClick={() => remove(r.id)}>
                    作废
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
