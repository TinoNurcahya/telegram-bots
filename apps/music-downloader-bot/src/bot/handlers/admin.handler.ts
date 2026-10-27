import { Context } from 'grammy';
import { UserService } from '../../services/user.service.js';

export function registerAdminHandlers(bot: any, userService: UserService, adminId: number = 0): void {
  bot.command(['stats', 'admin'], async (ctx: Context) => {
    const senderId = ctx.from?.id || 0;

    // Security check: Only allow admin if ADMIN_ID is configured
    if (adminId > 0 && senderId !== adminId) {
      await ctx.reply('⛔ Akses ditolak. Perintah ini hanya dapat diakses oleh Admin bot.');
      return;
    }

    try {
      const stats = await userService.getGlobalStats();
      const memUsage = Math.round(process.memoryUsage().rss / 1024 / 1024);
      const uptimeSec = Math.round(process.uptime());
      const hours = Math.floor(uptimeSec / 3600);
      const minutes = Math.floor((uptimeSec % 3600) / 60);

      const securityNote = adminId === 0
        ? `\n⚠️ *Perhatian:* ADMIN_ID belum diset di .env. Daftarkan Telegram ID Anda di .env agar perintah ini terkunci.`
        : '';

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
        `⏱️ *Process Uptime:* ${hours}j ${minutes}m\n` +
        `${securityNote}`;

      await ctx.reply(statsCard, { parse_mode: 'Markdown' });
    } catch (err) {
      console.error('Stats command error:', err);
      await ctx.reply('⚠️ Terjadi kendala saat mengambil data statistik bot.');
    }
  });

  // Admin VIP Grant Command: /grant <userId> [days/lifetime] or /grantme
  bot.command(['grant', 'grantme'], async (ctx: Context) => {
    const senderId = ctx.from?.id || 0;
    if (adminId > 0 && senderId !== adminId) {
      await ctx.reply('⛔ Akses ditolak. Perintah ini hanya dapat diakses oleh Admin bot.');
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
      await ctx.reply('⚠️ Format salah. Contoh penggunaan:\n`/grant 7741750167 lifetime`\n`/grant 12345678 30`\n`/grantme`', {
        parse_mode: 'Markdown',
      });
      return;
    }

    await userService.grantSubscription(targetId, duration);

    await ctx.reply(`✅ *Berhasil!* Status VIP (${duration}) telah diberikan kepada Telegram ID: \`${targetId}\``, {
      parse_mode: 'Markdown',
    });
  });
}
