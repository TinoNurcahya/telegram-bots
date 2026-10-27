import { Bot } from 'grammy';
import { loadConfig } from '../src/config/env.js';
import { BOT_COMMANDS } from '../src/bot/commands.js';

const config = loadConfig();

if (!config.botToken) {
  console.error('❌ [ERROR] BOT_TOKEN belum diset di file .env!');
  console.error('Silakan isi BOT_TOKEN di apps/music-downloader-bot/.env terlebih dahulu.');
  process.exit(1);
}

const bot = new Bot(config.botToken);
const command = process.argv[2] || 'info';

async function main() {
  switch (command) {
    case 'info':
    case '--info': {
      console.log('📡 Mengambil informasi webhook saat ini dari Telegram API...');
      try {
        const info = await bot.api.getWebhookInfo();
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log(`🌐 Webhook URL       : ${info.url || '(Tidak ada webhook aktif - Mode Polling)'}`);
        console.log(`🛡️ Has Custom Cert   : ${info.has_custom_certificate}`);
        console.log(`⏳ Pending Updates   : ${info.pending_update_count}`);
        console.log(`⚡ Max Connections   : ${info.max_connections || 'Default (40)'}`);
        if (info.last_error_date) {
          const errDate = new Date(info.last_error_date * 1000).toLocaleString('id-ID');
          console.log(`⚠️ Last Error Date   : ${errDate}`);
          console.log(`⚠️ Last Error Message: ${info.last_error_message}`);
        } else {
          console.log(`✅ Webhook Health    : Sehat (Tidak ada riwayat error)`);
        }
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      } catch (err) {
        console.error('❌ Gagal mengambil informasi webhook:', err);
      }
      break;
    }

    case 'set':
    case '--set': {
      const targetUrl = process.argv[3] || config.webhookUrl;
      if (!targetUrl || targetUrl.includes('your-music-bot.vercel.app')) {
        console.error('❌ [ERROR] URL Webhook tidak valid!');
        console.error('Tentukan URL publik Vercel Anda, contoh:');
        console.error('  npm run webhook:set https://music-bot.vercel.app/api/index');
        process.exit(1);
      }

      console.log(`🚀 Mendaftarkan Webhook Telegram ke: ${targetUrl}`);
      try {
        await bot.api.setWebhook(targetUrl, {
          secret_token: config.webhookSecret || undefined,
          drop_pending_updates: false,
          allowed_updates: ['message', 'callback_query', 'inline_query', 'pre_checkout_query'],
        });
        console.log('✅ Webhook berhasil diaktifkan di Telegram!');
        if (config.webhookSecret) {
          console.log('🛡️ Secret token otentikasi webhook berhasil dipasang.');
        }

        // Auto-register commands as well
        await bot.api.setMyCommands(BOT_COMMANDS);
        console.log('✅ Menu autocomplete perintah bot berhasil didaftarkan.');
      } catch (err) {
        console.error('❌ Gagal memasang webhook:', err);
      }
      break;
    }

    case 'delete':
    case '--delete': {
      console.log('🗑️ Menghapus webhook Telegram (kembali ke mode Long Polling lokal)...');
      try {
        await bot.api.deleteWebhook({ drop_pending_updates: false });
        console.log('✅ Webhook berhasil dihapus dari Telegram API.');
        console.log('💡 Sekarang Anda dapat menjalankan mode dev lokal: npm run dev');
      } catch (err) {
        console.error('❌ Gagal menghapus webhook:', err);
      }
      break;
    }

    case 'commands':
    case '--commands': {
      console.log('📝 Mendaftarkan menu perintah bot ke Telegram API...');
      try {
        await bot.api.setMyCommands(BOT_COMMANDS);
        console.log('✅ Daftar perintah bot berhasil didaftarkan:');
        BOT_COMMANDS.forEach((c) => console.log(`   /${c.command.padEnd(10)} - ${c.description}`));
      } catch (err) {
        console.error('❌ Gagal mendaftarkan perintah:', err);
      }
      break;
    }

    case 'health':
    case '--health': {
      const targetUrl = process.argv[3] || config.webhookUrl;
      console.log(`🩺 Memeriksa respons GET endpoint: ${targetUrl}`);
      try {
        const res = await fetch(targetUrl);
        const data = await res.json();
        console.log(`HTTP Status : ${res.status} ${res.statusText}`);
        console.log('Response    :', data);
      } catch (err) {
        console.error('❌ Endpoint tidak dapat dihubungi:', err);
      }
      break;
    }

    default: {
      console.log('📖 Panduan Penggunaan Webhook Manager:');
      console.log('   npm run webhook:info      - Cek status & error webhook di Telegram');
      console.log('   npm run webhook:set [url] - Daftarkan URL webhook Vercel');
      console.log('   npm run webhook:delete    - Hapus webhook (untuk kembali ke Long Polling)');
      console.log('   npm run webhook:commands  - Daftarkan menu perintah slash Telegram');
      console.log('   npm run webhook:health    - Cek kesehatan endpoint HTTP GET');
    }
  }
}

main().catch((e) => console.error(e));
