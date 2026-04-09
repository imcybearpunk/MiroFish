/**
 * Sanitized markdown renderer
 * Uses DOMPurify to prevent XSS from LLM-generated content rendered via v-html
 */
import DOMPurify from 'dompurify'

/**
 * Renders markdown to sanitized HTML safe for use with v-html.
 * @param {string} content - Raw markdown string (may come from LLM output)
 * @returns {string} Sanitized HTML string
 */
export function renderMarkdown(content) {
  if (!content) return ''

  // Strip leading h2 heading (section title already shown in parent)
  let processedContent = content.replace(/^##\s+.+\n+/, '')

  // Code blocks
  let html = processedContent.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // Headings
  html = html.replace(/^#### (.+)$/gm, '<h5 class="md-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')

  // Blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')

  // Lists
  html = html.replace(/^(\s*)- (.+)$/gm, (match, indent, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-li" data-level="${level}">${text}</li>`
  })
  html = html.replace(/^(\s*)(\d+)\. (.+)$/gm, (match, indent, num, text) => {
    const level = Math.floor(indent.length / 2)
    return `<li class="md-oli" data-level="${level}">${text}</li>`
  })

  // Wrap lists
  html = html.replace(/(<li class="md-li"[^>]*>.*?<\/li>\s*)+/g, '<ul class="md-ul">$&</ul>')
  html = html.replace(/(<li class="md-oli"[^>]*>.*?<\/li>\s*)+/g, '<ol class="md-ol">$&</ol>')

  // Clean up list whitespace
  html = html.replace(/<\/li>\s+<li/g, '</li><li')
  html = html.replace(/<ul class="md-ul">\s+/g, '<ul class="md-ul">')
  html = html.replace(/<ol class="md-ol">\s+/g, '<ol class="md-ol">')
  html = html.replace(/\s+<\/ul>/g, '</ul>')
  html = html.replace(/\s+<\/ol>/g, '</ol>')

  // Bold and italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/_(.+?)_/g, '<em>$1</em>')

  // Horizontal rules
  html = html.replace(/^---$/gm, '<hr class="md-hr">')

  // Links
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')

  // Paragraphs
  html = html.replace(/\n\n+/g, '</p><p class="md-p">')
  html = html.replace(/\n/g, '<br>')
  html = '<p class="md-p">' + html + '</p>'

  // Clean up empty paragraphs
  html = html.replace(/<p class="md-p"><\/p>/g, '')
  html = html.replace(/<p class="md-p">(<h[2-5])/g, '$1')
  html = html.replace(/(<\/h[2-5]>)<\/p>/g, '$1')
  html = html.replace(/<p class="md-p">(<ul|<ol|<blockquote|<pre|<hr)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>|<\/pre>)<\/p>/g, '$1')

  // Clean up <br> tags around block elements
  html = html.replace(/<br>\s*(<ul|<ol|<blockquote)/g, '$1')
  html = html.replace(/(<\/ul>|<\/ol>|<\/blockquote>)\s*<br>/g, '$1')
  html = html.replace(/<p class="md-p">(<br>\s*)+(<ul|<ol|<blockquote|<pre|<hr)/g, '$2')
  html = html.replace(/(<\/ol>|<\/ul>|<\/blockquote>)<br>(<p|<div)/g, '$1$2')

  // Clean up consecutive <br> tags
  html = html.replace(/(<br>\s*){2,}/g, '<br>')

  // ✅ SANITIZE — strip any scripts, event handlers, or dangerous attributes
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'h2', 'h3', 'h4', 'h5',
      'ul', 'ol', 'li', 'pre', 'code', 'blockquote', 'a', 'hr'
    ],
    ALLOWED_ATTR: ['class', 'data-level', 'href', 'target', 'rel'],
    FORCE_BODY: false,
  })
}
