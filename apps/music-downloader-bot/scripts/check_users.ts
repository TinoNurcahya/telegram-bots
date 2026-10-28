import { neon } from '@neondatabase/serverless';
import { loadConfig } from '../src/config/env.js';

const config = loadConfig();
if (!config.databaseUrl) {
  console.log('No DATABASE_URL configured.');
  process.exit(1);
}

const sql = neon(config.databaseUrl);

async function main() {
  try {
    const users = (await sql`
      SELECT 
        telegram_id, 
        username, 
        first_name, 
        total_downloads, 
        is_premium, 
        premium_tier, 
        created_at, 
        last_active 
      FROM music_users 
      ORDER BY created_at DESC 
      LIMIT 50;
    `) as any[];

    console.log(`TOTAL_USERS: ${users.length}`);
    users.forEach((u, i) => {
      const uname = u.username ? `@${u.username}` : '(tanpa username)';
      const tier = u.is_premium ? `👑 VIP (${u.premium_tier || 'active'})` : '🆓 Free';
      console.log(`${i + 1}. ${u.first_name || 'User'} (${uname}) - ID: ${u.telegram_id} | Status: ${tier} | Unduhan: ${u.total_downloads} lagu`);
    });
  } catch (err) {
    console.error('Database query error:', err);
  }
}

main();
