import { InlineKeyboard } from 'grammy';
import { TrackInfo } from '../../types/music.js';

/**
 * Build category selection keyboard for Top Charts.
 */
export function buildChartsCategoryKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text('🌍 Global Top 10 Hits', 'chart:cat:global')
    .row()
    .text('🇮🇩 Indonesia Top 10 Viral', 'chart:cat:indonesia');
}

/**
 * Build interactive number button keyboard for exploring top chart songs.
 */
export function buildChartListKeyboard(
  tracks: TrackInfo[],
  category: 'global' | 'indonesia'
): InlineKeyboard {
  const keyboard = new InlineKeyboard();

  // Row 1: Songs 1 to 5
  for (let i = 0; i < Math.min(5, tracks.length); i++) {
    keyboard.text(`[ ${i + 1} ]`, `chart:play:${i}:${category}`);
  }
  keyboard.row();

  // Row 2: Songs 6 to 10
  if (tracks.length > 5) {
    for (let i = 5; i < Math.min(10, tracks.length); i++) {
      keyboard.text(`[ ${i + 1} ]`, `chart:play:${i}:${category}`);
    }
    keyboard.row();
  }

  // Row 3: Back to category menu
  keyboard.text('🔄 Ganti Kategori Tangga Lagu', 'chart:menu');

  return keyboard;
}
