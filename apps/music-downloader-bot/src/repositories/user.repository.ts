import { neon } from '@neondatabase/serverless';

export interface UserRecord {
  telegramId: number;
  username?: string;
  firstName?: string;
  totalDownloads: number;
  dailyDownloadCount: number;
  dailyDownloadDate: string; // "YYYY-MM-DD"
  monthlyDownloadCount?: number;
  monthlyDownloadDate?: string; // "YYYY-MM"
  bonusQuota: number;
  isPremium: boolean;
  premiumTier?: string;
  premiumUntil?: string; // ISO 8601 string
  hasUsedTrial: boolean;
  invitedBy?: number;
  createdAt: string;
  lastActive: string;
}

export interface GlobalStats {
  totalUsers: number;
  totalDownloads: number;
  premiumUsers: number;
  totalReferrals: number;
}

export interface IUserRepository {
  initSchema?(): Promise<void>;
  upsertUser(telegramId: number, username?: string, firstName?: string): Promise<UserRecord>;
  getUser(telegramId: number): Promise<UserRecord | null>;
  incrementDailyDownload(telegramId: number, todayStr: string): Promise<number>;
  addBonusQuota(telegramId: number, amount: number): Promise<void>;
  grantPremium(telegramId: number, days: number, tier: string): Promise<void>;
  claimTrial(telegramId: number, days: number): Promise<boolean>;
  addReferral(inviterId: number, inviteeId: number): Promise<boolean>;
  getGlobalStats(): Promise<GlobalStats>;
  getAudioCache(trackId: string | number, quality: string, title?: string, artist?: string): Promise<string | null>;
  saveAudioCache(trackId: string | number, quality: string, fileId: string, title?: string, artist?: string): Promise<void>;
  recordPayment(chargeId: string, telegramId: number, payload: string, amount: number): Promise<boolean>;
}

/**
 * In-Memory User Repository for testing, local development, and zero-config fallback.
 */
export class MemoryUserRepository implements IUserRepository {
  private users = new Map<number, UserRecord>();
  private referrals = new Set<string>();
  private audioCache = new Map<string, string>(); // key: `${trackId}:${quality}`
  private processedPayments = new Set<string>();

  public async upsertUser(telegramId: number, username?: string, firstName?: string): Promise<UserRecord> {
    const existing = this.users.get(telegramId);
    const now = new Date().toISOString();

    if (existing) {
      existing.username = username || existing.username;
      existing.firstName = firstName || existing.firstName;
      existing.lastActive = now;
      return existing;
    }

    const newUser: UserRecord = {
      telegramId,
      username: username || '',
      firstName: firstName || 'User',
      totalDownloads: 0,
      dailyDownloadCount: 0,
      dailyDownloadDate: '',
      monthlyDownloadCount: 0,
      monthlyDownloadDate: '',
      bonusQuota: 0,
      isPremium: false,
      hasUsedTrial: false,
      createdAt: now,
      lastActive: now,
    };
    this.users.set(telegramId, newUser);
    return newUser;
  }

  public async getUser(telegramId: number): Promise<UserRecord | null> {
    return this.users.get(telegramId) || null;
  }

  public async incrementDailyDownload(telegramId: number, todayStr: string): Promise<number> {
    let user = this.users.get(telegramId);
    if (!user) {
      user = await this.upsertUser(telegramId);
    }

    const monthStr = todayStr.slice(0, 7);
    user.totalDownloads += 1;
    if (user.dailyDownloadDate !== todayStr) {
      user.dailyDownloadDate = todayStr;
      user.dailyDownloadCount = 1;
    } else {
      user.dailyDownloadCount += 1;
    }

    if (user.monthlyDownloadDate !== monthStr) {
      user.monthlyDownloadDate = monthStr;
      user.monthlyDownloadCount = 1;
    } else {
      user.monthlyDownloadCount = (user.monthlyDownloadCount || 0) + 1;
    }

    return user.dailyDownloadCount;
  }

