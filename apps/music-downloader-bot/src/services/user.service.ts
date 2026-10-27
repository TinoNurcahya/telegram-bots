import { IUserRepository, UserRecord } from '../repositories/user.repository.js';

export interface QuotaCheckResult {
  canDownload: boolean;
  usedToday: number;
  maxLimit: number;
  isPremium: boolean;
  daysLeft?: number;
  resetIntervalHours?: number;
}

export const PLANS: Record<string, { title: string; description: string; stars: number; days: number }> = {
  plan_1m: {
    title: 'Donasi Operasional Server (Supporter 1 Bulan)',
    description: 'Donasi pemeliharaan server 30 hari. Apresiasi: Status Supporter VIP 50 lagu/12 jam & HD 320kbps.',
    stars: 25,
    days: 30,
  },
  plan_3m: {
    title: 'Donasi Operasional Server (Supporter 3 Bulan)',
    description: 'Donasi pemeliharaan server 90 hari. Apresiasi: Status Supporter VIP 50 lagu/12 jam & HD 320kbps.',
    stars: 60,
    days: 90,
  },
  plan_lifetime: {
    title: 'Donasi Operasional Server (Lifetime Backer)',
    description: 'Donasi pemeliharaan permanen. Apresiasi: Status Supporter VIP seumur hidup.',
    stars: 99,
    days: 9999,
  },
};

export const BOOST_PLANS: Record<string, { title: string; description: string; stars: number; songs: number }> = {
  boost_25: {
    title: 'Donasi Server Boost +25 Lagu',
    description: 'Donasi pemeliharaan server dengan bonus apresiasi kuota 25 lagu instan.',
    stars: 10,
    songs: 25,
  },
  boost_50: {
    title: 'Donasi Server Boost +50 Lagu',
    description: 'Donasi pemeliharaan server dengan bonus apresiasi kuota 50 lagu instan.',
    stars: 18,
    songs: 50,
  },
};

export class UserService {
  constructor(private repo: IUserRepository, private adminId: number = 0) {}

  /**
   * Get quota cycle key.
   * - Free users: "YYYY-MM-DD" (24-hour cycle, resets at 00:00 UTC / 07:00 WIB)
   * - Premium users: "YYYY-MM-DD-00" or "YYYY-MM-DD-12" (12-hour cycle, resets at 07:00 WIB and 19:00 WIB)
   */
  public getQuotaCycleKey(isPremium: boolean, date: Date = new Date()): string {
    const isoDate = date.toISOString().split('T')[0];
    if (!isPremium) {
      return isoDate;
    }
    const utcHours = date.getUTCHours();
    const cycleSlot = utcHours < 12 ? '00' : '12';
    return `${isoDate}-${cycleSlot}`;
  }

  public async ensureUser(telegramId: number, username?: string, firstName?: string): Promise<UserRecord> {
    return this.repo.upsertUser(telegramId, username, firstName);
  }

  public async getUserProfile(telegramId: number): Promise<UserRecord & { daysLeft: number; isOwner?: boolean }> {
    let user = await this.repo.getUser(telegramId);
    if (!user) {
      user = await this.repo.upsertUser(telegramId);
    }

    const isOwner = this.adminId > 0 && telegramId === this.adminId;

    if (isOwner) {
      user.isPremium = true;
      user.premiumTier = 'lifetime';
      return { ...user, daysLeft: 9999, isOwner: true };
    }

    let daysLeft = 0;
    if (user.isPremium) {
      if (user.premiumTier === 'lifetime' || !user.premiumUntil) {
        daysLeft = 9999;
      } else {
        const expiry = new Date(user.premiumUntil).getTime();
        const now = Date.now();
        if (expiry > now) {
          daysLeft = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
        } else {
          // Expired
          user.isPremium = false;
        }
      }
    }

    return { ...user, daysLeft, isOwner: false };
  }

