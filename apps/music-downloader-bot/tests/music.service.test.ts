import { describe, it, expect } from 'vitest';
import { MusicService } from '../src/services/music.service.js';

describe('MusicService Unit Tests', () => {
  const musicService = new MusicService();

  it('should format duration in seconds to MM:SS correctly', () => {
    expect(musicService.formatDuration(0)).toBe('00:00');
    expect(musicService.formatDuration(59)).toBe('00:59');
    expect(musicService.formatDuration(60)).toBe('01:00');
    expect(musicService.formatDuration(215)).toBe('03:35');
    expect(musicService.formatDuration(3600)).toBe('60:00');
  });

  it('should decrypt JioSaavn DES-ECB encrypted media URL correctly', () => {
    // Known sample encrypted string from JioSaavn API
    const sampleEnc = 'ID2ieOjCrwfgWvL5sXl4B1ImC5QfbsDyQsDtuvz6EyDcBfL2BM2Nwm+Gkc6P0HOFOYDAF5HEhhIAyhjGcPng6Bw7tS9a8Gtq';
    const decrypted = musicService.decryptSaavnUrl(sampleEnc);
    expect(decrypted).toBeTruthy();
    expect(decrypted).toContain('https://');
    expect(decrypted).toContain('.mp4');
  });

  it('should search tracks and return structured metadata from Deezer', async () => {
    const tracks = await musicService.searchTracks('Coldplay Yellow', 3);
    expect(Array.isArray(tracks)).toBe(true);
    expect(tracks.length).toBeGreaterThan(0);

    const top = tracks[0];
    expect(top.title).toBeTruthy();
    expect(top.artist.toLowerCase()).toContain('coldplay');
    expect(top.duration).toBeGreaterThan(0);
    expect(top.durationFormatted).toMatch(/^\d{2}:\d{2}$/);
    expect(top.coverUrl).toBeTruthy();
    expect(top.previewUrl).toContain('https://');
  });

  it('should return empty array for empty search query', async () => {
    const tracks = await musicService.searchTracks('', 5);
    expect(tracks).toEqual([]);
  });

  it('should replace encrypted media URL bitrates correctly for 160 and 320 qualities', () => {
    const sampleEnc = 'ID2ieOjCrwfgWvL5sXl4B1ImC5QfbsDyQsDtuvz6EyDcBfL2BM2Nwm+Gkc6P0HOFOYDAF5HEhhIAyhjGcPng6Bw7tS9a8Gtq';
    const decrypted = musicService.decryptSaavnUrl(sampleEnc);
    expect(decrypted).toBeTruthy();

    const q160 = decrypted.replace(/_(96|320)\.mp4/, '_160.mp4');
    expect(q160).toContain('_160.mp4');

    const q320 = decrypted.replace(/_(96|160)\.mp4/, '_320.mp4');
    expect(q320).toContain('_320.mp4');
  });

  it('should sanitize song titles by stripping promotional brackets and artifacts', () => {
    expect(musicService.sanitizeTitle('Yellow (Live in Buenos Aires)')).toBe('Yellow');
    expect(musicService.sanitizeTitle('Die With A Smile (with Bruno Mars)')).toBe('Die With A Smile');
    expect(musicService.sanitizeTitle('Bohemian Rhapsody (2011 Remaster)')).toBe('Bohemian Rhapsody');
    expect(musicService.sanitizeTitle('Hati-Hati di Jalan')).toBe('Hati Hati di Jalan');
    expect(musicService.sanitizeTitle('Something Just Like This [Official Lyric Video]')).toBe('Something Just Like This');
  });

  it('should sanitize artist names by stripping featured credits', () => {
    expect(musicService.sanitizeArtist('Coldplay feat. BTS')).toBe('Coldplay');
    expect(musicService.sanitizeArtist('Lady Gaga, Bruno Mars')).toBe('Lady Gaga');
    expect(musicService.sanitizeArtist('Tulus')).toBe('Tulus');
  });

  it('should return null when external resolver URL is not configured or empty', async () => {
    const serviceWithoutResolver = new MusicService('');
    const resolved = await serviceWithoutResolver.resolveViaExternalResolver('Test Song', 'Test Artist');
    expect(resolved).toBeNull();
  });
});
