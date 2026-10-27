import { describe, it, expect } from 'vitest';
import {
  buildChartsCategoryKeyboard,
  buildChartListKeyboard,
} from '../src/bot/keyboards/charts.keyboard.js';
import { MusicService } from '../src/services/music.service.js';
import { TrackInfo } from '../src/types/music.js';

describe('Top Charts & Trending Keyboards and Service Tests', () => {
  const musicService = new MusicService();

  const dummyChartTracks: TrackInfo[] = Array.from({ length: 10 }, (_, i) => ({
    id: 1000 + i,
    title: `Hit Track ${i + 1}`,
    artist: `Artist ${i + 1}`,
    album: 'Chart Compilation',
    duration: 200,
    durationFormatted: '03:20',
    coverUrl: `https://example.com/cover_${i + 1}.jpg`,
    previewUrl: `https://example.com/preview_${i + 1}.mp3`,
    externalUrl: `https://example.com/track_${i + 1}`,
    source: 'deezer',
  }));

  it('should build category selection keyboard with Global and Indonesia options', () => {
    const kb = buildChartsCategoryKeyboard();
    const inline = kb.inline_keyboard;

    expect(inline.length).toBe(2);
    expect((inline[0][0] as any).text).toContain('Global Top 10');
    expect((inline[0][0] as any).callback_data).toBe('chart:cat:global');
    expect((inline[1][0] as any).text).toContain('Indonesia Top 10');
    expect((inline[1][0] as any).callback_data).toBe('chart:cat:indonesia');
  });

  it('should build 10 interactive song number buttons in 2 rows of 5 with change category button', () => {
    const kb = buildChartListKeyboard(dummyChartTracks, 'global');
    const inline = kb.inline_keyboard;

    expect(inline.length).toBe(3); // Row 1 (1-5), Row 2 (6-10), Row 3 (Menu)

    // Row 1: buttons 1 to 5
    expect(inline[0].length).toBe(5);
    expect((inline[0][0] as any).text).toBe('[ 1 ]');
    expect((inline[0][0] as any).callback_data).toBe('chart:play:0:global');
    expect((inline[0][4] as any).text).toBe('[ 5 ]');
    expect((inline[0][4] as any).callback_data).toBe('chart:play:4:global');

    // Row 2: buttons 6 to 10
    expect(inline[1].length).toBe(5);
    expect((inline[1][0] as any).text).toBe('[ 6 ]');
    expect((inline[1][0] as any).callback_data).toBe('chart:play:5:global');
    expect((inline[1][4] as any).text).toBe('[ 10 ]');
    expect((inline[1][4] as any).callback_data).toBe('chart:play:9:global');

    // Row 3: Return to category menu
    expect((inline[2][0] as any).text).toContain('Ganti Kategori');
    expect((inline[2][0] as any).callback_data).toBe('chart:menu');
  });

  it('should fetch real-time Global Top Charts from Deezer Chart API', async () => {
    const tracks = await musicService.getTopCharts('global', 5);
    expect(Array.isArray(tracks)).toBe(true);
    expect(tracks.length).toBeGreaterThan(0);

    const first = tracks[0];
    expect(first.title).toBeTruthy();
    expect(first.artist).toBeTruthy();
    expect(first.source).toBe('deezer');
  });

  it('should fetch real-time Indonesia Top Charts from Apple iTunes RSS', async () => {
    const tracks = await musicService.getTopCharts('indonesia', 5);
    expect(Array.isArray(tracks)).toBe(true);
    expect(tracks.length).toBeGreaterThan(0);

    const first = tracks[0];
    expect(first.title).toBeTruthy();
    expect(first.artist).toBeTruthy();
    expect(first.source).toBe('itunes');
  });
});
