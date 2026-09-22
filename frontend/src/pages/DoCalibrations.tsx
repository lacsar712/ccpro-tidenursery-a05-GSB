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
  calibrator: '水质技术员',
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
    if (!confirm('确认删除该张校准票？删除后该塘口可能立即失去有效校准。')) return
    try {
      await api(`/api/do-calibrations/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} (${p.species})` : `#${id}`
  }

  // 每个塘口最近一张票的序号，用于标注当前生效票
  const latestIdByPond = new Map<number, number>()
  for (const r of rows) {
    if (!latestIdByPond.has(r.pondId)) latestIdByPond.set(r.pondId, r.id)
  }
  // 失效时间 = 校准时刻 + 有效小时数
  const expiresAt = (r: DoCalibration) =>
    new Date(new Date(r.calibratedAt).getTime() + r.validHours * 3600000)

  return (
    <div>
      <header className="page-header">
        <h1>溶氧探头校准票</h1>
        <p className="muted">
          实机读数与标准液读数绝对差不得超过 0.5（否则 400）；自最近一张票校准时刻起有效小时数内视为有效，过期后该塘口禁止新建水质样。
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
          标准液读数 (mg/L)
          <input
            type="number"
            step="0.01"
            value={form.standardReading}
            onChange={(e) => setForm({ ...form, standardReading: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          实机读数 (mg/L)
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
            value={form.calibrator}
            onChange={(e) => setForm({ ...form, calibrator: e.target.value })}
            required
          />
        </label>
        <button type="submit" className="btn primary">
          开具校准票
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>票号</th>
              <th>所属塘口</th>
              <th>校准时刻</th>
              <th>标准液读数</th>
              <th>实机读数</th>
              <th>绝对差</th>
              <th>有效小时数</th>
              <th>失效时刻</th>
              <th>校准人</th>
              <th>状态</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const diff = Math.abs(r.deviceReading - r.standardReading)
              const isLatest = latestIdByPond.get(r.pondId) === r.id
              const valid = isLatest && expiresAt(r).getTime() > Date.now()
              return (
                <tr key={r.id}>
                  <td>#{r.id}</td>
                  <td>{pondLabel(r.pondId)}</td>
                  <td>{new Date(r.calibratedAt).toLocaleString()}</td>
                  <td>{r.standardReading}</td>
                  <td>{r.deviceReading}</td>
                  <td>{diff.toFixed(2)}</td>
                  <td>{r.validHours}</td>
                  <td>{expiresAt(r).toLocaleString()}</td>
                  <td>{r.calibrator}</td>
                  <td>
                    {isLatest ? (
                      valid ? (
                        <span className="badge cal-ok">有效</span>
                      ) : (
                        <span className="badge cal-bad">已过期</span>
                      )
                    ) : (
                      <span className="badge dry">历史票</span>
                    )}
                  </td>
                  <td>
                    <button className="btn ghost" onClick={() => remove(r.id)}>
                      删除
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
