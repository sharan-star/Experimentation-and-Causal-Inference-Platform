// Thin wrapper around the native fetch API.
// Every backend route is served under the `/api` prefix; the Vite dev server
// proxies that prefix to http://localhost:8000 so requests stay same-origin.

const BASE = '/api'

async function parseResponse(res) {
  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (!res.ok) {
    let message = `Request failed with status ${res.status}`
    if (data && typeof data === 'object' && data.detail != null) {
      message =
        typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } else if (typeof data === 'string' && data.trim()) {
      message = data
    }
    const err = new Error(message)
    err.status = res.status
    throw err
  }

  return data
}

export async function apiGet(path) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'application/json' },
  })
  return parseResponse(res)
}

export async function apiPost(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
  })
  return parseResponse(res)
}

export async function apiUploadCsv(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/datasets/upload`, {
    method: 'POST',
    body: form,
  })
  return parseResponse(res)
}

// ---------------------------------------------------------------------------
// Named helpers for the dataset endpoints
// ---------------------------------------------------------------------------
export function listDatasets() {
  return apiGet('/datasets')
}

export function getDataset(name) {
  return apiGet(`/datasets/${encodeURIComponent(name)}`)
}

export function simulateDataset(simulate) {
  return apiPost('/datasets/simulate', { source: 'simulate', simulate })
}

export function health() {
  return apiGet('/health')
}
