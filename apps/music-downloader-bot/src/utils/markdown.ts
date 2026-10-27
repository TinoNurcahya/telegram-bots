/**
 * Escape special characters for Telegram legacy Markdown (v1) parsing.
 * Characters to escape: _, *, `, [
 */
export function escapeMarkdown(text: string): string {
  if (!text) return '';
  return text.replace(/([_*`\[])/g, '\\$1');
}