  public async checkDailyQuota(telegramId: number): Promise<QuotaCheckResult> {
    const profile = await this.getUserProfile(telegramId);

    // Bot Owner has unlimited downloads without cycle limits
    if (profile.isOwner) {
      return {
        canDownload: true,
        usedToday: profile.dailyDownloadCount || 0,
        maxLimit: 999999,
        isPremium: true,
        daysLeft: 9999,
        resetIntervalHours: 0,
      };
    }

    const cycleKey = this.getQuotaCycleKey(profile.isPremium);
    const usedInCycle = profile.dailyDownloadDate === cycleKey ? profile.dailyDownloadCount : 0;

    if (profile.isPremium) {
      // 50 songs per 12-hour cycle + bonus quota
      const maxLimit = 50 + (profile.bonusQuota || 0);
      return {
        canDownload: usedInCycle < maxLimit,
        usedToday: usedInCycle,
        maxLimit,
        isPremium: true,
        daysLeft: profile.daysLeft,
        resetIntervalHours: 12,
      };
    }

    // Free users: 5 songs per 24 hours + bonus quota
    const maxLimit = 5 + (profile.bonusQuota || 0);

    return {
      canDownload: usedInCycle < maxLimit,
      usedToday: usedInCycle,
      maxLimit,
      isPremium: false,
      resetIntervalHours: 24,
    };
  }

  public async recordDownload(telegramId: number): Promise<number> {
    const profile = await this.getUserProfile(telegramId);
    const cycleKey = this.getQuotaCycleKey(profile.isPremium);
    return this.repo.incrementDailyDownload(telegramId, cycleKey);
  }

  public async addExtraBoost(telegramId: number, boostKey: string): Promise<boolean> {
    const boost = BOOST_PLANS[boostKey];
    if (!boost) return false;

    await this.repo.addBonusQuota(telegramId, boost.songs);
    return true;
  }

  public async claimFreeTrial(telegramId: number): Promise<{ success: boolean; message: string }> {
    const user = await this.repo.getUser(telegramId);
    if (user?.hasUsedTrial) {
      return {
        success: false,
        message: 'Anda sudah pernah mengklaim Free Trial 7 Hari sebelumnya.',
      };
    }

    const claimed = await this.repo.claimTrial(telegramId, 7);
    if (claimed) {
      return {
        success: true,
        message: 'Selamat! Free Trial 7 Hari berhasil diaktifkan. Anda kini menikmati unduhan tanpa batas!',
      };
    }

    return {
      success: false,
      message: 'Gagal mengklaim Free Trial. Silakan coba lagi nanti.',
    };
  }

  public async processReferral(
    inviterId: number,
    inviteeId: number
  ): Promise<{ success: boolean; inviterReward: number; inviteeReward: number } | null> {
    if (inviterId === inviteeId) {
      return null; // Self-referral blocked
    }

    const inviter = await this.repo.getUser(inviterId);
    if (!inviter) {
      return null;
    }

    const invitee = await this.repo.getUser(inviteeId);
    if (invitee && (invitee.invitedBy || invitee.totalDownloads > 0)) {
      return null; // Already active or referred
    }

    const added = await this.repo.addReferral(inviterId, inviteeId);
    if (!added) {
      return null;
    }

    // Reward both parties: +3 bonus quota
    await this.repo.addBonusQuota(inviterId, 3);
    await this.repo.addBonusQuota(inviteeId, 3);

    return {
      success: true,
      inviterReward: 3,
      inviteeReward: 3,
    };
  }

  public async grantSubscription(telegramId: number, planKey: string): Promise<boolean> {
    if (planKey === 'lifetime' || planKey === 'plan_lifetime') {
      await this.repo.grantPremium(telegramId, 9999, 'lifetime');
      return true;
    }
    const plan = PLANS[planKey];
    if (plan) {
      await this.repo.grantPremium(telegramId, plan.days, planKey.replace('plan_', ''));
      return true;
    }
    const days = parseInt(planKey, 10);
    if (!isNaN(days) && days > 0) {
      await this.repo.grantPremium(telegramId, days, `manual_${days}d`);
      return true;
    }
    return false;
  }

  public async getGlobalStats() {
    return this.repo.getGlobalStats();
  }

  public async getAudioCache(trackId: string | number, quality: string): Promise<string | null> {
    return this.repo.getAudioCache(trackId, quality);
  }

  public async saveAudioCache(trackId: string | number, quality: string, fileId: string): Promise<void> {
    return this.repo.saveAudioCache(trackId, quality, fileId);
  }

  public async recordPayment(chargeId: string, telegramId: number, payload: string, amount: number): Promise<boolean> {
    return this.repo.recordPayment(chargeId, telegramId, payload, amount);
  }
}

