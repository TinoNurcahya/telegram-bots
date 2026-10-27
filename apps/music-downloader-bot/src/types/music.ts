export interface TrackInfo {
  id: string | number;
  title: string;
  artist: string;
  album: string;
  duration: number; // Duration in seconds
  durationFormatted: string; // "MM:SS"
  coverUrl: string; // High-resolution cover artwork URL
  previewUrl: string; // Direct MP3/AAC audio stream URL (30s official preview)
  downloadUrl?: string; // Full audio stream URL if resolved
  externalUrl?: string; // Official web link (Deezer, iTunes, etc.)
  source: 'deezer' | 'itunes' | 'saavn';
}

export interface LyricsResult {
  trackName: string;
  artistName: string;
  albumName?: string;
  duration?: number;
  plainLyrics?: string;
  syncedLyrics?: string;
  isInstrumental?: boolean;
}

export interface SearchResult {
  query: string;
  total: number;
  tracks: TrackInfo[];
}
