import CryptoJS from 'crypto-js';
import { TrackInfo } from '../types/music.js';

const JIOSAAVN_KEY = '38346591';

export class MusicService {
  /**
   * Format seconds to MM:SS display format.
   */
  public formatDuration(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  /**
   * Search for songs across Deezer catalog with iTunes fallback.
   */
  public async searchTracks(query: string, limit: number = 5): Promise<TrackInfo[]> {
    if (!query || !query.trim()) {
      return [];
    }

    try {
      // 1. Primary Search Provider: Deezer API (Fast, rich metadata, HD covers)
      const deezerUrl = `https://api.deezer.com/search?q=${encodeURIComponent(query.trim())}&limit=${limit}`;
      const response = await fetch(deezerUrl, {
        headers: { 'User-Agent': 'MusicDownloaderBot/1.0' },
        signal: AbortSignal.timeout(6000),
      });

      if (response.ok) {
        const data = (await response.json()) as any;
        if (data && Array.isArray(data.data) && data.data.length > 0) {
          return data.data.map((item: any): TrackInfo => ({
            id: item.id,
            title: item.title_short || item.title || 'Unknown Title',
            artist: item.artist?.name || 'Unknown Artist',
            album: item.album?.title || 'Single',
            duration: item.duration || 0,
            durationFormatted: this.formatDuration(item.duration || 0),
            coverUrl: item.album?.cover_xl || item.album?.cover_big || item.album?.cover_medium || '',
            previewUrl: item.preview || '',
            externalUrl: item.link || '',
            source: 'deezer',
          }));
        }
      }
    } catch (err) {
      console.warn('Deezer search failed, falling back to iTunes:', err);
    }

    // 2. Fallback Search Provider: iTunes Search API
    try {
      const itunesUrl = `https://itunes.apple.com/search?term=${encodeURIComponent(query.trim())}&entity=song&limit=${limit}`;
      const response = await fetch(itunesUrl, {
        headers: { 'User-Agent': 'MusicDownloaderBot/1.0' },
        signal: AbortSignal.timeout(6000),
      });

      if (response.ok) {
        const data = (await response.json()) as any;
        if (data && Array.isArray(data.results)) {
          return data.results.map((item: any): TrackInfo => ({
            id: item.trackId,
            title: item.trackName || 'Unknown Title',
            artist: item.artistName || 'Unknown Artist',
            album: item.collectionName || 'Single',
            duration: Math.round((item.trackTimeMillis || 0) / 1000),
            durationFormatted: this.formatDuration(Math.round((item.trackTimeMillis || 0) / 1000)),
            coverUrl: (item.artworkUrl100 || '').replace('100x100bb', '600x600bb'),
            previewUrl: item.previewUrl || '',
            externalUrl: item.trackViewUrl || '',
            source: 'itunes',
          }));
        }
      }
    } catch (err) {
      console.error('iTunes fallback search failed:', err);
    }

    return [];
  }

  /**
   * Decrypt JioSaavn DES-ECB encrypted media URL.
   */
  public decryptSaavnUrl(encryptedUrl: string): string {
    try {
      const key = CryptoJS.enc.Utf8.parse(JIOSAAVN_KEY);
      const decrypted = CryptoJS.DES.decrypt(
        encryptedUrl,
        key,
        {
          mode: CryptoJS.mode.ECB,
          padding: CryptoJS.pad.Pkcs7,
        }
      );
      const url = decrypted.toString(CryptoJS.enc.Utf8);
      return url || '';
    } catch (e) {
      console.error('Failed to decrypt Saavn URL:', e);
      return '';
    }
  }

  /**
   * Resolve full 320kbps/160kbps audio stream URL for a given song title and artist.
   */
  public async resolveFullAudioStream(
    title: string,
    artist: string,
    quality: '160' | '320' = '160'
  ): Promise<string | null> {
    const query = `${title} ${artist}`.trim();
    const searchUrl = `https://www.jiosaavn.com/api.php?__call=search.getResults&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=3&p=1&q=${encodeURIComponent(query)}`;

    try {
      const res = await fetch(searchUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Accept': 'application/json, text/plain, */*',
        },
        signal: AbortSignal.timeout(8000),
      });

      if (!res.ok) {
        return null;
      }

      const data = (await res.json()) as any;
      const results = data?.results || [];

      for (const item of results) {
        const encrypted = item?.more_info?.encrypted_media_url;
        if (encrypted) {
          const directUrl = this.decryptSaavnUrl(encrypted);
          if (directUrl && directUrl.startsWith('http')) {
            if (quality === '320') {
              // Upgrade to Studio HD 320kbps
              return directUrl.replace(/_(96|160)\.mp4/, '_320.mp4');
            } else {
              // Standard 160kbps
              return directUrl.replace(/_(96|320)\.mp4/, '_160.mp4');
            }
          }
        }
      }
    } catch (err) {
      console.warn('Failed to resolve full audio stream via JioSaavn:', err);
    }

    return null;
  }

  /**
   * Fetch real-time Top Charts (Global or Indonesia).
   */
  public async getTopCharts(category: 'global' | 'indonesia', limit: number = 10): Promise<TrackInfo[]> {
    try {
      if (category === 'global') {
        const deezerChartUrl = `https://api.deezer.com/chart/0/tracks?limit=${limit}`;
        const res = await fetch(deezerChartUrl, {
          headers: { 'User-Agent': 'MusicDownloaderBot/1.0' },
          signal: AbortSignal.timeout(6000),
        });

        if (res.ok) {
          const data = (await res.json()) as any;
          if (data && Array.isArray(data.data)) {
            return data.data.map((item: any): TrackInfo => ({
              id: item.id,
              title: item.title_short || item.title || 'Unknown Title',
              artist: item.artist?.name || 'Unknown Artist',
              album: item.album?.title || 'Global Top Hits',
              duration: item.duration || 0,
              durationFormatted: this.formatDuration(item.duration || 0),
              coverUrl: item.album?.cover_xl || item.album?.cover_big || item.album?.cover_medium || '',
              previewUrl: item.preview || '',
              externalUrl: item.link || '',
              source: 'deezer',
            }));
          }
        }
      } else {
        // Indonesia Top Charts from Apple iTunes RSS Feed
        const itunesIdUrl = `https://itunes.apple.com/id/rss/topsongs/limit=${limit}/json`;
        const res = await fetch(itunesIdUrl, {
          headers: { 'User-Agent': 'MusicDownloaderBot/1.0' },
          signal: AbortSignal.timeout(6000),
        });

        if (res.ok) {
          const data = (await res.json()) as any;
          const entries = data?.feed?.entry;
          if (Array.isArray(entries)) {
            return entries.map((e: any): TrackInfo => {
              const rawId = e.id?.attributes?.['im:id'] || 0;
              const title = e['im:name']?.label || 'Unknown Title';
              const artist = e['im:artist']?.label || 'Unknown Artist';
              const cover = (e['im:image']?.[2]?.label || e['im:image']?.[0]?.label || '').replace(/\/\d+x\d+bb\./, '/600x600bb.');
              const link = e.link?.[0]?.attributes?.href || '';
              const preview = e.link?.[1]?.attributes?.href || '';

              return {
                id: parseInt(rawId, 10) || Math.floor(Math.random() * 100000),
                title,
                artist,
                album: 'Indonesia Top Viral Hits',
                duration: 210,
                durationFormatted: '03:30',
                coverUrl: cover,
                previewUrl: preview,
                externalUrl: link,
                source: 'itunes',
              };
            });
          }
        }
      }
    } catch (err) {
      console.error(`Failed to fetch ${category} top charts:`, err);
    }

    return [];
  }
}
