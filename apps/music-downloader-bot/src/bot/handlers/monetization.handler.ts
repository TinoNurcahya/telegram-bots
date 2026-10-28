import { Context, InlineKeyboard } from 'grammy';
import { UserService, PLANS, BOOST_PLANS } from '../../services/user.service.js';
import { buildUpgradeKeyboard } from '../keyboards/monetization.keyboard.js';
import { escapeMarkdown } from '../../utils/markdown.js';

export function registerMonetizationHandlers(bot: any, userService: UserService): void {
  // 1. /upgrade & /premium commands
  bot.command(['upgrade', 'premium'], async (ctx: Context) => {
    const userId = ctx.from?.id || 0;
    const profile = await userService.getUserProfile(userId);

    if (profile.isPremium) {
      const daysText = profile.premiumTier === 'lifetime' ? 'Seumur Hidup' : `${profile.daysLeft} hari lagi`;
      const quotaCount = profile.premiumTier === 'trial_7d' ? '10' : '15';
      const monthlyMax = profile.premiumTier === 'trial_7d' ? '50' : '150';
      await ctx.reply(
        `⭐ STATUS AKUN: PREMIUM MEMBER\n\n` +
        `Anda sedang menikmati akses Premium (${profile.premiumTier}):\n` +
        `⏳ Sisa Masa Aktif: ${daysText}\n\n` +
        `Fasilitas eksklusif Anda:\n` +
        `✨ Unduh hingga ${quotaCount} lagu per hari (maks ${monthlyMax} lagu/bulan)\n` +
        `🎧 Kualitas audio HD 320kbps\n` +
        `📜 Akses lirik dan pencarian instan tanpa batas`
      );
      return;
    }

    const pitch =
      `💖 DUKUNGAN OPERASIONAL & DONATUR VIP (TELEGRAM STARS)\n\n` +
      `Bot ini dikembangkan secara independen. Donasi Telegram Stars Anda digunakan sepenuhnya untuk pemeliharaan server cloud dan pembaruan API agar bot tetap aktif 24/7.\n\n` +
      `Sebagai bentuk apresiasi bagi para donatur, akun Anda mendapatkan status Supporter VIP:\n` +
      `✨ Kuota hingga 15 lagu per hari (maks 150 lagu/bulan)\n` +
      `🎧 Kualitas audio jernih Studio HD 320kbps\n` +
      `📜 Akses lirik dan pencarian instan tanpa batas\n\n` +
      `PILIHAN DUKUNGAN DONASI:\n` +
      (!profile.hasUsedTrial ? `🎁 Free Trial 7 Hari: GRATIS (Coba 10 lagu/hari, maks 50 lagu)\n` : '') +
      `🌟 Donasi Supporter 1 Bulan: 25 Stars\n` +
      `🚀 Donasi Supporter 3 Bulan: 60 Stars (Hemat 20%)\n` +
      `👑 Donasi Lifetime Backer: 99 Stars (Akses permanen)\n\n` +
      `Pilih tombol di bawah untuk menyalurkan dukungan Anda:`;

    await ctx.reply(pitch, {
      reply_markup: buildUpgradeKeyboard(profile.hasUsedTrial),
    });
  });

  // 2. /trial command
  bot.command('trial', async (ctx: Context) => {
    const userId = ctx.from?.id || 0;
    const profile = await userService.getUserProfile(userId);

    if (profile.hasUsedTrial || profile.isPremium) {
      const daysText = profile.premiumTier === 'lifetime' ? 'Seumur Hidup' : `${profile.daysLeft} hari lagi`;
      const quotaCount = profile.premiumTier === 'trial_7d' ? '10' : '15';
      const monthlyMax = profile.premiumTier === 'trial_7d' ? '50' : '150';
      await ctx.reply(
        `⭐ STATUS TRIAL & VIP ANDA AKTIF!\n\n` +
        `Anda sudah mengaktifkan Free Trial 7 Hari (atau langganan VIP):\n` +
        `⏳ Sisa Masa Aktif: ${daysText}\n` +
        `✨ Kuota: ${quotaCount} lagu per hari (maks ${monthlyMax} lagu/bulan)\n` +
        `🎧 Kualitas: Studio HD 320kbps\n\n` +
        `Ketik /profile untuk melihat statistik lengkap akun Anda!`
      );
      return;
    }

    const res = await userService.claimFreeTrial(userId);
    if (res.success) {
      await ctx.reply(
        `🎉 SELAMAT! FREE TRIAL 7 HARI BERHASIL DIAKTIFKAN! ⭐\n\n` +
        `Status VIP Anda telah aktif selama 7 hari ke depan.\n\n` +
        `Fasilitas eksklusif Anda:\n` +
        `✨ Kuota unduh 10 lagu per hari (maks 50 lagu selama masa trial)\n` +
        `💎 Audio kualitas rekaman studio HD 320kbps\n` +
        `📜 Lirik lagu lengkap & akses instan\n\n` +
        `Ketik /profile untuk cek kuota Anda atau langsung cari lagu favorit Anda!`
      );
    } else {
      await ctx.reply(res.message);
    }
  });

  // 3. /profile command & profile button callback
  bot.command('profile', async (ctx: Context) => {
    await sendUserProfile(ctx, userService);
  });

  bot.callbackQuery('show_profile', async (ctx: Context) => {
    await ctx.answerCallbackQuery();
    await sendUserProfile(ctx, userService);
  });

  // 4. /invite command
  bot.command('invite', async (ctx: Context) => {
    const userId = ctx.from?.id || 0;
    let botUsername = 'Musicdownloader2001_bot';
    try {
      const me = ctx.me || (await ctx.api.getMe());
      if (me?.username) {
        botUsername = me.username;
      }
    } catch (_) {}

    const inviteLink = `https://t.me/${botUsername}?start=ref_${userId}`;
    const shareText = encodeURIComponent(
      '🎵 Dengarkan dan unduh lagu favoritmu langsung di Telegram dengan audio kualitas jernih di @Musicdownloader2001_bot!'
    );
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(inviteLink)}&text=${shareText}`;

    const inviteKeyboard = new InlineKeyboard()
      .url('📢 Bagikan ke Teman / Grup', shareUrl)
      .row()
      .url('🎁 Buka Link Undangan', inviteLink);

    const text =
      `👥 PROGRAM REFERRAL TEMAN\n\n` +
      `Bagikan link undangan pribadi Anda ke teman atau grup Telegram:\n` +
      `${inviteLink}\n\n` +
      `🎁 KEUNTUNGAN REFERRAL:\n` +
      `Teman yang baru pertama kali bergabung akan langsung mendapatkan +3 kuota unduhan lagu tambahan.\n` +
      `Anda sebagai pengundang juga akan langsung menerima +3 kuota unduhan lagu tambahan!\n\n` +
      `Ajak sebanyak-banyaknya teman Anda untuk mengumpulkan kuota download gratis!`;

    await ctx.reply(text, { reply_markup: inviteKeyboard });
  });

  // 5. Callback queries for monetization
  bot.callbackQuery('show_upgrade_menu', async (ctx: Context) => {
    const userId = ctx.from?.id || 0;
    const profile = await userService.getUserProfile(userId);
    await ctx.answerCallbackQuery();

    const pitch =
      `💖 DUKUNGAN OPERASIONAL & DONATUR VIP (TELEGRAM STARS)\n\n` +
      `Donasi Anda membantu pemeliharaan infrastruktur server cloud agar bot tetap aktif dan responsif 24/7!\n\n` +
      `Fasilitas Apresiasi Donatur VIP:\n` +
      `✨ Kuota hingga 15 lagu per hari (maks 150 lagu/bulan)\n` +
      `🎧 Kualitas audio rekaman studio HD 320kbps\n` +
      `📜 Akses lirik dan pencarian instan tanpa batas\n\n` +
      `PILIHAN DUKUNGAN DONASI:\n` +
      (!profile.hasUsedTrial ? `🎁 Free Trial 7 Hari: GRATIS (10 lagu/hari, maks 50 lagu)\n` : '') +
      `🌟 Donasi Supporter 1 Bulan: 25 Stars\n` +
      `🚀 Donasi Supporter 3 Bulan: 60 Stars (Hemat 20%)\n` +
      `👑 Donasi Lifetime Backer: 99 Stars`;

    await ctx.reply(pitch, {
      reply_markup: buildUpgradeKeyboard(profile.hasUsedTrial),
    });
  });

  bot.callbackQuery('claim_trial_7d', async (ctx: Context) => {
    const userId = ctx.from?.id || 0;
    await ctx.answerCallbackQuery();
    const profile = await userService.getUserProfile(userId);

    if (profile.hasUsedTrial || profile.isPremium) {
      const daysText = profile.premiumTier === 'lifetime' ? 'Seumur Hidup' : `${profile.daysLeft} hari lagi`;
      try {
        await ctx.editMessageReplyMarkup({
          reply_markup: buildUpgradeKeyboard(true),
        });
      } catch (_) {}
      await ctx.reply(
        `⭐ STATUS TRIAL & VIP ANDA AKTIF!\n\n` +
        `Anda sudah mengklaim Free Trial sebelumnya:\n` +
        `⏳ Sisa Masa Aktif: ${daysText}\n\n` +
        `Ketik /profile untuk melihat kuota Anda atau /upgrade jika ingin memperpanjang akses VIP.`
      );
      return;
    }

    const res = await userService.claimFreeTrial(userId);
    if (res.success) {
      try {
        await ctx.editMessageReplyMarkup({
          reply_markup: buildUpgradeKeyboard(true),
        });
      } catch (_) {}

      await ctx.reply(
        `🎉 SELAMAT! FREE TRIAL 7 HARI BERHASIL DIAKTIFKAN! ⭐\n\n` +
        `Status VIP Anda telah aktif selama 7 hari ke depan.\n\n` +
        `Fasilitas eksklusif Anda:\n` +
        `✨ Kuota unduh 10 lagu per hari (maks 50 lagu selama masa trial)\n` +
        `💎 Audio kualitas rekaman studio HD 320kbps\n` +
        `📜 Lirik lagu lengkap & akses instan\n\n` +
        `Ketik /profile untuk cek kuota Anda atau langsung cari lagu favorit Anda!`
      );
    } else {
      await ctx.reply(res.message);
    }
  });

  bot.callbackQuery(/^pay_stars_(.+)$/, async (ctx: Context) => {
    await ctx.answerCallbackQuery();
    const planKey = ctx.match?.[1];
    const fullKey = `plan_${planKey}`;
    const plan = PLANS[fullKey];

    if (!plan) {
      await ctx.reply('⚠️ Paket langganan tidak ditemukan.');
      return;
    }

    try {
      await ctx.replyWithInvoice(
        plan.title,
        plan.description,
        fullKey,
        'XTR', // Telegram Stars native currency
        [{ label: plan.title, amount: plan.stars }]
      );
    } catch (err) {
      console.error('Invoice error:', err);
      await ctx.reply(
        '⚠️ Maaf, pembayaran via Telegram Stars memerlukan setup Bot Payments di BotFather, ' +
        'atau Anda dapat mencoba kembali dalam beberapa saat.'
      );
    }
  });

  // Extra Quota Boost callback queries
  bot.callbackQuery(/^pay_boost_(25|50)$/, async (ctx: Context) => {
    await ctx.answerCallbackQuery();
    const boostKey = `boost_${ctx.match?.[1]}`;
    const boost = BOOST_PLANS[boostKey];

    if (!boost) {
      await ctx.reply('⚠️ Paket Extra Boost tidak ditemukan.');
      return;
    }

    try {
      await ctx.replyWithInvoice(
        boost.title,
        boost.description,
        boostKey,
        'XTR',
        [{ label: boost.title, amount: boost.stars }]
      );
    } catch (err) {
      console.error('Boost invoice error:', err);
      await ctx.reply('⚠️ Terjadi kendala saat memproses faktur Telegram Stars. Silakan coba lagi nanti.');
    }
  });

  // 6. Pre-checkout query validation (Anti-tampering)
  bot.on('pre_checkout_query', async (ctx: Context) => {
    const query = ctx.preCheckoutQuery;
    if (!query) return;

    // Currency check: Must be XTR
    if (query.currency !== 'XTR') {
      await ctx.answerPreCheckoutQuery(false, {
        error_message: 'Mata uang transaksi tidak valid. Hanya Telegram Stars (XTR) yang didukung.',
      });
      return;
    }

    // Payload check (PLANS or BOOST_PLANS)
    const plan = PLANS[query.invoice_payload] || BOOST_PLANS[query.invoice_payload];
    if (!plan) {
      await ctx.answerPreCheckoutQuery(false, {
        error_message: 'Paket langganan atau boost tidak valid atau telah kedaluwarsa.',
      });
      return;
    }

    // Amount check: Prevent price manipulation
    if (query.total_amount !== plan.stars) {
      await ctx.answerPreCheckoutQuery(false, {
        error_message: `Jumlah Telegram Stars tidak cocok (diharapkan ${plan.stars} Stars).`,
      });
      return;
    }

    // Approve transaction
    await ctx.answerPreCheckoutQuery(true);
  });

  // 7. Successful payment handler
  bot.on('message:successful_payment', async (ctx: Context) => {
    const payment = ctx.message?.successful_payment;
    if (!payment) return;

    const userId = ctx.from?.id || 0;
    const payload = payment.invoice_payload;

    if (payment.currency !== 'XTR') {
      await ctx.reply('⚠️ Transaksi tidak sah.');
      return;
    }

    // Payment Idempotency Guard (Prevents double crediting on webhook retries)
    const chargeId = payment.telegram_payment_charge_id;
    const isNew = await userService.recordPayment(chargeId, userId, payload, payment.total_amount);
    if (!isNew) {
      console.warn(`Duplicate payment webhook received and safely deduplicated: ${chargeId}`);
      return;
    }

    // Case A: Extra Quota Boost fulfillment
    if (payload.startsWith('boost_')) {
      const boost = BOOST_PLANS[payload];
      if (!boost || payment.total_amount !== boost.stars) {
        await ctx.reply('⚠️ Data transaksi boost tidak sesuai.');
        return;
      }

      await userService.addExtraBoost(userId, payload);
      const boostNotice =
        `🎉 PEMBELIAN EXTRA BOOST BERHASIL! ⭐\n` +
        `━━━━━━━━━━━━━━━━━━━━\n` +
        `Akun Anda telah ditambahkan +${boost.songs} kuota unduhan lagu tambahan!\n` +
        `Kuota ini langsung aktif dan dapat langsung Anda gunakan sekarang juga!`;

      await ctx.reply(boostNotice);
      return;
    }

    // Case B: Premium Pass Subscription fulfillment
    const plan = PLANS[payload];
    if (!plan || payment.total_amount !== plan.stars) {
      console.warn(`Suspicious payment from ${userId}: payload=${payload}, amount=${payment.total_amount}`);
      await ctx.reply('⚠️ Pembayaran terdeteksi namun tidak cocok dengan sistem kami. Silakan hubungi admin.');
      return;
    }

    await userService.grantSubscription(userId, payload);
    const celebration =
      `🎉 PEMBAYARAN TELEGRAM STARS BERHASIL! ⭐\n` +
      `━━━━━━━━━━━━━━━━━━━━\n` +
      `Selamat! Akun Anda telah berhasil di-upgrade ke:\n` +
      `👑 ${plan.title}\n\n` +
      `Fasilitas yang langsung aktif:\n` +
      `✨ Kuota 15 lagu per hari (maks 150 lagu/bulan)\n` +
      `🎧 Kualitas audio HD 320kbps\n` +
      `📜 Lirik lagu lengkap & pencarian instan\n\n` +
      `Terima kasih atas dukungan Anda! Selamat menikmati musik favorit Anda!`;

    await ctx.reply(celebration);
  });
}

/**
 * Common handler to build and send user profile card.
 */
async function sendUserProfile(ctx: Context, userService: UserService): Promise<void> {
  const userId = ctx.from?.id || 0;
  if (ctx.from) {
    await userService.ensureUser(userId, ctx.from.username, ctx.from.first_name);
  }
  const profile = await userService.getUserProfile(userId);
  const quota = await userService.checkDailyQuota(userId);

  const statusBadge = profile.isOwner
    ? '👑 Bot Creator & Lifetime VIP (Akses Penuh Tanpa Batas)'
    : profile.isPremium
    ? `⭐ Premium (${profile.premiumTier === 'lifetime' ? 'Seumur Hidup' : `${profile.daysLeft} hari lagi`})`
    : '🆓 Akun Gratis (Freemium)';

  const dailyQuotaLabel = profile.isOwner
    ? `Akses Tanpa Batas`
    : `${quota.usedToday} / ${quota.maxLimit} lagu (Reset 07:00 WIB)`;

  const monthlyQuotaLabel = profile.isOwner
    ? `Akses Tanpa Batas`
    : `${quota.usedThisMonth} / ${quota.maxMonthlyLimit} lagu (Reset awal bulan)`;

  const profileCard =
    `👤 PROFIL & STATISTIK PENGGUNA\n` +
    `━━━━━━━━━━━━━━━━━━━━\n` +
    `🆔 Telegram ID: \`${userId}\`\n` +
    `👤 Nama: ${escapeMarkdown(profile.firstName || 'Pengguna')}\n` +
    `🎖️ Status: ${statusBadge}\n` +
    `📥 Total Lagu Diunduh: ${profile.totalDownloads} lagu\n` +
    `📊 Kuota Hari Ini: ${dailyQuotaLabel}\n` +
    `🗓️ Kuota Bulan Ini: ${monthlyQuotaLabel}\n` +
    `🎁 Bonus Kuota Tambahan: +${profile.bonusQuota} lagu\n\n` +
    `Gunakan /invite untuk menambah kuota gratis atau /upgrade untuk akses VIP!`;

  await ctx.reply(profileCard, { parse_mode: 'Markdown' });
}
