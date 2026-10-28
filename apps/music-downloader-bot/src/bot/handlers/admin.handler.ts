import { Context } from 'grammy';
import { UserService } from '../../services/user.service.js';
import { escapeMarkdown } from '../../utils/markdown.js';

export function registerAdminHandlers(bot: any, userService: UserService, adminId: number = 0): void {
  bot.command(['stats', 'admin'], async (ctx: Context) => {
    const senderId = ctx.from?.id || 0;

    // Security check: Strictly enforce admin authorization (Fail-Closed)
    if (!adminId || adminId <= 0 || senderId !== adminId) {
      await ctx.reply('⛔ Akses ditolak. Perintah ini hanya dapat diakses oleh Admin.');
      return;
    }

    try {
      const stats = await userService.getGlobalStats();
      const memUsage = Math.round(process.memoryUsage().rss / 1024 / 1024);
      const uptimeSec = Math.round(process.uptime());
      const hours = Math.floor(uptimeSec / 3600);
      const minutes = Math.floor((uptimeSec % 3600) / 60);

      const statsCard =
        `📊 *DASHBOARD STATISTIK & KESEHATAN BOT*\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
        `👥 *Total Pengguna Terdaftar:* ${stats.totalUsers.toLocaleString()} user\n` +
        `📥 *Total Unduhan Musik:* ${stats.totalDownloads.toLocaleString()} lagu\n` +
        `👑 *Pelanggan VIP Aktif:* ${stats.premiumUsers.toLocaleString()} member\n` +
        `🎁 *Total Referral Teman:* ${stats.totalReferrals.toLocaleString()} koneksi\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
        `⚡ *Runtime:* Node.js ${process.version}\n` +
        `💾 *Memory RSS:* ${memUsage} MB\n` +
        `⏱️ *Process Uptime:* ${hours}j ${minutes}m`;

      await ctx.reply(statsCard, { parse_mode: 'Markdown' });
    } catch (err) {
      console.error('Stats command error:', err);
      await ctx.reply('⚠️ Terjadi kendala saat mengambil data statistik bot.');
    }
  });

  // Admin VIP Grant Command: /grant <userId> [days/lifetime] or /grantme
  bot.command(['grant', 'grantme'], async (ctx: Context) => {
    const senderId = ctx.from?.id || 0;
    if (!adminId || adminId <= 0 || senderId !== adminId) {
      await ctx.reply('⛔ Akses ditolak. Perintah ini hanya dapat diakses oleh Admin.');
      return;
    }

    const text = ctx.message?.text?.trim() || '';
    const args = text.split(/\s+/).slice(1);

    let targetId = senderId;
    let duration = 'lifetime';

    if (text.startsWith('/grantme')) {
      targetId = senderId;
      duration = 'lifetime';
    } else if (args.length >= 1) {
      targetId = parseInt(args[0], 10);
      duration = args[1]?.toLowerCase() || 'lifetime';
    }

    if (isNaN(targetId)) {
      await ctx.reply('⚠️ Format salah. Contoh penggunaan:\n`/grant 123456789 lifetime`\n`/grant 987654321 30`\n`/grantme`', {
        parse_mode: 'Markdown',
      });
      return;
    }

    await userService.grantSubscription(targetId, duration);

    await ctx.reply(`✅ *Berhasil!* Status VIP (${duration}) telah diberikan kepada Telegram ID: \`${targetId}\``, {
      parse_mode: 'Markdown',
    });
  });

  // Admin User List Command: /users or /userlist [page]
  bot.command(['users', 'userlist'], async (ctx: Context) => {
    const senderId = ctx.from?.id || 0;
    if (!adminId || adminId <= 0 || senderId !== adminId) {
      await ctx.reply('⛔ Akses ditolak. Perintah ini hanya dapat diakses oleh Admin.');
      return;
    }

    const text = ctx.message?.text?.trim() || '';
    const pageArg = text.split(/\s+/)[1];
    let page = parseInt(pageArg || '1', 10);
    if (isNaN(page) || page < 1) page = 1;

    await sendUsersListPage(ctx, userService, page, false);
  });

  // Pagination callback query for /users
  if (typeof bot.callbackQuery === 'function') {
    bot.callbackQuery(/^users_page_(\d+)$/, async (ctx: Context) => {
      const senderId = ctx.from?.id || 0;
      if (!adminId || adminId <= 0 || senderId !== adminId) {
        await ctx.answerCallbackQuery({ text: '⛔ Akses ditolak.', show_alert: true });
        return;
      }
      await ctx.answerCallbackQuery();
      const page = parseInt(ctx.match?.[1] || '1', 10);
      await sendUsersListPage(ctx, userService, page, true);
    });
  }

  // Admin Broadcast Command: /broadcast <pesan>
  bot.command('broadcast', async (ctx: Context) => {
    const senderId = ctx.from?.id || 0;
    if (!adminId || adminId <= 0 || senderId !== adminId) {
      await ctx.reply('⛔ Akses ditolak. Perintah ini hanya dapat diakses oleh Admin.');
      return;
    }

    const text = ctx.message?.text?.trim() || '';
    const parts = text.split(/\s+/);
    const messageToSend = text.substring(parts[0].length).trim();

    if (!messageToSend) {
      await ctx.reply(
        `📢 *PANDUAN BROADCAST ADMIN*\n\n` +
        `Gunakan perintah ini untuk mengirim pengumuman ke seluruh pengguna bot:\n` +
        `Format: \`/broadcast <pesan Anda>\`\n\n` +
        `Contoh:\n` +
        `\`/broadcast 📢 Halo semuanya! Server telah diperbarui dengan fitur baru.\``,
        { parse_mode: 'Markdown' }
      );
      return;
    }

    const userIds = await userService.getAllUserIds();
    if (userIds.length === 0) {
      await ctx.reply('⚠️ Tidak ada pengguna terdaftar untuk dikirimi broadcast.');
      return;
    }

    // Serverless Timeout Guard: Limit batch to 100 targets per execution to stay within Vercel timeout
    const MAX_TARGETS = 100;
    const targetUserIds = userIds.slice(0, MAX_TARGETS);
    const hasMore = userIds.length > MAX_TARGETS;

    const statusMsg = await ctx.reply(
      `⏳ Memulai pengiriman broadcast ke *${targetUserIds.length}* pengguna${hasMore ? ` (batch 1 dari total ${userIds.length} user)` : ''}...`,
      { parse_mode: 'Markdown' }
    );

    const startTime = Date.now();
    let successCount = 0;
    let failCount = 0;

    for (const targetId of targetUserIds) {
      try {
        await ctx.api.sendMessage(targetId, messageToSend, { parse_mode: 'Markdown' });
        successCount++;
      } catch (err: any) {
        failCount++;
      }
      // Small delay (40ms) to respect Telegram's rate limits
      await new Promise((r) => setTimeout(r, 40));
    }

    const elapsedSec = ((Date.now() - startTime) / 1000).toFixed(1);
    const serverlessNote = hasMore
      ? `\n⚠️ *Batas Serverless:* Pengiriman dibatasi ${MAX_TARGETS} user per batch untuk menjaga kestabilan waktu eksekusi Vercel.`
      : '';
    const reportCard =
      `📢 *LAPORAN HASIL PENGIRIMAN BROADCAST*\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
      `✅ *Berhasil Terkirim:* ${successCount} user\n` +
      `❌ *Gagal / Diblokir:* ${failCount} user\n` +
      `📊 *Target Batch:* ${targetUserIds.length} user\n` +
      `⏱️ *Durasi:* ${elapsedSec} detik` +
      `${serverlessNote}`;

    try {
      if (ctx.chat?.id && statusMsg?.message_id) {
        await ctx.api.editMessageText(ctx.chat.id, statusMsg.message_id, reportCard, {
          parse_mode: 'Markdown',
        });
      } else {
        await ctx.reply(reportCard, { parse_mode: 'Markdown' });
      }
    } catch (_) {
      await ctx.reply(reportCard, { parse_mode: 'Markdown' });
    }
  });
}

/**
 * Render and send paginated user list card.
 */
async function sendUsersListPage(
  ctx: Context,
  userService: UserService,
  page: number,
  isEdit: boolean
): Promise<void> {
  const limit = 8;
  const offset = (page - 1) * limit;
  const { users, total } = await userService.getUsers(limit, offset);
  const totalPages = Math.max(1, Math.ceil(total / limit));

  if (users.length === 0) {
    const emptyMsg = `👥 *DAFTAR PENGGUNA TERDAFTAR*\n\nBelum ada pengguna yang terdaftar di database.`;
    if (isEdit) {
      await ctx.editMessageText(emptyMsg, { parse_mode: 'Markdown' });
    } else {
      await ctx.reply(emptyMsg, { parse_mode: 'Markdown' });
    }
    return;
  }

  let text = `👥 *DAFTAR PENGGUNA TERDAFTAR*\n(Halaman ${page}/${totalPages} • Total: ${total} user)\n`;
  text += `━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;

  users.forEach((u, i) => {
    const num = offset + i + 1;
    const name = escapeMarkdown(u.firstName || 'User');
    const uname = u.username ? `@${escapeMarkdown(u.username)}` : '_tanpa username_';
    const tier = u.isPremium ? `👑 *VIP* (${escapeMarkdown(u.premiumTier || 'active')})` : '🆓 *Free*';
    const date = u.createdAt ? u.createdAt.split('T')[0] : '-';

    text += `${num}. *${name}* (${uname})\n`;
    text += `   🆔 \`${u.telegramId}\` • Status: ${tier}\n`;
    text += `   📥 Unduhan: *${u.totalDownloads}* lagu • Gabung: \`${date}\`\n\n`;
  });

  const buttons: any[] = [];
  if (page > 1) {
    buttons.push({ text: '⬅️ Sebelumnya', callback_data: `users_page_${page - 1}` });
  }
  if (page < totalPages) {
    buttons.push({ text: 'Selanjutnya ➡️', callback_data: `users_page_${page + 1}` });
  }

  const keyboard = buttons.length > 0 ? { inline_keyboard: [buttons] } : undefined;

  if (isEdit) {
    try {
      await ctx.editMessageText(text, { parse_mode: 'Markdown', reply_markup: keyboard });
    } catch (_) {
      await ctx.reply(text, { parse_mode: 'Markdown', reply_markup: keyboard });
    }
  } else {
    await ctx.reply(text, { parse_mode: 'Markdown', reply_markup: keyboard });
  }
}