  public async addBonusQuota(telegramId: number, amount: number): Promise<void> {
    let user = this.users.get(telegramId);
    if (!user) {
      user = await this.upsertUser(telegramId);
    }
    user.bonusQuota += amount;
  }

  public async grantPremium(telegramId: number, days: number, tier: string): Promise<void> {
    let user = this.users.get(telegramId);
    if (!user) {
      user = await this.upsertUser(telegramId);
    }

    user.isPremium = true;
    user.premiumTier = tier;
    if (days >= 9999) {
      user.premiumUntil = undefined; // Lifetime
    } else {
      const expiry = new Date();
      expiry.setDate(expiry.getDate() + days);
      user.premiumUntil = expiry.toISOString();
    }
  }

  public async claimTrial(telegramId: number, days: number = 7): Promise<boolean> {
    let user = this.users.get(telegramId);
    if (!user) {
      user = await this.upsertUser(telegramId);
    }

    if (user.hasUsedTrial) {
      return false;
    }

    user.hasUsedTrial = true;
    user.isPremium = true;
    user.premiumTier = 'trial_7d';
    const expiry = new Date();
    expiry.setDate(expiry.getDate() + days);
    user.premiumUntil = expiry.toISOString();
    return true;
  }

  public async addReferral(inviterId: number, inviteeId: number): Promise<boolean> {
    const key = `${inviterId}:${inviteeId}`;
    if (this.referrals.has(key)) {
      return false;
    }
    this.referrals.add(key);

    const invitee = this.users.get(inviteeId);
    if (invitee) {
      invitee.invitedBy = inviterId;
    }
    return true;
  }

  public async getGlobalStats(): Promise<GlobalStats> {
    let totalDownloads = 0;
    let premiumUsers = 0;
    for (const user of this.users.values()) {
      totalDownloads += user.totalDownloads;
      if (user.isPremium) premiumUsers++;
    }
    return {
      totalUsers: this.users.size,
      totalDownloads,
      premiumUsers,
      totalReferrals: this.referrals.size,
    };
  }

  private normalizeCacheSlug(title?: string, artist?: string): string {
    if (!title) return '';
    return `${title}_${artist || ''}`.toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  public async getAudioCache(
    trackId: string | number,
    quality: string,
    title?: string,
    artist?: string
  ): Promise<string | null> {
    const direct = this.audioCache.get(`${trackId}:${quality}`);
    if (direct) return direct;

    const slug = this.normalizeCacheSlug(title, artist);
    if (slug) {
      return this.audioCache.get(`slug:${slug}:${quality}`) || null;
    }
    return null;
  }

  public async saveAudioCache(
    trackId: string | number,
    quality: string,
    fileId: string,
    title?: string,
    artist?: string
  ): Promise<void> {
    this.audioCache.set(`${trackId}:${quality}`, fileId);
    const slug = this.normalizeCacheSlug(title, artist);
    if (slug) {
      this.audioCache.set(`slug:${slug}:${quality}`, fileId);
    }
  }

  public async recordPayment(chargeId: string, _telegramId: number, _payload: string, _amount: number): Promise<boolean> {
    if (this.processedPayments.has(chargeId)) {
      return false; // Already fulfilled!
    }
    this.processedPayments.add(chargeId);
    return true;
  }
}

/**
 * Neon Serverless PostgreSQL Repository with automatic schema protection & atomic operations.
 */
export class PostgresUserRepository implements IUserRepository {
  private sql: ReturnType<typeof neon>;
  private initPromise?: Promise<void>;

  constructor(databaseUrl: string) {
    this.sql = neon(databaseUrl);
  }

  public async ensureSchema(): Promise<void> {
    if (!this.initPromise) {
      this.initPromise = this.initSchema();
    }
    return this.initPromise;
  }

