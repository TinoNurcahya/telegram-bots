import { Context, InputFile, InlineKeyboard } from 'grammy';
import { MusicService } from '../../services/music.service.js';
import { LyricsService } from '../../services/lyrics.service.js';
import { UserService } from '../../services/user.service.js';
import { buildPlayerKeyboard, buildLyricsBackKeyboard, buildHdUpsellKeyboard, buildStartKeyboard } from '../keyboards/player.keyboard.js';
import { buildQuotaLimitKeyboard, buildPremiumQuotaLimitKeyboard } from '../keyboards/monetization.keyboard.js';
import { buildChartsCategoryKeyboard, buildChartListKeyboard } from '../keyboards/charts.keyboard.js';
import { escapeMarkdown } from '../../utils/markdown.js';

export function registerMusicHandlers(
  bot: any,
  musicService: MusicService,
  lyricsService: LyricsService,
  userService?: UserService
): void {
  // 1. /start command
  bot.command('start', async (ctx: Context) => {
    const name = ctx.from?.first_name || 'Kawan';
    const userId = ctx.from?.id || 0;
    const match = ctx.match?.toString() || '';

    let referralBanner = '';
    if (userService && match.startsWith('ref_')) {
      const inviterId = parseInt(match.replace('ref_', ''), 10);
      if (!isNaN(inviterId) && inviterId !== userId) {
        const refRes = await userService.processReferral(inviterId, userId);
        if (refRes && refRes.success) {
          referralBanner =
            `🎁 BONUS SAMBUTAN REFERRAL!\n` +
            `Anda bergabung melalui link teman dan mendapatkan +3 Kuota Unduhan Lagu Tambahan!\n` +
            `━━━━━━━━━━━━━━━━━━━━\n\n`;

          try {
            await ctx.api.sendMessage(
              inviterId,
              `🎉 Kawan Anda ${name} baru saja bergabung! Akun Anda mendapatkan +3 Kuota Unduhan Lagu Tambahan!`
            );
          } catch (_) {}
        }
      }
    }

    if (userService) {
      await userService.ensureUser(userId, ctx.from?.username, ctx.from?.first_name);
    }

    const welcome =
      `${referralBanner}` +
      `🎵 Halo ${name}! Selamat datang di Music Discovery & Downloader Bot.\n\n` +
      `Temukan lagu favorit Anda, dengarkan pratinjau audio resmi, telusuri tangga lagu terpopuler, unduh lagu langsung ke chat, dan baca lirik lengkap secara instan!\n\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `🔍 CARA MENCARI LAGU:\n` +
      `Ketik perintah /song diikuti judul lagu, contoh:\n` +
      `/song Coldplay Yellow\n` +
      `/song Tulus Hati Hati di Jalan\n` +
      `/song Adele Easy On Me\n\n` +
      `Anda juga bisa langsung mengetik judul lagu apa saja di chat ini tanpa perintah slash.\n\n` +
      `📈 TANGGA LAGU HITS:\n` +
      `Ketik /charts untuk melihat Top 10 Hits Global dan Indonesia.\n\n` +
      `💖 DUKUNGAN SERVER & KUOTA:\n` +
      `Ketik /profile untuk melihat sisa kuota Anda, atau /upgrade untuk menjadi Supporter VIP!\n\n` +
      `💡 FITUR INLINE QUERY:\n` +
      `Gunakan bot ini di grup atau chat lain: cukup ketik @Musicdownloader2001_bot judul lagu di kolom pesan!`;

    const startKeyboard = buildStartKeyboard(userId, 'Musicdownloader2001_bot');
    await ctx.reply(welcome, { reply_markup: startKeyboard });
  });

  // 2. /help command
  bot.command('help', async (ctx: Context) => {
    const help =
      `📖 PANDUAN PENGGUNAAN BOT MUSIK\n\n` +
      `1. /song <judul> — Cari lagu berdasarkan judul atau nama penyanyi\n` +
      `2. /charts — Lihat tangga lagu Top 10 Global & Indonesia\n` +
      `3. /lyrics <judul> — Cari lirik lagu lengkap & karaoke synced\n` +
      `4. /profile — Cek statistik unduhan & sisa kuota siklus ini\n` +
      `5. /trial — Klaim uji coba gratis VIP 7 hari (1x per akun)\n` +
      `6. /upgrade — Salurkan donasi Stars untuk mendukung server\n` +
      `7. /invite — Ajak teman untuk mendapat bonus kuota +3 lagu\n\n` +
      `Tombol pada kartu lagu:\n` +
      `📥 Unduh (160kbps): Mengirim audio format standar ke chat\n` +
      `💎 Unduh HD (320kbps): Audio jernih kualitas rekaman studio VIP\n` +
      `🎧 Putar Preview: Memutar cuplikan resmi audio 30 detik\n` +
      `📜 Lihat Lirik: Menampilkan lirik lagu dari LRCLIB\n\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `⚖️ DISCLAIMER & HAK CIPTA:\n` +
      `Bot ini tidak menyimpan atau meng-host file audio apa pun di server kami. Seluruh metadata dan audio dialirkan langsung dari CDN publik pihak ketiga untuk tujuan edukasi dan penggunaan wajar (fair use). Seluruh hak cipta lagu sepenuhnya milik artis, komposer, dan label rekaman masing-masing.`;

    await ctx.reply(help);
  });

  // 3. /song command & general text search
  bot.command('song', async (ctx: Context) => {
    const query = ctx.match?.toString().trim();
    if (!query) {
      await ctx.reply('⚠️ Silakan masukkan judul lagu yang ingin dicari, contoh:\n`/song Bohemian Rhapsody`', {
        parse_mode: 'Markdown',
      });
      return;
    }
    await handleSongSearch(ctx, query, musicService);
  });

  // 4. /lyrics command
  bot.command('lyrics', async (ctx: Context) => {
    const query = ctx.match?.toString().trim();
    if (!query) {
      await ctx.reply('⚠️ Silakan masukkan judul lagu untuk mencari lirik, contoh:\n`/lyrics Yellow Coldplay`', {
        parse_mode: 'Markdown',
      });
      return;
    }

    const statusMsg = await ctx.reply('🔎 *Mencari lirik lagu...*', { parse_mode: 'Markdown' });
    try {
      // Split query into track and artist if possible
      const parts = query.split(/[-–—by]/i);
      const trackName = parts[0]?.trim() || query;
      const artistName = parts[1]?.trim() || '';

      const lyrics = await lyricsService.getLyrics(trackName, artistName);
      if (!lyrics || (!lyrics.plainLyrics && !lyrics.syncedLyrics && !lyrics.isInstrumental)) {
        await ctx.api.editMessageText(
          ctx.chat!.id,
          statusMsg.message_id,
          `⚠️ Lirik untuk "${query}" tidak ditemukan di database LRCLIB. Pastikan ejaan judul dan artis benar.`
        );
        return;
      }

      const formatted = lyricsService.formatLyricsDisplay(lyrics);
      await ctx.api.editMessageText(ctx.chat!.id, statusMsg.message_id, formatted, {
        parse_mode: 'Markdown',
      });
    } catch (err) {
      console.error('Lyrics error:', err);
      await ctx.api.editMessageText(
        ctx.chat!.id,
        statusMsg.message_id,
        '⚠️ Terjadi kendala saat mengambil lirik. Silakan coba lagi.'
      );
    }
  });

  // 4b. /charts & /trending commands
  bot.command(['charts', 'trending'], async (ctx: Context) => {
    const text =
      `📈 TANGGA LAGU TERPOPULER (TOP CHARTS)\n\n` +
      `Temukan lagu-lagu hits yang sedang viral dan paling banyak didengarkan secara global maupun di Indonesia!\n\n` +
      `PILIH KATEGORI TANGGA LAGU:`;

    await ctx.reply(text, {
      reply_markup: buildChartsCategoryKeyboard(),
    });
  });

  // 5. Callback query dispatcher
  bot.on('callback_query:data', async (ctx: Context, next: any) => {
    const data = ctx.callbackQuery?.data || '';

    // Only intercept callback queries meant for music & chart navigation
    const isMusicCallback =
      data === 'noop' ||
      data === 'chart:menu' ||
      data === 'charts_cat_global' ||
      data.startsWith('chart:cat:') ||
      data.startsWith('chart:play:') ||
      data.startsWith('dl:') ||
      data.startsWith('nav:') ||
      data.startsWith('prev:') ||
      data.startsWith('lyr:');

    if (!isMusicCallback) {
      return next();
    }

    await ctx.answerCallbackQuery();

    if (data === 'noop') {
      return;
    }

    // Chart Category Menu selector
    if (data === 'chart:menu') {
      const text =
        `📈 TANGGA LAGU TERPOPULER (TOP CHARTS)\n\n` +
        `Temukan lagu-lagu hits yang sedang viral dan paling banyak didengarkan secara global maupun di Indonesia!\n\n` +
        `PILIH KATEGORI TANGGA LAGU:`;

      try {
        await ctx.editMessageText(text, {
          reply_markup: buildChartsCategoryKeyboard(),
        });
      } catch (_) {
        await ctx.reply(text, {
          reply_markup: buildChartsCategoryKeyboard(),
        });
      }
      return;
    }

    // Chart Category Selected (Global or Indonesia)
    if (data === 'charts_cat_global' || data.startsWith('chart:cat:')) {
      const category = (data === 'charts_cat_global' ? 'global' : data.replace('chart:cat:', '')) as 'global' | 'indonesia';
      const categoryTitle = category === 'global' ? '🌍 GLOBAL TOP 10 HITS' : '🇮🇩 INDONESIA TOP 10 VIRAL';

      try {
        await ctx.editMessageText(`⏳ Mengambil data ${categoryTitle}...`);
      } catch (_) {}

      const chartTracks = await musicService.getTopCharts(category, 10);
      if (!chartTracks || chartTracks.length === 0) {
        await ctx.reply(`⚠️ Maaf, gagal mengambil data tangga lagu saat ini. Silakan coba kembali.`);
        return;
      }

      let chartList = `${categoryTitle}\n━━━━━━━━━━━━━━━━━━━━\n\n`;
      chartTracks.forEach((t, i) => {
        chartList += `${i + 1}. ${t.title} — ${t.artist}\n`;
      });
      chartList += `\n🎧 Ketuk nomor lagu di bawah untuk memutar cuplikan, melihat lirik, atau mengunduh audio:`;

      await ctx.reply(chartList, {
        reply_markup: buildChartListKeyboard(chartTracks, category),
      });
      return;
    }

    // Chart Play Selected (Open rich player card for selected chart song)
    if (data.startsWith('chart:play:')) {
      const parts = data.split(':');
      const idx = parseInt(parts[2] || '0', 10);
      const cat = (parts[3] || 'global') as 'global' | 'indonesia';

      const chartTracks = await musicService.getTopCharts(cat, 10);
      const track = chartTracks[idx];
      if (!track) {
        await ctx.reply('⚠️ Data lagu tangga lagu tidak ditemukan. Silakan buka kembali /charts.');
        return;
      }

      const songQuery = `${track.title} ${track.artist}`.trim();
      const caption = formatTrackCaption(track, 0, 1);
      const keyboard = buildPlayerKeyboard(track, songQuery, 0, 1);

      if (track.coverUrl) {
        await ctx.replyWithPhoto(track.coverUrl, {
          caption,
          parse_mode: 'Markdown',
          reply_markup: keyboard,
        });
      } else {
        await ctx.reply(caption, {
          parse_mode: 'Markdown',
          reply_markup: keyboard,
        });
      }
      return;
    }

    let action = '';
    let quality: '160' | '320' = '160';
    let index = 0;
    let query = '';

    const safeDecode = (encoded: string): string => {
      try {
        return decodeURIComponent(encoded);
      } catch (_) {
        return encoded;
      }
    };

    const parts = data.split(':');
    if (parts[0] === 'dl') {
      action = 'dl';
      if (parts.length >= 4) {
        quality = parts[1] === '320' ? '320' : '160';
        index = parseInt(parts[2] || '0', 10);
        query = safeDecode(parts.slice(3).join(':') || '');
      } else {
        // Fallback for dl:index:query
        quality = '160';
        index = parseInt(parts[1] || '0', 10);
        query = safeDecode(parts.slice(2).join(':') || '');
      }
    } else {
      action = parts[0] || '';
      index = parseInt(parts[1] || '0', 10);
      query = safeDecode(parts.slice(2).join(':') || '');
    }

    if (!query) return;

    const tracks = await musicService.searchTracks(query, 5);
    const track = tracks[index];
    if (!track) {
      await ctx.reply('⚠️ Data lagu telah kedaluwarsa. Silakan lakukan pencarian ulang.');
      return;
    }

    // 5a. Navigation (Previous / Next song)
    if (action === 'nav') {
      const caption = formatTrackCaption(track, index, tracks.length);
      const keyboard = buildPlayerKeyboard(track, query, index, tracks.length);

      try {
        if (track.coverUrl) {
          await ctx.editMessageMedia(
            {
              type: 'photo',
              media: track.coverUrl,
              caption: caption,
              parse_mode: 'Markdown',
            },
            { reply_markup: keyboard }
          );
        } else {
          await ctx.editMessageCaption({
            caption: caption,
            parse_mode: 'Markdown',
            reply_markup: keyboard,
          });
        }
      } catch (err) {
        // Fallback: send fresh message if media edit fails
        await ctx.replyWithPhoto(track.coverUrl || 'https://placehold.co/600x600/png?text=Music', {
          caption: caption,
          parse_mode: 'Markdown',
          reply_markup: keyboard,
        });
      }
      return;
    }

    // 5b. Download full track (160kbps Standard or 320kbps Studio HD)
    if (action === 'dl') {
      const userId = ctx.from?.id || 0;

      // 1. Check if 320kbps Studio HD is requested
      if (userService && quality === '320') {
        const profile = await userService.getUserProfile(userId);
        if (!profile.isPremium) {
          // Free user attempting 320kbps -> show educational HD upsell without quota consumption
          const hdUpsellCard =
            `🔒 FITUR EKSKLUSIF: AUDIO STUDIO HD (320KBPS)\n\n` +
            `Audio kualitas HD 320kbps menghadirkan suara jernih berkualitas rekaman studio dengan kedalaman bass dan vokal maksimal.\n\n` +
            `Fitur ini khusus untuk pengguna Premium Pass atau pengguna Free Trial 7 Hari.\n\n` +
            `Pilihan Anda:\n` +
            `1. Aktifkan Free Trial 7 Hari (100% Gratis)\n` +
            `2. Berlangganan mulai dari 25 Telegram Stars (/upgrade)\n` +
            `3. Atau tetap unduh versi standar 160kbps di bawah ini:`;

          await ctx.reply(hdUpsellCard, {
            reply_markup: buildHdUpsellKeyboard(index, query, profile.hasUsedTrial),
          });
          return;
        }
      }

      // 2. Freemium & VIP daily quota gate
      if (userService) {
        const quota = await userService.checkDailyQuota(userId);
        if (!quota.canDownload) {
          const profile = await userService.getUserProfile(userId);

          // VIP quota limit reached
          if (profile.isPremium) {
            const limitNotice =
              `⏳ BATAS KUOTA SIKLUS 12 JAM TERCAPAI (${quota.maxLimit}/${quota.maxLimit} Lagu)\n\n` +
              `Sebagai member VIP, kuota Anda akan kembali di-reset otomatis pada pukul 07:00 WIB / 19:00 WIB (siklus 12 jam).\n\n` +
              `⚡ INGIN LANJUT MENGUNDUH SEKARANG?\n` +
              `Anda dapat menambah kuota unduhan instan tanpa harus menunggu siklus reset:`;

            await ctx.reply(limitNotice, {
              reply_markup: buildPremiumQuotaLimitKeyboard(),
            });
            return;
          }

          // Free user quota limit reached
          const limitNotice =
            `⏳ BATAS UNDUHAN HARIAN TERCAPAI (${quota.maxLimit}/${quota.maxLimit} Lagu Gratis)\n\n` +
            `Anda telah menggunakan seluruh kuota gratis harian Anda (${quota.maxLimit} lagu).\n` +
            `Kuota unduhan akan di-reset otomatis besok pukul 07:00 WIB (00:00 UTC).\n\n` +
            `🌟 FASILITAS PREMIUM PASS:\n` +
            `✨ Unduh hingga 50 lagu per siklus 12 jam (reset 2x sehari)\n` +
            `🎧 Kualitas audio HD 320kbps\n` +
            `📜 Akses lirik dan fitur inline query sepuasnya\n\n` +
            `Upgrade sekarang dengan Telegram Stars (XTR) atau klaim Free Trial 7 Hari!`;

          await ctx.reply(limitNotice, {
            reply_markup: buildQuotaLimitKeyboard(profile.hasUsedTrial),
          });
          return;
        }
      }

      const qualityBadge = quality === '320' ? 'Studio HD (320kbps)' : 'Standar (160kbps)';
      const safeTitle = escapeMarkdown(track.title);
      const safeArtist = escapeMarkdown(track.artist);
      const safeAlbum = escapeMarkdown(track.album);

      const downloadNotice = await ctx.reply(
        `⏳ *Menghubungkan audio stream [${qualityBadge}] untuk:* ${safeTitle} — ${safeArtist}...\nMohon tunggu beberapa detik.`,
        { parse_mode: 'Markdown' }
      );

      // 1. Check audio file_id cache first (Instant delivery without CDN fetch)
      let cachedFileId: string | null = null;
      if (userService) {
        cachedFileId = await userService.getAudioCache(track.id, quality);
      }

      const botUsernameEscaped = ctx.me?.username ? escapeMarkdown(ctx.me.username) : 'Musicdownloader2001\\_bot';

      if (cachedFileId) {
        try {
          const note = quality === '320'
            ? `\n\n💎 *Kualitas:* Studio HD (320kbps) — VIP Member ✨ *(Instant Cloud Cache)*\n🤖 Diunduh via @${botUsernameEscaped}`
            : `\n\n🎧 *Kualitas:* Standar (160kbps) *(Instant Cloud Cache)*\n💡 *Tips:* Mau audio Studio HD 320kbps tanpa kuota? Ketik /upgrade\n🤖 Diunduh via @${botUsernameEscaped}`;

          try {
            await ctx.replyWithAudio(cachedFileId, {
              caption: `🎵 *${safeTitle}*\n🎙️ *${safeArtist}*\n💿 *Album:* ${safeAlbum}${note}`,
              parse_mode: 'Markdown',
            });
          } catch (_) {
            // Fallback for files cached as Telegram documents
            await ctx.replyWithDocument(cachedFileId, {
              caption: `🎵 *${safeTitle}*\n🎙️ *${safeArtist}*\n💿 *Album:* ${safeAlbum}${note}`,
              parse_mode: 'Markdown',
            });
          }

          if (userService) {
            await userService.recordDownload(userId);
          }

          try {
            await ctx.api.deleteMessage(ctx.chat!.id, downloadNotice.message_id);
          } catch (_) {}
          return;
        } catch (cacheErr) {
          console.warn('Failed to send cached audio file_id, falling back to CDN stream:', cacheErr);
        }
      }

      // 2. Fallback to resolving stream URL from CDN
      try {
        const fullStreamUrl = await musicService.resolveFullAudioStream(track.title, track.artist, quality);
        const finalUrl = fullStreamUrl || track.previewUrl;
        const isPreview = !fullStreamUrl && !!track.previewUrl;

        if (!finalUrl) {
          await ctx.api.editMessageText(
            ctx.chat!.id,
            downloadNotice.message_id,
            '⚠️ Maaf, link streaming audio untuk lagu ini sedang tidak tersedia dari penyedia CDN.'
          );
          return;
        }

        let qualityCaption = '';
        if (quality === '320') {
          qualityCaption = `\n\n💎 *Kualitas:* Studio HD (320kbps) — VIP Member ✨\n🤖 Diunduh via @${botUsernameEscaped}`;
        } else {
          qualityCaption = `\n\n🎧 *Kualitas:* Standar (160kbps)\n💡 *Tips:* Mau audio Studio HD 320kbps tanpa kuota? Ketik /upgrade\n🤖 Diunduh via @${botUsernameEscaped}`;
        }

        const note = isPreview
          ? `\n\n*(Tersedia format preview resmi 30s)*\n🤖 Didengarkan via @${botUsernameEscaped}`
          : qualityCaption;

        let thumbnailInput: InputFile | undefined = undefined;
        if (track.coverUrl && track.coverUrl.startsWith('http')) {
          try {
            thumbnailInput = new InputFile(new URL(track.coverUrl));
          } catch (_) {
            thumbnailInput = undefined;
          }
        }

        const sentAudio = await ctx.replyWithAudio(finalUrl, {
          title: track.title,
          performer: track.artist,
          thumbnail: thumbnailInput,
          caption: `🎵 *${safeTitle}*\n🎙️ *${safeArtist}*\n💿 *Album:* ${safeAlbum}${note}`,
          parse_mode: 'Markdown',
        });

        if (userService) {
          await userService.recordDownload(userId);

          // Save newly generated Telegram file_id to cache (supports both audio and document messages)
          const fileId = sentAudio?.audio?.file_id || (sentAudio as any)?.document?.file_id;
          if (!isPreview && fileId) {
            await userService.saveAudioCache(track.id, quality, fileId);
          }
        }

        // Clean up status message
        try {
          await ctx.api.deleteMessage(ctx.chat!.id, downloadNotice.message_id);
        } catch (_) {}
      } catch (err) {
        console.error('Audio stream delivery error:', err);
        const failKeyboard = track.previewUrl
          ? new InlineKeyboard().text('🎧 Putar Preview (30s)', `prev:${index}:${encodeURIComponent(query)}`).row()
          : undefined;

        await ctx.api.editMessageText(
          ctx.chat!.id,
          downloadNotice.message_id,
          '⚠️ Gagal mengalirkan audio lagu penuh ke Telegram. Link CDN mungkin mengalami kendala jaringan atau pembatasan sementara. Anda dapat mencoba mendengarkan cuplikan pratinjau audio 30 detik di bawah ini:',
          { reply_markup: failKeyboard }
        );
      }
      return;
    }

    // 5c. Play 30s preview
    if (action === 'prev') {
      if (!track.previewUrl) {
        await ctx.reply('⚠️ Preview audio tidak tersedia untuk lagu ini.');
        return;
      }

      const safeTitle = escapeMarkdown(track.title);
      const safeArtist = escapeMarkdown(track.artist);
      const botUsernameEscaped = ctx.me?.username ? escapeMarkdown(ctx.me.username) : 'Musicdownloader2001\\_bot';

      let thumbnailInput: InputFile | undefined = undefined;
      if (track.coverUrl && track.coverUrl.startsWith('http')) {
        try {
          thumbnailInput = new InputFile(new URL(track.coverUrl));
        } catch (_) {
          thumbnailInput = undefined;
        }
      }

      await ctx.replyWithAudio(track.previewUrl, {
        title: `${track.title} (Official Preview)`,
        performer: track.artist,
        thumbnail: thumbnailInput,
        caption: `🎧 *Preview Resmi (30 Detik)*\n🎵 *${safeTitle}* — ${safeArtist}\n\n🤖 Didengarkan via @${botUsernameEscaped}`,
        parse_mode: 'Markdown',
      });
      return;
    }

    // 5d. View lyrics
    if (action === 'lyr') {
      const waitMsg = await ctx.reply('📜 *Mengambil lirik lagu...*', { parse_mode: 'Markdown' });
      try {
        const lyrics = await lyricsService.getLyrics(track.title, track.artist);
        if (!lyrics || (!lyrics.plainLyrics && !lyrics.syncedLyrics && !lyrics.isInstrumental)) {
          await ctx.api.editMessageText(
            ctx.chat!.id,
            waitMsg.message_id,
            `⚠️ Lirik untuk "${track.title}" belum tersedia di database LRCLIB.`
          );
          return;
        }

        const formatted = lyricsService.formatLyricsDisplay(lyrics);
        const backKeyboard = buildLyricsBackKeyboard(index, query);

        await ctx.api.editMessageText(ctx.chat!.id, waitMsg.message_id, formatted, {
          parse_mode: 'Markdown',
          reply_markup: backKeyboard,
        });
      } catch (err) {
        console.error('Lyrics callback error:', err);
        await ctx.api.editMessageText(
          ctx.chat!.id,
          waitMsg.message_id,
          '⚠️ Gagal memuat lirik. Silakan coba lagi.'
        );
      }
    }
  });

  // 6. Generic text search (when user types song title directly without /song)
  bot.on('message:text', async (ctx: Context, next: any) => {
    const text = ctx.message?.text?.trim() || '';
    if (text.startsWith('/')) {
      return next(); // Pass through to command handlers
    }
    await handleSongSearch(ctx, text, musicService);
  });
}

