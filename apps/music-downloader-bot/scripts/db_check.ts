import dotenv from 'dotenv';
dotenv.config();

import { PostgresUserRepository } from '../src/repositories/user.repository.js';
import { loadConfig } from '../src/config/env.js';

async function main() {
  const config = loadConfig();
  console.log('🔍 Checking Database Configuration...');
  if (!config.databaseUrl) {
    console.error('❌ DATABASE_URL is not set in .env!');
    process.exit(1);
  }

  console.log('📡 Connecting to Neon PostgreSQL...');
  console.log(`🔗 Target URL: ${config.databaseUrl.replace(/:[^:@]+@/, ':****@')}`);

  const repo = new PostgresUserRepository(config.databaseUrl);

  console.log('⚙️ Initializing tables schema (music_users, music_referrals, music_audio_cache, music_payments)...');
  await repo.initSchema();
  console.log('✅ Schema migration executed successfully!');

  console.log('📊 Querying global stats to verify database query execution...');
  const stats = await repo.getGlobalStats();
  console.log('📈 Current Global Stats from Cloud Database:', stats);

  const users = await (repo as any).sql`SELECT telegram_id, username, first_name, created_at FROM music_users LIMIT 5;`;
  console.log('👤 Registered Users in Database:', users);

  console.log('🎉 Neon PostgreSQL Cloud Database is 100% READY for Production!');
}

main().catch((err) => {
  console.error('❌ Database connection or schema error:', err);
  process.exit(1);
});
