import CryptoJS from 'crypto-js';
import { TrackInfo } from '../types/music.js';

const JIOSAAVN_KEY = '38346591';

export class MusicService {
  constructor(private readonly streamResolverUrl: string = '') {}

  /**
   * Clean titles by removing promotional or metadata artifacts (feat, live, remaster, official, etc.)
   */
  public sanitizeTitle(title: string): string {
    if (!title) return '';
    return title
      .replace(/\s*[\(\[][^\)\]]*(?:feat\.?|ft\.?|featuring|with|prod\.?|official|video|audio|lyric|lyrics|remaster|live|radio edit|deluxe|version)[^\)\]]*[\)\]]/gi, '')
      .replace(/[-–—|/\\#]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Clean artist names by removing secondary artists or featured credits.
   */
  public sanitizeArtist(artist: string): string {
    if (!artist) return '';
    return artist
      .replace(/\s*(?:feat\.?|ft\.?|featuring|with|,|&|\+).*$/i, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

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
   * Resolve audio stream via JioSaavn with title/artist match verification.
   */
  public async resolveViaJioSaavn(
    cleanTitle: string,
    cleanArtist: string,
    quality: '160' | '320' = '160'
  ): Promise<string | null> {
    const queries = [
      `${cleanTitle} ${cleanArtist}`.trim(),
      cleanTitle,
    ];

    for (const q of queries) {
      if (!q) continue;
      const searchUrl = `https://www.jiosaavn.com/api.php?__call=search.getResults&_format=json&_marker=0&api_version=4&ctx=web6dot0&n=5&p=1&q=${encodeURIComponent(q)}`;

      try {
        const res = await fetch(searchUrl, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
          },
          signal: AbortSignal.timeout(6000),
        });

        if (!res.ok) continue;

        const data = (await res.json()) as any;
        const results = data?.results || [];
        if (!Array.isArray(results) || results.length === 0) continue;

        const targetWords = cleanTitle.toLowerCase().split(/\s+/).filter((w) => w.length >= 3);

        for (const item of results) {
          const itemTitle = (item.title || '').toLowerCase();
          const isTitleMatch = targetWords.length > 0
            ? targetWords.some((w) => itemTitle.includes(w))
            : itemTitle.includes(cleanTitle.toLowerCase());

          if (!isTitleMatch) {
            continue;
          }

          const encrypted = item?.more_info?.encrypted_media_url;
          if (encrypted) {
            const directUrl = this.decryptSaavnUrl(encrypted);
            if (directUrl && directUrl.startsWith('http')) {
              if (quality === '320') {
                return directUrl.replace(/_(96|160)\.mp4/, '_320.mp4');
              } else {
                return directUrl.replace(/_(96|320)\.mp4/, '_160.mp4');
              }
            }
          }
        }
      } catch (err) {
        console.warn(`JioSaavn query attempt for "${q}" failed:`, err);
      }
    }

    return null;
  }

  /**
   * Resolve audio stream via External Audio Stream Resolver (configured via STREAM_RESOLVER_URL).
   */
  public async resolveViaExternalResolver(
    cleanTitle: string,
    cleanArtist: string,
    quality: '160' | '320' = '160'
  ): Promise<string | null> {
    if (!this.streamResolverUrl) {
      return null;
    }

    try {
      const base = this.streamResolverUrl.replace(/\/+$/, '');
      const query = `${cleanTitle} ${cleanArtist}`.trim();
      const url = `${base}?q=${encodeURIComponent(query)}&title=${encodeURIComponent(cleanTitle)}&artist=${encodeURIComponent(cleanArtist)}&quality=${quality}`;

      const res = await fetch(url, {
        headers: {
          'Accept': 'application/json, text/plain, */*',
          'User-Agent': 'MusicDownloaderBot/1.0',
        },
        signal: AbortSignal.timeout(10000),
      });

      if (!res.ok) {
        return null;
      }

      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        const data = (await res.json()) as any;
        const streamUrl = data?.url || data?.downloadUrl || data?.streamUrl || data?.link || data?.audioUrl;
        if (typeof streamUrl === 'string' && streamUrl.startsWith('http')) {
          return streamUrl;
        }
      } else {
        const text = (await res.text()).trim();
        if (text.startsWith('http')) {
          return text;
        }
      }
    } catch (err) {
      console.warn('External stream resolver error:', err);
    }

    return null;
  }

  /**
   * Resolve full 320kbps/160kbps audio stream URL using multi-provider hybrid pipeline.
   * Priority:
   * 1. JioSaavn (Fast, high-quality direct CDN if matched)
   * 2. External Audio Stream Resolver (if STREAM_RESOLVER_URL is configured)
   */
  public async resolveFullAudioStream(
    title: string,
    artist: string,
    quality: '160' | '320' = '160'
  ): Promise<string | null> {
    const cleanTitle = this.sanitizeTitle(title);
    const cleanArtist = this.sanitizeArtist(artist);

    // 1. Primary: JioSaavn
    try {
      const saavnUrl = await this.resolveViaJioSaavn(cleanTitle, cleanArtist, quality);
      if (saavnUrl) {
        return saavnUrl;
      }
    } catch (err) {
      console.warn('JioSaavn stream resolution failed:', err);
    }

    // 2. Secondary: External Audio Stream Resolver
    if (this.streamResolverUrl) {
      try {
        const externalUrl = await this.resolveViaExternalResolver(cleanTitle, cleanArtist, quality);
        if (externalUrl) {
          return externalUrl;
        }
      } catch (err) {
        console.warn('External resolver resolution failed:', err);
      }
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
