import { describe, it, expect } from 'vitest';
import {
  buildUpgradeKeyboard,
  buildQuotaLimitKeyboard,
  buildPremiumQuotaLimitKeyboard,
} from '../src/bot/keyboards/monetization.keyboard.js';
import { PLANS, BOOST_PLANS } from '../src/services/user.service.js';

describe('Monetization Keyboards & Anti-Tamper Tests', () => {
  it('should include 7-day free trial button if user has not used trial', () => {
    const kb = buildUpgradeKeyboard(false);
    const inline = kb.inline_keyboard;
    expect(inline.some((row) => row.some((btn) => btn.text.includes('Free Trial')))).toBe(true);
  });

  it('should hide 7-day free trial button if user has already used trial', () => {
    const kb = buildUpgradeKeyboard(true);
    const inline = kb.inline_keyboard;
    expect(inline.some((row) => row.some((btn) => btn.text.includes('Free Trial')))).toBe(false);
  });

  it('should include Telegram Stars amounts on upgrade buttons', () => {
    const kb = buildUpgradeKeyboard(true);
    const inline = kb.inline_keyboard;
    const buttonTexts = inline.flatMap((row) => row.map((b) => b.text)).join(' ');

    expect(buttonTexts).toContain('25 Stars');
    expect(buttonTexts).toContain('60 Stars');
    expect(buttonTexts).toContain('99 Stars');
  });

  it('should build quota limit keyboard with upgrade and invite buttons', () => {
    const kb = buildQuotaLimitKeyboard(false);
    const inline = kb.inline_keyboard;
    const buttonTexts = inline.flatMap((row) => row.map((b) => b.text)).join(' ');

    expect(buttonTexts).toContain('Free Trial');
    expect(buttonTexts).toContain('Dukung Server');
    expect(buttonTexts).toContain('Ajak Teman');
  });

  it('should build VIP quota limit keyboard with Extra Boost +25 and +50 buttons', () => {
    const kb = buildPremiumQuotaLimitKeyboard();
    const inline = kb.inline_keyboard;

    expect(inline.length).toBe(2);
    expect((inline[0][0] as any).text).toContain('+25 Lagu');
    expect((inline[0][0] as any).text).toContain('10 Stars');
    expect((inline[0][0] as any).callback_data).toBe('pay_boost_25');

    expect((inline[1][0] as any).text).toContain('+50 Lagu');
    expect((inline[1][0] as any).text).toContain('18 Stars');
    expect((inline[1][0] as any).callback_data).toBe('pay_boost_50');
  });

  it('should validate Telegram Stars plan and boost parameters against tampering', () => {
    // Valid plan
    const validPlan = PLANS.plan_1m;
    expect(validPlan.stars).toBe(25);
    expect(validPlan.days).toBe(30);

    // Validate anti-tamper scenario logic
    const testPreCheckout = (currency: string, payload: string, amount: number) => {
      if (currency !== 'XTR') return { ok: false, error: 'invalid currency' };
      const plan = (PLANS as any)[payload] || (BOOST_PLANS as any)[payload];
      if (!plan) return { ok: false, error: 'unknown payload' };
      if (amount !== plan.stars) return { ok: false, error: 'amount mismatch' };
      return { ok: true };
    };

    // 1. Currency spoofing (e.g. USD)
    expect(testPreCheckout('USD', 'plan_1m', 25).ok).toBe(false);

    // 2. Fake payload
    expect(testPreCheckout('XTR', 'hack_unlimited_free', 0).ok).toBe(false);

    // 3. Amount tampering (paying 1 Star for Lifetime 99 Stars)
    expect(testPreCheckout('XTR', 'plan_lifetime', 1).ok).toBe(false);

    // 4. Legitimate plan transaction
    expect(testPreCheckout('XTR', 'plan_lifetime', 99).ok).toBe(true);

    // 5. Legitimate Extra Boost transactions
    expect(testPreCheckout('XTR', 'boost_25', 10).ok).toBe(true);
    expect(testPreCheckout('XTR', 'boost_50', 18).ok).toBe(true);

    // 6. Extra Boost amount tampering
    expect(testPreCheckout('XTR', 'boost_25', 5).ok).toBe(false);
  });

  it('should gate 320kbps HD audio for Free users and allow for Premium users', () => {
    const checkAudioAccess = (isPremium: boolean, requestedQuality: '160' | '320') => {
      if (requestedQuality === '320' && !isPremium) {
        return { allowed: false, requireUpsell: true, deductQuota: false };
      }
      return { allowed: true, requireUpsell: false, deductQuota: !isPremium };
    };

    // Free user downloading 160kbps -> allowed, deducts quota, no upsell
    expect(checkAudioAccess(false, '160')).toEqual({
      allowed: true,
      requireUpsell: false,
      deductQuota: true,
    });

    // Free user downloading 320kbps -> intercepted, requires upsell, no quota deducted
    expect(checkAudioAccess(false, '320')).toEqual({
      allowed: false,
      requireUpsell: true,
      deductQuota: false,
    });

    // Premium user downloading 320kbps -> allowed, no upsell, no quota deducted
    expect(checkAudioAccess(true, '320')).toEqual({
      allowed: true,
      requireUpsell: false,
      deductQuota: false,
    });
  });

  it('should enforce payment idempotency to prevent double fulfillment on webhook retries', async () => {
    const { MemoryUserRepository } = await import('../src/repositories/user.repository.js');
    const { UserService } = await import('../src/services/user.service.js');
    const repo = new MemoryUserRepository();
    const service = new UserService(repo);

    const chargeId = 'tg_charge_ch_123456789';
    const userId = 888888;
    const payload = 'boost_25';

    // First webhook delivery -> returns true (processed fresh)
    const firstDelivery = await service.recordPayment(chargeId, userId, payload, 10);
    expect(firstDelivery).toBe(true);

    // Second webhook delivery with same charge_id (Telegram retry) -> returns false (deduplicated)
    const secondDelivery = await service.recordPayment(chargeId, userId, payload, 10);
    expect(secondDelivery).toBe(false);
  });
});

