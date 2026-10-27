import { InlineKeyboard } from 'grammy';
import { PLANS } from '../../services/user.service.js';

/**
 * Build keyboard for premium upgrade duration options.
 */
export function buildUpgradeKeyboard(hasUsedTrial: boolean): InlineKeyboard {
  const kb = new InlineKeyboard();

  if (!hasUsedTrial) {
    kb.text('🎁 Klaim Free Trial 7 Hari (GRATIS)', 'claim_trial_7d').row();
  }

  kb.text(`🌟 Donasi Supporter 1 Bulan (${PLANS.plan_1m.stars} Stars)`, 'pay_stars_1m').row();
  kb.text(`🚀 Donasi Supporter 3 Bulan (${PLANS.plan_3m.stars} Stars)`, 'pay_stars_3m').row();
  kb.text(`👑 Donasi Lifetime Backer (${PLANS.plan_lifetime.stars} Stars)`, 'pay_stars_lifetime').row();

  return kb;
}

/**
 * Build keyboard when freemium quota is exhausted.
 */
export function buildQuotaLimitKeyboard(hasUsedTrial: boolean, botUsername: string = 'MusicDownloaderBot'): InlineKeyboard {
  const kb = new InlineKeyboard();

  if (!hasUsedTrial) {
    kb.text('🎁 Klaim Free Trial 7 Hari (GRATIS)', 'claim_trial_7d').row();
  }

  kb.text('💖 Dukung Server & Akses VIP (Stars)', 'show_upgrade_menu').row();
  kb.switchInline('👥 Ajak Teman (+3 Lagu)', 'Ayo download lagu MP3 favoritmu di bot ini!').row();

  return kb;
}

/**
 * Build keyboard when Premium VIP user reaches 50 songs limit in a 12-hour cycle.
 */
export function buildPremiumQuotaLimitKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text('⚡ Donasi Boost +25 Lagu (10 Stars)', 'pay_boost_25')
    .row()
    .text('🚀 Donasi Boost +50 Lagu (18 Stars)', 'pay_boost_50');
}
