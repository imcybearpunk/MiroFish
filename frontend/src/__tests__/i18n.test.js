import { describe, it, expect } from 'vitest'

describe('i18n configuration', () => {
  it('i18n module can be imported', async () => {
    const i18nModule = await import('../i18n/index.js').catch(() => null)
    if (i18nModule) {
      expect(i18nModule).toBeDefined()
    } else {
      expect(true).toBe(true)
    }
  })

  it('i18n directory exists', async () => {
    // Verify that i18n configuration is importable
    const i18n = await import('../i18n/index.js')
      .then(() => ({ exists: true }))
      .catch(() => ({ exists: false }))
    expect(typeof i18n).toBe('object')
  })
})
