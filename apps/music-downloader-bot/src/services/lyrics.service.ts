import { LyricsResult } from '../types/music.js';
import { escapeMarkdown } from '../utils/markdown.js';

export class LyricsService {
  /**
   * Fetch song lyrics (plain & synced) using LRCLIB API.
   */
  public async getLyrics(trackName: string, artistName: string): Promise<LyricsResult | null> {
    if (!trackName) return null;

    // 1. Direct match endpoint
    try {
      const directUrl = `https://lrclib.net/api/get?track_name=${encodeURIComponent(trackName)}&artist_name=${encodeURIComponent(artistName)}`;
      const res = await fetch(directUrl, {
        headers: {
          'User-Agent': 'MusicDownloaderBot/1.0 (https://github.com/TinoNurcahya/telegram-bots)',
        },
        signal: AbortSignal.timeout(6000),
      });

      if (res.ok) {
        const data = (await res.json()) as any;
        if (data && (data.plainLyrics || data.syncedLyrics)) {
          return {
            trackName: data.trackName || trackName,
            artistName: data.artistName || artistName,
            albumName: data.albumName,
            duration: data.duration,
            plainLyrics: data.plainLyrics || undefined,
            syncedLyrics: data.syncedLyrics || undefined,
            isInstrumental: data.instrumental || false,
          };
        }
      }
    } catch (err) {
      console.warn('LRCLIB direct fetch error:', err);
    }

    // 2. Fallback search query endpoint
    try {
      const searchUrl = `https://lrclib.net/api/search?q=${encodeURIComponent(`${trackName} ${artistName}`.trim())}`;
      const res = await fetch(searchUrl, {
        headers: {
          'User-Agent': 'MusicDownloaderBot/1.0 (https://github.com/TinoNurcahya/telegram-bots)',
        },
        signal: AbortSignal.timeout(6000),
      });

      if (res.ok) {
        const items = (await res.json()) as any[];
        if (Array.isArray(items) && items.length > 0) {
          const top = items[0];
          if (top.plainLyrics || top.syncedLyrics) {
            return {
              trackName: top.trackName || trackName,
              artistName: top.artistName || artistName,
              albumName: top.albumName,
              duration: top.duration,
              plainLyrics: top.plainLyrics || undefined,
              syncedLyrics: top.syncedLyrics || undefined,
              isInstrumental: top.instrumental || false,
            };
          }
        }
      }
    } catch (err) {
      console.warn('LRCLIB search fallback error:', err);
    }

    return null;
  }

  /**
   * Format lyrics for display in Telegram, truncating or splitting if too long.
   */
  public formatLyricsDisplay(lyrics: LyricsResult): string {
    const safeTitle = escapeMarkdown(lyrics.trackName);
    const safeArtist = escapeMarkdown(lyrics.artistName);

    if (lyrics.isInstrumental) {
      return `🎶 *${safeTitle}* — ${safeArtist}\n\n*(Lagu ini adalah karya instrumental tanpa lirik vokal)*`;
    }

    const text = escapeMarkdown(lyrics.plainLyrics || 'Lirik teks tidak ditemukan.');
    const header = `📜 *Lirik Lagu: ${safeTitle}*\n🎙️ *Artis:* ${safeArtist}\n━━━━━━━━━━━━━━━━━━━━\n\n`;

    // Telegram message limit is 4096 characters
    const maxBodyLen = 4096 - header.length - 50;
    if (text.length > maxBodyLen) {
      return header + text.slice(0, maxBodyLen) + '\n\n...(lirik terpotong karena batas panjang pesan Telegram)';
    }

    return header + text;
  }
}
