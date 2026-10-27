import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryUserRepository } from '../src/repositories/user.repository.js';
import { UserService, PLANS } from '../src/services/user.service.js';

describe('UserService & Freemium Quota Tests', () => {
  let repo: MemoryUserRepository;
  let userService: UserService;

  beforeEach(() => {
    repo = new MemoryUserRepository();
    userService = new UserService(repo);
  });

  it('should grant 5 free downloads per day to new users', async () => {
    const userId = 1001;
    await userService.ensureUser(userId, 'musicfan', 'Fan');

    // 1st to 5th download should be permitted
    for (let i = 0; i < 5; i++) {
      const quota = await userService.checkDailyQuota(userId);
      expect(quota.canDownload).toBe(true);
      expect(quota.maxLimit).toBe(5);
      await userService.recordDownload(userId);
    }

    // 6th download must be BLOCKED
    const blockedQuota = await userService.checkDailyQuota(userId);
    expect(blockedQuota.canDownload).toBe(false);
    expect(blockedQuota.usedToday).toBe(5);
  });

  it('should bypass quota for premium users', async () => {
    const userId = 1002;
    await userService.ensureUser(userId, 'vipuser', 'VIP');

    // Exhaust 5 downloads
    for (let i = 0; i < 5; i++) {
      await userService.recordDownload(userId);
    }
    expect((await userService.checkDailyQuota(userId)).canDownload).toBe(false);

    // Grant 1 month premium
    await userService.grantSubscription(userId, 'plan_1m');

    const premiumQuota = await userService.checkDailyQuota(userId);
    expect(premiumQuota.canDownload).toBe(true);
    expect(premiumQuota.isPremium).toBe(true);
    expect(premiumQuota.maxLimit).toBe(50);
    expect(premiumQuota.resetIntervalHours).toBe(12);
  });

  it('should allow 1-time 7-day Free Trial and reject duplicate claims', async () => {
    const userId = 1003;
    await userService.ensureUser(userId, 'trialuser', 'Trial');

    // First claim must succeed
    const firstClaim = await userService.claimFreeTrial(userId);
    expect(firstClaim.success).toBe(true);
    expect((await userService.checkDailyQuota(userId)).isPremium).toBe(true);

    // Second claim must be rejected
    const secondClaim = await userService.claimFreeTrial(userId);
    expect(secondClaim.success).toBe(false);
    expect(secondClaim.message).toContain('sudah pernah mengklaim');
  });

  it('should process referral properly and reject self-referral', async () => {
    const inviterId = 2001;
    const inviteeId = 2002;

    await userService.ensureUser(inviterId, 'inviter', 'Alice');
    await userService.ensureUser(inviteeId, 'invitee', 'Bob');

    // 1. Self-referral must be rejected
    const selfRef = await userService.processReferral(inviterId, inviterId);
    expect(selfRef).toBeNull();

    // 2. Legitimate referral gives +3 bonus quota to both
    const validRef = await userService.processReferral(inviterId, inviteeId);
    expect(validRef).not.toBeNull();
    expect(validRef?.success).toBe(true);
    expect(validRef?.inviterReward).toBe(3);
    expect(validRef?.inviteeReward).toBe(3);

    // Inviter quota should now be 5 + 3 = 8
    const inviterQuota = await userService.checkDailyQuota(inviterId);
    expect(inviterQuota.maxLimit).toBe(8);

    // Invitee quota should now be 5 + 3 = 8
    const inviteeQuota = await userService.checkDailyQuota(inviteeId);
    expect(inviteeQuota.maxLimit).toBe(8);

    // 3. Duplicate referral must be rejected
    const duplicateRef = await userService.processReferral(inviterId, inviteeId);
    expect(duplicateRef).toBeNull();
  });

  it('should correctly configure Telegram Stars plans and boost catalog', () => {
    expect(PLANS.plan_1m.stars).toBe(25);
    expect(PLANS.plan_3m.stars).toBe(60);
    expect(PLANS.plan_lifetime.stars).toBe(99);
  });

  it('should correctly calculate 12-hour cycle keys for Premium and 24-hour for Free', () => {
    const morningDate = new Date('2026-10-26T08:30:00Z'); // 08:30 UTC
    const eveningDate = new Date('2026-10-26T18:30:00Z'); // 18:30 UTC

    // Free users always get YYYY-MM-DD
    expect(userService.getQuotaCycleKey(false, morningDate)).toBe('2026-10-26');
    expect(userService.getQuotaCycleKey(false, eveningDate)).toBe('2026-10-26');

    // Premium users get 12-hour slots: -00 for 00:00-11:59 UTC, -12 for 12:00-23:59 UTC
    expect(userService.getQuotaCycleKey(true, morningDate)).toBe('2026-10-26-00');
    expect(userService.getQuotaCycleKey(true, eveningDate)).toBe('2026-10-26-12');
  });

  it('should allow purchasing Extra Quota Boost (+25 or +50 songs) when Premium limit is reached', async () => {
    const userId = 3001;
    await userService.ensureUser(userId, 'heavy_listener', 'Heavy');
    await userService.grantSubscription(userId, 'plan_1m');

    // Add +25 songs boost
    const boostSuccess = await userService.addExtraBoost(userId, 'boost_25');
    expect(boostSuccess).toBe(true);

    const quota = await userService.checkDailyQuota(userId);
    expect(quota.maxLimit).toBe(75); // 50 base + 25 boost
  });
});
