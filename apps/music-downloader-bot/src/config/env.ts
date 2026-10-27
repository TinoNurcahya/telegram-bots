import dotenv from 'dotenv';
dotenv.config();

export interface BotConfig {
  botToken: string;
  webhookSecret: string;
  webhookUrl: string;
  databaseUrl: string;
  adminId: number;
  isProduction: boolean;
}

export function loadConfig(): BotConfig {
  const botToken = process.env.BOT_TOKEN || '';
  const webhookSecret = process.env.WEBHOOK_SECRET || '';
  const webhookUrl = process.env.WEBHOOK_URL || '';
  const databaseUrl = process.env.DATABASE_URL || '';
  const adminId = parseInt(process.env.ADMIN_ID || '0', 10);
  const isProduction = process.env.NODE_ENV === 'production';

  return {
    botToken,
    webhookSecret,
    webhookUrl,
    databaseUrl,
    adminId,
    isProduction,
  };
}
