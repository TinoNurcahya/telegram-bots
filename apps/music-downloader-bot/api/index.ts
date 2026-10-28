import { webhookCallback } from 'grammy';
import type { IncomingMessage, ServerResponse } from 'http';
import { createBot } from '../src/bot/bot.js';
import { loadConfig } from '../src/config/env.js';

const config = loadConfig();
// Use fallback token during build time or health check
const botToken = config.botToken || '000000000:dummy_token_for_cold_boot';
const { bot } = createBot(botToken, undefined, config.databaseUrl, config.adminId, config.streamResolverUrl, config.rapidApiKey);
const handleUpdate = webhookCallback(bot, 'http');

export default async function handler(req: IncomingMessage, res: ServerResponse): Promise<void> {
  // 1. Health check endpoint for uptime monitors and browser
  if (req.method === 'GET') {
    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/json');
    res.end(
      JSON.stringify({
        status: 'ok',
        service: 'MusicDownloaderBot',
        mode: 'vercel-serverless',
        runtime: 'Node.js 22 (TypeScript)',
        framework: 'grammY',
      })
    );
    return;
  }

  // 2. Webhook receiver endpoint from Telegram
  if (req.method === 'POST') {
    if (config.webhookSecret) {
      const secretHeader = req.headers['x-telegram-bot-api-secret-token'];
      if (secretHeader !== config.webhookSecret) {
        res.statusCode = 403;
        res.end('Forbidden: invalid secret token');
        return;
      }
    }

    try {
      await handleUpdate(req, res);
    } catch (err) {
      console.error('Webhook execution error:', err);
      // Ensure 200 OK is returned to Telegram to avoid infinite update retry loops
      if (!res.writableEnded) {
        res.statusCode = 200;
        res.end(JSON.stringify({ ok: true, error: String(err) }));
      }
    }
    return;
  }

  res.statusCode = 405;
  res.end('Method Not Allowed');
}