/**
 * Common handler for searching and presenting song results.
 */
async function handleSongSearch(ctx: Context, query: string, musicService: MusicService): Promise<void> {
  const safeQuery = escapeMarkdown(query);
  const searchingMsg = await ctx.reply(`🔎 *Mencari:* "${safeQuery}"...`, { parse_mode: 'Markdown' });

  try {
    const tracks = await musicService.searchTracks(query, 5);
    if (!tracks || tracks.length === 0) {
      await ctx.api.editMessageText(
        ctx.chat!.id,
        searchingMsg.message_id,
        `⚠️ Lagu dengan judul "${query}" tidak ditemukan. Coba tambahkan nama penyanyi untuk hasil yang lebih akurat.`
      );
      return;
    }

    const topTrack = tracks[0];
    const caption = formatTrackCaption(topTrack, 0, tracks.length);
    const keyboard = buildPlayerKeyboard(topTrack, query, 0, tracks.length);

    // Send high-resolution album cover photo with caption and buttons
    if (topTrack.coverUrl) {
      await ctx.replyWithPhoto(topTrack.coverUrl, {
        caption: caption,
        parse_mode: 'Markdown',
        reply_markup: keyboard,
      });
      // Delete temporary searching message
      try {
        await ctx.api.deleteMessage(ctx.chat!.id, searchingMsg.message_id);
      } catch (_) {}
    } else {
      await ctx.api.editMessageText(ctx.chat!.id, searchingMsg.message_id, caption, {
        parse_mode: 'Markdown',
        reply_markup: keyboard,
      });
    }
  } catch (err) {
    console.error('Search error:', err);
    await ctx.api.editMessageText(
      ctx.chat!.id,
      searchingMsg.message_id,
      '⚠️ Terjadi kendala saat melakukan pencarian musik. Silakan coba beberapa saat lagi.'
    );
  }
}

/**
 * Format track presentation card caption.
 */
function formatTrackCaption(track: any, index: number, total: number): string {
  const safeTitle = escapeMarkdown(track.title);
  const safeArtist = escapeMarkdown(track.artist);
  const safeAlbum = escapeMarkdown(track.album);

  return (
    `🎵 *HASIL PENCARIAN MUSIK* (${index + 1}/${total})\n` +
    `━━━━━━━━━━━━━━━━━━━━\n` +
    `🎶 *Judul:* ${safeTitle}\n` +
    `🎙️ *Penyanyi:* ${safeArtist}\n` +
    `💿 *Album:* ${safeAlbum}\n` +
    `⏱️ *Durasi:* \`${track.durationFormatted}\`\n\n` +
    `Pilih aksi di bawah untuk memutar atau mengunduh:`
  );
}
