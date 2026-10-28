import type { BotCommand } from 'grammy/types';

/**
 * Official Telegram Bot slash commands specification for public users.
 * Registered via bot.api.setMyCommands() to populate Telegram's autocomplete menu.
 */
export const BOT_COMMANDS: BotCommand[] = [
  { command: 'song', description: 'Cari & unduh musik atau lagu favorit' },
  { command: 'charts', description: 'Tangga lagu Top 10 Global & Indonesia' },
  { command: 'lyrics', description: 'Cari lirik lagu lengkap & karaoke synced' },
  { command: 'profile', description: 'Cek sisa kuota unduhan & status akun' },
  { command: 'upgrade', description: 'Dukungan server & Supporter VIP Stars' },
  { command: 'trial', description: 'Klaim Free Trial 7 Hari (1x per akun)' },
  { command: 'invite', description: 'Ajak teman & dapatkan +3 kuota unduhan' },
  { command: 'help', description: 'Panduan lengkap cara penggunaan bot' },
];

/**
 * Admin exclusive commands list with admin badge.
 */
export const ADMIN_COMMANDS: BotCommand[] = [
  ...BOT_COMMANDS,
  { command: 'stats', description: '👑 [Admin] Dashboard statistik & kesehatan bot' },
  { command: 'grant', description: '👑 [Admin] Berikan akses VIP ke user' },
  { command: 'grantme', description: '👑 [Admin] Berikan VIP seumur hidup ke diri sendiri' },
];

/**
 * Register public commands globally and scoped admin commands exclusively to ADMIN_ID.
 */
export async function setupBotCommands(botApi: any, adminId: number = 0): Promise<void> {
  // 1. Default public scope (all private chats)
  await botApi.setMyCommands(BOT_COMMANDS);

  // 2. Scoped admin chat (only visible in admin's personal chat)
  if (adminId > 0) {
    try {
      await botApi.setMyCommands(ADMIN_COMMANDS, {
        scope: { type: 'chat', chat_id: adminId },
      });
    } catch (err) {
      console.warn('Gagal mendaftarkan menu scoped admin:', err);
    }
  }
}
