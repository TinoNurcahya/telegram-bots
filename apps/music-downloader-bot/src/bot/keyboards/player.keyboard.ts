import { InlineKeyboard } from 'grammy';
import { TrackInfo } from '../../types/music.js';

/**
 * Safely encode query payload guaranteeing it never exceeds byte limits or corrupts percent encoding.
 */
function safeQueryPayload(query: string, maxBytes: number = 45): string {
  if (!query) return '';
  const trimmed = query.trim();
  let encoded = encodeURIComponent(trimmed);
  if (Buffer.byteLength(encoded, 'utf8') <= maxBytes) {
    return encoded;
  }

  // Truncate character-by-character before encoding to ensure complete UTF-8 sequences
  let len = trimmed.length;
  while (len > 0) {
    len--;
    encoded = encodeURIComponent(trimmed.slice(0, len));
    if (Buffer.byteLength(encoded, 'utf8') <= maxBytes) {
      return encoded;
    }
  }
  return '';
}

/**
 * Build interactive player, download, and pagination keyboard for a song result.
 */
export function buildPlayerKeyboard(
  track: TrackInfo,
  query: string,
  currentIndex: number,
  totalTracks: number
): InlineKeyboard {
  const keyboard = new InlineKeyboard();
  const q = safeQueryPayload(query);

  // Row 1: Dual Bitrate Download Buttons (160kbps Standard vs 320kbps Studio HD)
  keyboard
    .text('📥 Unduh (160kbps)', `dl:160:${currentIndex}:${q}`)
    .text('💎 Unduh HD (320kbps)', `dl:320:${currentIndex}:${q}`)
    .row();

  // Row 2: Preview & Lyrics
  keyboard
    .text('🎧 Putar Preview (30s)', `prev:${currentIndex}:${q}`)
    .text('📜 Lihat Lirik', `lyr:${currentIndex}:${q}`)
    .row();

  // Row 3: Web link if available
  if (track.externalUrl && track.externalUrl.startsWith('http')) {
    keyboard.url('🌐 Buka di Web', track.externalUrl).row();
  }

  // Row 4: Navigation buttons if multiple results exist
  if (totalTracks > 1) {
    if (currentIndex > 0) {
      keyboard.text('⬅️ Sebelumnya', `nav:${currentIndex - 1}:${q}`);
    }

    keyboard.text(`🎵 ${currentIndex + 1}/${totalTracks}`, `noop`);

    if (currentIndex < totalTracks - 1) {
      keyboard.text('Berikutnya ➡️', `nav:${currentIndex + 1}:${q}`);
    }
  }

  return keyboard;
}

/**
 * Build back keyboard when viewing lyrics.
 */
export function buildLyricsBackKeyboard(currentIndex: number, query: string): InlineKeyboard {
  const q = safeQueryPayload(query);
  return new InlineKeyboard().text('⬅️ Kembali ke Lagu', `nav:${currentIndex}:${q}`);
}

/**
 * Build educational upsell keyboard for Free users attempting to download 320kbps HD audio.
 */
export function buildHdUpsellKeyboard(
  currentIndex: number,
  query: string,
  hasUsedTrial: boolean
): InlineKeyboard {
  const keyboard = new InlineKeyboard();
  const q = safeQueryPayload(query);

  if (!hasUsedTrial) {
    keyboard
      .text('🎁 Klaim Free Trial 7 Hari', 'claim_trial_7d')
      .text('💎 Beli Stars', 'show_upgrade_menu')
      .row();
  } else {
    keyboard.text('💎 Berlangganan Stars (/upgrade)', 'show_upgrade_menu').row();
  }

  keyboard
    .text('📥 Tetap Unduh Versi 160kbps', `dl:160:${currentIndex}:${q}`)
    .row();

  keyboard.text('⬅️ Kembali ke Lagu', `nav:${currentIndex}:${q}`);

  return keyboard;
}

/**
 * Build interactive start and quick access keyboard for /start command.
 */
export function buildStartKeyboard(
  userId: number,
  botUsername: string = 'Musicdownloader2001_bot'
): InlineKeyboard {
  const shareText = encodeURIComponent(
    '🎵 Cari dan unduh lagu favoritmu langsung di Telegram dengan audio kualitas studio!'
  );
  const inviteLink = `https://t.me/${botUsername}?start=ref_${userId}`;
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${shareText}`;

  return new InlineKeyboard()
    .switchInline('🔍 Cari di Chat Lain', '')
    .row()
    .text('📈 Top 10 Charts', 'charts_cat_global')
    .row()
    .url('👥 Ajak Teman (+3 Lagu)', shareUrl);
}
