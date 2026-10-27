import { Context } from 'grammy';
import type { InlineQueryResult } from 'grammy/types';
import { MusicService } from '../../services/music.service.js';

export function registerInlineHandlers(bot: any, musicService: MusicService): void {
  bot.on('inline_query', async (ctx: Context) => {
    const query = ctx.inlineQuery?.query?.trim() || '';
    if (!query) {
      await ctx.answerInlineQuery([], {
        cache_time: 10,
        button: {
          text: '🔍 Ketik judul lagu yang ingin dicari...',
          start_parameter: 'inline_help',
        },
      });
      return;
    }

    try {
      const tracks = await musicService.searchTracks(query, 8);
      const results: InlineQueryResult[] = tracks.map((track, i) => {
        // Use audio preview or article result
        return {
          type: 'audio',
          id: `track_${track.id}_${i}`,
          audio_url: track.previewUrl || 'https://cdnt-preview.dzcdn.net/api/1/1/6/4/f/0/64f36083ad5a11e6803ef7ddbcdaf898.mp3',
          title: track.title,
          performer: track.artist,
          audio_duration: track.duration,
          caption: `🎵 *${track.title}* — ${track.artist}\n💿 Album: ${track.album} (\`${track.durationFormatted}\`)`,
          parse_mode: 'Markdown',
        };
      });

      await ctx.answerInlineQuery(results, {
        cache_time: 300,
      });
    } catch (err) {
      console.error('Inline query error:', err);
      await ctx.answerInlineQuery([], { cache_time: 10 });
    }
  });
}
