import type { BotCommand } from 'grammy/types';

/**
 * Official Telegram Bot slash commands specification.
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