  public async initSchema(): Promise<void> {
    try {
      await this.sql`
        CREATE TABLE IF NOT EXISTS music_users (
          telegram_id BIGINT PRIMARY KEY,
          username TEXT,
          first_name TEXT,
          total_downloads INTEGER DEFAULT 0,
          daily_download_count INTEGER DEFAULT 0,
          daily_download_date TEXT DEFAULT '',
          monthly_download_count INTEGER DEFAULT 0,
          monthly_download_date TEXT DEFAULT '',
          bonus_quota INTEGER DEFAULT 0,
          is_premium BOOLEAN DEFAULT FALSE,
          premium_tier TEXT DEFAULT '',
          premium_until TEXT DEFAULT '',
          has_used_trial BOOLEAN DEFAULT FALSE,
          invited_by BIGINT DEFAULT 0,
          created_at TEXT DEFAULT '',
          last_active TEXT DEFAULT ''
        );
      `;
      await this.sql`
        ALTER TABLE music_users ADD COLUMN IF NOT EXISTS monthly_download_count INTEGER DEFAULT 0;
      `;
      await this.sql`
        ALTER TABLE music_users ADD COLUMN IF NOT EXISTS monthly_download_date TEXT DEFAULT '';
      `;
      await this.sql`
        CREATE TABLE IF NOT EXISTS music_referrals (
          id SERIAL PRIMARY KEY,
          inviter_id BIGINT NOT NULL,
          invitee_id BIGINT NOT NULL UNIQUE,
          created_at TEXT DEFAULT ''
        );
      `;
      await this.sql`
        CREATE TABLE IF NOT EXISTS music_audio_cache (
          id TEXT PRIMARY KEY,
          file_id TEXT NOT NULL,
          created_at TEXT DEFAULT ''
        );
      `;
      await this.sql`
        CREATE TABLE IF NOT EXISTS music_payments (
          charge_id TEXT PRIMARY KEY,
          telegram_id BIGINT NOT NULL,
          payload TEXT NOT NULL,
          amount INTEGER NOT NULL,
          created_at TEXT DEFAULT ''
        );
      `;
    } catch (err) {
      console.warn('Neon Postgres initSchema error:', err);
    }
  }

  public async upsertUser(telegramId: number, username?: string, firstName?: string): Promise<UserRecord> {
    await this.ensureSchema();
    const now = new Date().toISOString();
    try {
      await this.sql`
        INSERT INTO music_users (telegram_id, username, first_name, created_at, last_active)
        VALUES (${telegramId}, ${username || ''}, ${firstName || 'User'}, ${now}, ${now})
        ON CONFLICT (telegram_id) DO UPDATE SET
          username = EXCLUDED.username,
          first_name = EXCLUDED.first_name,
          last_active = EXCLUDED.last_active;
      `;
    } catch (e) {
      console.error('upsertUser Postgres error:', e);
    }
    return (await this.getUser(telegramId))!;
  }

  public async getUser(telegramId: number): Promise<UserRecord | null> {
    await this.ensureSchema();
    try {
      const rows = (await this.sql`
        SELECT * FROM music_users WHERE telegram_id = ${telegramId} LIMIT 1;
      `) as any[];

      if (!rows || rows.length === 0) return null;
      const r = rows[0];

      return {
        telegramId: Number(r.telegram_id),
        username: r.username,
        firstName: r.first_name,
        totalDownloads: Number(r.total_downloads || 0),
        dailyDownloadCount: Number(r.daily_download_count || 0),
        dailyDownloadDate: r.daily_download_date || '',
        monthlyDownloadCount: Number(r.monthly_download_count || 0),
        monthlyDownloadDate: r.monthly_download_date || '',
        bonusQuota: Number(r.bonus_quota || 0),
        isPremium: Boolean(r.is_premium),
        premiumTier: r.premium_tier,
        premiumUntil: r.premium_until,
        hasUsedTrial: Boolean(r.has_used_trial),
        invitedBy: Number(r.invited_by || 0),
        createdAt: r.created_at || '',
        lastActive: r.last_active || '',
      };
    } catch (e) {
      console.error('getUser Postgres error:', e);
      return null;
    }
  }

