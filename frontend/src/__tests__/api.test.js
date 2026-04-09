import { describe, it, expect, vi } from 'vitest'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

describe('API modules exist and export functions', () => {
  it('graph api exports expected functions', async () => {
    const graphApi = await import('../api/graph.js')
    expect(graphApi).toBeDefined()
    // Check it exports something (functions or objects)
    expect(Object.keys(graphApi).length).toBeGreaterThan(0)
  })

  it('simulation api exports expected functions', async () => {
    const simApi = await import('../api/simulation.js')
    expect(simApi).toBeDefined()
    expect(Object.keys(simApi).length).toBeGreaterThan(0)
  })

  it('report api exports expected functions', async () => {
    const reportApi = await import('../api/report.js')
    expect(reportApi).toBeDefined()
    expect(Object.keys(reportApi).length).toBeGreaterThan(0)
  })
})
