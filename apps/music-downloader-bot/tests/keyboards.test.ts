import { describe, it, expect } from 'vitest';
import {
  buildPlayerKeyboard,
  buildLyricsBackKeyboard,
  buildHdUpsellKeyboard,
} from '../src/bot/keyboards/player.keyboard.js';
import { TrackInfo } from '../src/types/music.js';

describe('Player Keyboard Unit Tests', () => {
  const sampleTrack: TrackInfo = {
    id: 12345,
    title: 'Yellow',
    artist: 'Coldplay',
    album: 'Parachutes',
    duration: 266,
    durationFormatted: '04:26',
    coverUrl: 'https://example.com/cover.jpg',
    previewUrl: 'https://example.com/preview.mp3',
    externalUrl: 'https://deezer.com/track/12345',
    source: 'deezer',
  };

  it('should generate keyboard with dual 160kbps & 320kbps download buttons, preview, lyrics, and navigation', () => {
    const keyboard = buildPlayerKeyboard(sampleTrack, 'Coldplay', 0, 3);
    const inline = keyboard.inline_keyboard;

    expect(inline.length).toBeGreaterThanOrEqual(4);

    // Row 1: Dual Bitrate Download Buttons (160kbps & 320kbps)
    expect((inline[0][0] as any).text).toContain('160kbps');
    expect((inline[0][0] as any).callback_data).toContain('dl:160:0:Coldplay');
    expect((inline[0][1] as any).text).toContain('320kbps');
    expect((inline[0][1] as any).callback_data).toContain('dl:320:0:Coldplay');

    // Row 2: Preview & Lyrics
    expect((inline[1][0] as any).text).toContain('Putar Preview');
    expect((inline[1][0] as any).callback_data).toContain('prev:0:Coldplay');
    expect((inline[1][1] as any).text).toContain('Lihat Lirik');
    expect((inline[1][1] as any).callback_data).toContain('lyr:0:Coldplay');

    // Row 3: Web Link
    expect((inline[2][0] as any).url).toBe('https://deezer.com/track/12345');

    // Row 4: Pagination (at index 0, Next button should be present)
    const navRow = inline[3];
    expect(navRow.some((b) => b.text.includes('1/3'))).toBe(true);
    expect(navRow.some((b) => b.text.includes('Berikutnya'))).toBe(true);
  });

  it('should build lyrics back button pointing to current track index', () => {
    const backKb = buildLyricsBackKeyboard(2, 'Adele');
    const inline = backKb.inline_keyboard;
    expect(inline.length).toBe(1);
    expect((inline[0][0] as any).text).toContain('Kembali ke Lagu');
    expect((inline[0][0] as any).callback_data).toContain('nav:2:Adele');
  });

  it('should build HD upsell keyboard with trial offer for eligible free users', () => {
    const upsellKb = buildHdUpsellKeyboard(0, 'Coldplay', false);
    const inline = upsellKb.inline_keyboard;

    expect(inline.length).toBe(3);
    expect(inline[0].some((b) => b.text.includes('Free Trial'))).toBe(true);
    expect(inline[0].some((b) => b.text.includes('Stars'))).toBe(true);
    expect((inline[1][0] as any).text).toContain('Tetap Unduh Versi 160kbps');
    expect((inline[1][0] as any).callback_data).toContain('dl:160:0:Coldplay');
  });

  it('should build HD upsell keyboard without trial offer if user already claimed trial', () => {
    const upsellKb = buildHdUpsellKeyboard(1, 'Adele', true);
    const inline = upsellKb.inline_keyboard;

    expect(inline.length).toBe(3);
    expect(inline[0].some((b) => b.text.includes('Free Trial'))).toBe(false);
    expect(inline[0].some((b) => b.text.includes('Stars'))).toBe(true);
    expect((inline[1][0] as any).text).toContain('Tetap Unduh Versi 160kbps');
    expect((inline[1][0] as any).callback_data).toContain('dl:160:1:Adele');
  });

  it('should safely encode long and unicode queries without exceeding 64 bytes or causing URI malformed errors', () => {
    const longJapaneseQuery = '進撃の巨人 The Final Season - 特別の長いタイトルです';
    const kb = buildPlayerKeyboard(sampleTrack, longJapaneseQuery, 0, 1);
    const downloadCb = (kb.inline_keyboard[0][0] as any).callback_data as string;

    // Must be <= 64 bytes (Telegram API limit)
    expect(Buffer.byteLength(downloadCb, 'utf8')).toBeLessThanOrEqual(64);

    // Must decode cleanly without URIError: URI malformed
    const queryPart = downloadCb.split(':')[3];
    expect(() => decodeURIComponent(queryPart)).not.toThrow();
  });
});
