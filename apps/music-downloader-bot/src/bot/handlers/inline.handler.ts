import { Context, InlineKeyboard } from 'grammy';
import type { InlineQueryResult } from 'grammy/types';
import { MusicService } from '../../services/music.service.js';
import { UserService } from '../../services/user.service.js';
import { escapeMarkdown } from '../../utils/markdown.js';

export function registerInlineHandlers(
  bot: any,
  musicService: MusicService,
  userService?: UserService
): void {
  // 1. Handle incoming inline queries (@bot song_title)
  bot.on('inline_query', async (ctx: Context) => {
    const query = ctx.inlineQuery?.query?.trim() || '';
    const userId = ctx.from?.id || 0;
    const botUsername = ctx.me?.username || 'Musicdownloader2001_bot';
    const botUsernameEscaped = escapeMarkdown(botUsername);

    // Empty query -> show helper prompt
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

    // 2. Check user download quota before resolving results
    if (userService && userId > 0) {
      try {
        const quota = await userService.checkDailyQuota(userId);
        if (!quota.canDownload) {
          const isMonthly = quota.limitReason === 'monthly';
          const limitNotice = isMonthly
            ? `Batas kuota bulanan (${quota.usedThisMonth}/${quota.maxMonthlyLimit} lagu) tercapai. Upgrade VIP untuk kuota lebih banyak!`
            : `Batas kuota harian (${quota.maxLimit}/${quota.maxLimit} lagu) tercapai. Reset pukul 07:00 WIB atau upgrade VIP!`;

          const quotaCard: InlineQueryResult = {
            type: 'article',
            id: 'quota_limit_exceeded',
            title: '⏳ Batas Kuota Unduhan Tercapai',
            description: limitNotice,
            input_message_content: {
              message_text:
                `⏳ *BATAS KUOTA UNDUHAN TERCAPAI*\n\n` +
                `${limitNotice}\n\n` +
                `✨ Nikmati kuota lebih besar hingga 15 lagu/hari (150 lagu/bulan) & audio Studio HD 320kbps dengan menjadi VIP Supporter!`,
              parse_mode: 'Markdown',
            },
            reply_markup: new InlineKeyboard()
              .url('🌟 Donasi VIP Stars', `https://t.me/${botUsername}?start=upgrade`)
              .url('🎁 Free Trial 7 Hari', `https://t.me/${botUsername}?start=trial`),
          };

          await ctx.answerInlineQuery([quotaCard], { cache_time: 10 });
          return;
        }
      } catch (err) {
        console.warn('Inline quota check warning:', err);
      }
    }

    // 3. Search song metadata
    try {
      const tracks = await musicService.searchTracks(query, 6);
      if (!tracks || tracks.length === 0) {
        await ctx.answerInlineQuery([], { cache_time: 10 });
        return;
      }

      // 4. Build Hybrid results: Cache first, JioSaavn fast stream second, Deep-link card fallback
      const results: InlineQueryResult[] = await Promise.all(
        tracks.map(async (track, i) => {
          const cleanTitle = musicService.sanitizeTitle(track.title);
          const cleanArtist = musicService.sanitizeArtist(track.artist);
          const safeTitle = escapeMarkdown(track.title);
          const safeArtist = escapeMarkdown(track.artist);
          const safeAlbum = escapeMarkdown(track.album);

          const defaultMarkup = new InlineKeyboard()
            .switchInlineCurrent('🔍 Cari Lagu Lain', `${cleanTitle}`)
            .url('🤖 Buka Bot', `https://t.me/${botUsername}`);

          const audioCaption =
            `🎵 *${safeTitle}*\n` +
            `🎙️ *${safeArtist}*\n` +
            `💿 *Album:* ${safeAlbum} (\`${track.durationFormatted}\`)\n\n` +
            `🤖 Diunduh via @${botUsernameEscaped}`;

          // Option A: Check Telegram Cloud Audio Cache (Instant full track)
          let cachedFileId: string | null = null;
          if (userService) {
            try {
              cachedFileId = await userService.getAudioCache(track.id, '160', track.title, track.artist);
            } catch (_) {}
          }

          if (cachedFileId) {
            return {
              type: 'audio',
              id: `audio_cached_${track.id}_${i}`,
              audio_file_id: cachedFileId,
              caption: audioCaption,
              parse_mode: 'Markdown',
              reply_markup: defaultMarkup,
            };
          }

          // Option B: Fast JioSaavn stream resolution for direct full song MP3
          let saavnUrl: string | null = null;
          try {
            saavnUrl = await musicService.resolveViaJioSaavn(cleanTitle, cleanArtist, '160');
          } catch (_) {}

          if (saavnUrl) {
            return {
              type: 'audio',
              id: `audio_saavn_${track.id}_${i}`,
              audio_url: saavnUrl,
              title: track.title,
              performer: track.artist,
              audio_duration: track.duration,
              caption: audioCaption,
              parse_mode: 'Markdown',
              reply_markup: defaultMarkup,
            };
          }

          // Option C: Article Card with Deep-Link to Private Chat for high-quality audio / YouTube download
          const deepLinkUrl = `https://t.me/${botUsername}?start=dl_${track.id}`;
          const cardMarkup = new InlineKeyboard()
            .url('📥 Unduh Lagu Full (MP3)', deepLinkUrl)
            .row()
            .switchInlineCurrent('🔍 Cari Lagu Lain', `${cleanTitle}`);

          return {
            type: 'article',
            id: `article_dl_${track.id}_${i}`,
            title: `${track.title} — ${track.artist}`,
            description: `💿 Album: ${track.album} • ⏱️ ${track.durationFormatted} • Ketuk untuk unduh Full`,
            thumbnail_url: track.coverUrl || undefined,
            input_message_content: {
              message_text:
                `🎵 *${safeTitle}*\n` +
                `🎙️ *${safeArtist}*\n` +
                `💿 *Album:* ${safeAlbum} (\`${track.durationFormatted}\`)\n\n` +
                `✨ *Kualitas Audio:* Standar (160kbps) & Studio HD (320kbps)\n` +
                `📥 Ketuk tombol di bawah untuk mengunduh lagu full:`,
              parse_mode: 'Markdown',
            },
            reply_markup: cardMarkup,
          };
        })
      );

      await ctx.answerInlineQuery(results, {
        cache_time: 300,
      });
    } catch (err) {
      console.error('Inline query error:', err);
      await ctx.answerInlineQuery([], { cache_time: 10 });
    }
  });

  // 2. Handle chosen inline result to deduct quota when user sends an audio
  bot.on('chosen_inline_result', async (ctx: Context) => {
    const resultId = ctx.chosenInlineResult?.result_id || '';
    const userId = ctx.from?.id || 0;
    if (!userId || !userService) return;

    // Deduct quota only when a full audio was dispatched
    if (resultId.startsWith('audio_')) {
      try {
        await userService.recordDownload(userId);
      } catch (err) {
        console.warn('Failed to record download from chosen_inline_result:', err);
      }
    }
  });
}
