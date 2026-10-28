import { createBot } from './bot/bot.js';
import { loadConfig } from './config/env.js';
import { setupBotCommands } from './bot/commands.js';

const config = loadConfig();

if (!config.botToken) {
  console.error('⚠️ [ERROR] BOT_TOKEN belum diset di file .env!');
  console.error('Silakan buat file .env di apps/music-downloader-bot/.env dan isi BOT_TOKEN dari @BotFather.');
  process.exit(1);
}

const { bot } = createBot(config.botToken, undefined, config.databaseUrl, config.adminId, config.streamResolverUrl, config.rapidApiKey);

console.log('🎵 Memulai Music Downloader Bot dalam mode Long Polling lokal...');
bot.start({
  onStart: async (botInfo) => {
    console.log(`🚀 Bot @${botInfo.username} berhasil berjalan dan siap menerima pesan!`);
    try {
      await setupBotCommands(bot.api, config.adminId);
      console.log('✅ Menu perintah resmi Telegram berhasil didaftarkan ke @BotFather.');
    } catch (err) {
      console.warn('⚠️ Gagal mendaftarkan menu perintah ke Telegram API:', err);
    }
  },
});

