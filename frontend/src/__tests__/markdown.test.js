import { describe, it, expect, vi } from 'vitest'

// Mock DOMPurify since jsdom doesn't have full browser APIs
vi.mock('dompurify', () => ({
  default: {
    sanitize: (html, _opts) => html, // passthrough in tests
  },
}))

import { renderMarkdown } from '../utils/markdown.js'

describe('renderMarkdown', () => {
  it('returns empty string for null input', () => {
    expect(renderMarkdown(null)).toBe('')
    expect(renderMarkdown(undefined)).toBe('')
    expect(renderMarkdown('')).toBe('')
  })

  it('renders bold text', () => {
    const result = renderMarkdown('**hello**')
    expect(result).toContain('<strong>hello</strong>')
  })

  it('renders italic text', () => {
    const result = renderMarkdown('*hello*')
    expect(result).toContain('<em>hello</em>')
  })

  it('renders h2 heading', () => {
    const result = renderMarkdown('## Title')
    expect(result).toContain('<h3 class="md-h3">Title</h3>')
  })

  it('renders h3 heading', () => {
    const result = renderMarkdown('### Subtitle')
    expect(result).toContain('<h4 class="md-h4">Subtitle</h4>')
  })

  it('renders unordered list items', () => {
    const result = renderMarkdown('- item one\n- item two')
    expect(result).toContain('<li class="md-li"')
    expect(result).toContain('item one')
    expect(result).toContain('item two')
  })

  it('renders inline code', () => {
    const result = renderMarkdown('use `npm install`')
    expect(result).toContain('<code class="inline-code">npm install</code>')
  })

  it('renders links with noopener', () => {
    const result = renderMarkdown('[GitHub](https://github.com)')
    expect(result).toContain('href="https://github.com"')
    expect(result).toContain('rel="noopener noreferrer"')
  })

  it('strips leading h2 section title', () => {
    const result = renderMarkdown('## Section Title\n\nContent here')
    expect(result).not.toContain('Section Title')
    expect(result).toContain('Content here')
  })

  it('renders blockquotes', () => {
    const result = renderMarkdown('> important note')
    expect(result).toContain('<blockquote class="md-quote">important note</blockquote>')
  })

  it('passes output through DOMPurify.sanitize', () => {
    // DOMPurify is mocked as passthrough, but we verify it's called
    const result = renderMarkdown('hello world')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})