  /**
   * Atomic conditional quota increment preventing read-modify-write race conditions.
   */
  public async incrementDailyDownload(telegramId: number, todayStr: string): Promise<number> {
    await this.ensureSchema();
    const now = new Date().toISOString();
    const monthStr = todayStr.slice(0, 7);
    try {
      const rows = (await this.sql`
        INSERT INTO music_users (
          telegram_id, daily_download_date, daily_download_count,
          monthly_download_date, monthly_download_count,
          total_downloads, created_at, last_active
        )
        VALUES (${telegramId}, ${todayStr}, 1, ${monthStr}, 1, 1, ${now}, ${now})
        ON CONFLICT (telegram_id) DO UPDATE SET
          daily_download_count = CASE 
            WHEN music_users.daily_download_date = ${todayStr} THEN music_users.daily_download_count + 1 
            ELSE 1 
          END,
          daily_download_date = ${todayStr},
          monthly_download_count = CASE
            WHEN music_users.monthly_download_date = ${monthStr} THEN COALESCE(music_users.monthly_download_count, 0) + 1
            ELSE 1
          END,
          monthly_download_date = ${monthStr},
          total_downloads = music_users.total_downloads + 1,
          last_active = ${now}
        RETURNING daily_download_count;
      `) as any[];

      return Number(rows?.[0]?.daily_download_count || 1);
    } catch (e) {
      console.error('incrementDailyDownload atomic error:', e);
      return 1;
    }
  }

  public async addBonusQuota(telegramId: number, amount: number): Promise<void> {
    await this.ensureSchema();
    try {
      await this.sql`
        UPDATE music_users
        SET bonus_quota = bonus_quota + ${amount}
        WHERE telegram_id = ${telegramId};
      `;
    } catch (e) {
      console.error('addBonusQuota error:', e);
    }
  }

  public async grantPremium(telegramId: number, days: number, tier: string): Promise<void> {
    await this.ensureSchema();
    const expiry = days >= 9999 ? '' : new Date(Date.now() + days * 86400000).toISOString();
    try {
      await this.sql`
        UPDATE music_users
        SET is_premium = TRUE,
            premium_tier = ${tier},
            premium_until = ${expiry}
        WHERE telegram_id = ${telegramId};
      `;
    } catch (e) {
      console.error('grantPremium error:', e);
    }
  }

  public async claimTrial(telegramId: number, days: number = 7): Promise<boolean> {
    await this.ensureSchema();
    const user = await this.getUser(telegramId);
    if (!user || user.hasUsedTrial) {
      return false;
    }

    const expiry = new Date(Date.now() + days * 86400000).toISOString();
    try {
      await this.sql`
        UPDATE music_users
        SET has_used_trial = TRUE,
            is_premium = TRUE,
            premium_tier = 'trial_7d',
            premium_until = ${expiry}
        WHERE telegram_id = ${telegramId};
      `;
      return true;
    } catch (e) {
      console.error('claimTrial error:', e);
      return false;
    }
  }

  public async addReferral(inviterId: number, inviteeId: number): Promise<boolean> {
    await this.ensureSchema();
    const now = new Date().toISOString();
    try {
      await this.sql`
        INSERT INTO music_referrals (inviter_id, invitee_id, created_at)
        VALUES (${inviterId}, ${inviteeId}, ${now});
      `;
      await this.sql`
        UPDATE music_users SET invited_by = ${inviterId} WHERE telegram_id = ${inviteeId};
      `;
      return true;
    } catch (e) {
      return false;
    }
  }

