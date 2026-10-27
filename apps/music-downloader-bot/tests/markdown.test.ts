import { describe, it, expect } from 'vitest';
import { escapeMarkdown } from '../src/utils/markdown.js';

describe('Markdown Sanitizer Unit Tests', () => {
  it('should escape underscore characters to prevent italic parsing errors', () => {
    expect(escapeMarkdown('song_title_remix')).toBe('song\\_title\\_remix');
  });

  it('should escape asterisk characters to prevent bold parsing errors', () => {
    expect(escapeMarkdown('Star * Band *')).toBe('Star \\* Band \\*');
  });

  it('should escape square brackets to prevent broken link entities', () => {
    expect(escapeMarkdown('Song [Official Video]')).toBe('Song \\[Official Video]');
  });

  it('should escape backtick characters to prevent broken code blocks', () => {
    expect(escapeMarkdown('Track `2024`')).toBe('Track \\`2024\\`');
  });

  it('should return empty string if input is empty or null', () => {
    expect(escapeMarkdown('')).toBe('');
    expect(escapeMarkdown((null as unknown) as string)).toBe('');
  });

  it('should leave normal strings unchanged', () => {
    expect(escapeMarkdown('Coldplay - Yellow')).toBe('Coldplay - Yellow');
  });
});
