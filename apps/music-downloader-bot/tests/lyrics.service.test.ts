import { describe, it, expect } from 'vitest';
import { LyricsService } from '../src/services/lyrics.service.js';

describe('LyricsService Unit Tests', () => {
  const lyricsService = new LyricsService();

  it('should fetch plain and synced lyrics for known songs from LRCLIB', async () => {
    const result = await lyricsService.getLyrics('Yellow', 'Coldplay');
    expect(result).not.toBeNull();
    if (result) {
      expect(result.trackName.toLowerCase()).toContain('yellow');
      expect(result.artistName.toLowerCase()).toContain('coldplay');
      expect(result.plainLyrics).toBeTruthy();
      expect(result.plainLyrics?.toLowerCase()).toContain('look at the stars');
    }
  });

  it('should return null for non-existent track', async () => {
    const result = await lyricsService.getLyrics('xyz_non_existent_random_song_123456', 'fake_artist_999');
    expect(result).toBeNull();
  });

  it('should format lyrics display safely under Telegram character limit', () => {
    const mockLyrics = {
      trackName: 'Test Song',
      artistName: 'Test Artist',
      plainLyrics: 'Line 1\nLine 2\nLine 3',
    };

    const formatted = lyricsService.formatLyricsDisplay(mockLyrics);
    expect(formatted).toContain('Lirik Lagu: Test Song');
    expect(formatted).toContain('Test Artist');
    expect(formatted).toContain('Line 1');
    expect(formatted.length).toBeLessThan(4096);
  });

  it('should handle instrumental track gracefully', () => {
    const mockInstrumental = {
      trackName: 'Interlude',
      artistName: 'Orchestra',
      isInstrumental: true,
    };

    const formatted = lyricsService.formatLyricsDisplay(mockInstrumental);
    expect(formatted).toContain('karya instrumental tanpa lirik');
  });
});