  public async getGlobalStats(): Promise<GlobalStats> {
    await this.ensureSchema();
    try {
      const userRows = (await this.sql`
        SELECT 
          COUNT(*)::int as total_users,
          COALESCE(SUM(total_downloads), 0)::int as total_downloads,
          COALESCE(COUNT(*) FILTER (WHERE is_premium = true), 0)::int as premium_users
        FROM music_users;
      `) as any[];

      const refRows = (await this.sql`
        SELECT COUNT(*)::int as total_referrals FROM music_referrals;
      `) as any[];

      return {
        totalUsers: userRows?.[0]?.total_users || 0,
        totalDownloads: userRows?.[0]?.total_downloads || 0,
        premiumUsers: userRows?.[0]?.premium_users || 0,
        totalReferrals: refRows?.[0]?.total_referrals || 0,
      };
    } catch (err) {
      console.warn('getGlobalStats error:', err);
      return {
        totalUsers: 0,
        totalDownloads: 0,
        premiumUsers: 0,
        totalReferrals: 0,
      };
    }
  }

  private normalizeCacheSlug(title?: string, artist?: string): string {
    if (!title) return '';
    return `${title}_${artist || ''}`.toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  public async getAudioCache(
    trackId: string | number,
    quality: string,
    title?: string,
    artist?: string
  ): Promise<string | null> {
    await this.ensureSchema();
    try {
      const key = `${trackId}:${quality}`;
      const slug = this.normalizeCacheSlug(title, artist);
      const slugKey = slug ? `slug:${slug}:${quality}` : '';

      const rows = (await this.sql`
        SELECT file_id FROM music_audio_cache 
        WHERE id = ${key} OR (id = ${slugKey} AND ${slugKey} != '')
        LIMIT 1;
      `) as any[];
      return rows && rows.length > 0 ? rows[0].file_id : null;
    } catch (err) {
      console.warn('getAudioCache error:', err);
      return null;
    }
  }

  public async saveAudioCache(
    trackId: string | number,
    quality: string,
    fileId: string,
    title?: string,
    artist?: string
  ): Promise<void> {
    await this.ensureSchema();
    const key = `${trackId}:${quality}`;
    const slug = this.normalizeCacheSlug(title, artist);
    const slugKey = slug ? `slug:${slug}:${quality}` : '';
    const now = new Date().toISOString();

    try {
      await this.sql`
        INSERT INTO music_audio_cache (id, file_id, created_at)
        VALUES (${key}, ${fileId}, ${now})
        ON CONFLICT (id) DO UPDATE SET file_id = EXCLUDED.file_id;
      `;

      if (slugKey) {
        await this.sql`
          INSERT INTO music_audio_cache (id, file_id, created_at)
          VALUES (${slugKey}, ${fileId}, ${now})
          ON CONFLICT (id) DO UPDATE SET file_id = EXCLUDED.file_id;
        `;
      }
    } catch (err) {
      console.warn('saveAudioCache error:', err);
    }
  }

  public async recordPayment(chargeId: string, telegramId: number, payload: string, amount: number): Promise<boolean> {
    await this.ensureSchema();
    const now = new Date().toISOString();
    try {
      const res = (await this.sql`
        INSERT INTO music_payments (charge_id, telegram_id, payload, amount, created_at)
        VALUES (${chargeId}, ${telegramId}, ${payload}, ${amount}, ${now})
        ON CONFLICT (charge_id) DO NOTHING
        RETURNING charge_id;
      `) as any[];

      // If returned array has element, it was inserted fresh. If empty, duplicate webhook retry!
      return Array.isArray(res) && res.length > 0;
    } catch (err) {
      console.warn('recordPayment error:', err);
      return true; // Fallback to allowing fulfillment if DB write error
    }
  }
}

/**
 * Repository Factory: Uses Neon PostgreSQL if DATABASE_URL is set, otherwise Memory repository.
 */
export function createUserRepository(databaseUrl?: string): IUserRepository {
  if (databaseUrl && databaseUrl.startsWith('postgres')) {
    const repo = new PostgresUserRepository(databaseUrl);
    repo.ensureSchema().catch((err) => console.warn('Schema init deferred:', err));
    return repo;
  }
  return new MemoryUserRepository();
}
