import { describe, it, expect } from 'vitest';
import { MemoryUserRepository } from '../src/repositories/user.repository.js';
import { UserService } from '../src/services/user.service.js';
import { registerAdminHandlers } from '../src/bot/handlers/admin.handler.js';

describe('Admin Handler & Audio Cache Unit Tests', () => {
  it('should save and retrieve audio file_id from cache', async () => {
    const repo = new MemoryUserRepository();
    const service = new UserService(repo);

    // Initial cache is null
    expect(await service.getAudioCache(12345, '160')).toBeNull();
    expect(await service.getAudioCache(12345, '320')).toBeNull();

    // Save audio file_id for 160kbps
    await service.saveAudioCache(12345, '160', 'tg_audio_file_id_standard_160');
    expect(await service.getAudioCache(12345, '160')).toBe('tg_audio_file_id_standard_160');
    expect(await service.getAudioCache(12345, '320')).toBeNull();

    // Save audio file_id for 320kbps
    await service.saveAudioCache(12345, '320', 'tg_audio_file_id_hd_320');
    expect(await service.getAudioCache(12345, '320')).toBe('tg_audio_file_id_hd_320');
  });

  it('should compute accurate global statistics across users and downloads', async () => {
    const repo = new MemoryUserRepository();
    const service = new UserService(repo);

    // Initial stats
    let stats = await service.getGlobalStats();
    expect(stats.totalUsers).toBe(0);
    expect(stats.totalDownloads).toBe(0);
    expect(stats.premiumUsers).toBe(0);
    expect(stats.totalReferrals).toBe(0);

    // Create user 1 and simulate downloads
    await service.ensureUser(1001, 'user_one', 'User One');
    await service.recordDownload(1001);
    await service.recordDownload(1001);

    // Create user 2 with premium VIP
    await service.ensureUser(1002, 'user_two', 'User Two');
    await service.grantSubscription(1002, 'plan_1m');
    await service.recordDownload(1002);

    // Add referral
    await service.processReferral(1001, 1003);

    stats = await service.getGlobalStats();
    expect(stats.totalUsers).toBe(3); // 1001, 1002, 1003
    expect(stats.totalDownloads).toBe(3); // 2 + 1
    expect(stats.premiumUsers).toBe(1); // 1002
    expect(stats.totalReferrals).toBe(1); // 1001 -> 1003
  });

  it('should guard /stats command by ADMIN_ID', async () => {
    const repo = new MemoryUserRepository();
    const service = new UserService(repo);
    const mockBot: any = {
      commands: new Map<string, Function>(),
      command(names: string | string[], fn: Function) {
        const list = Array.isArray(names) ? names : [names];
        list.forEach((n) => this.commands.set(n, fn));
      },
    };

    const adminId = 999999;
    registerAdminHandlers(mockBot, service, adminId);

    const statsHandler = mockBot.commands.get('stats');
    expect(statsHandler).toBeDefined();

    // Non-admin call
    let repliedText = '';
    const nonAdminCtx: any = {
      from: { id: 111111 },
      reply: (msg: string) => {
        repliedText = msg;
      },
    };
    await statsHandler(nonAdminCtx);
    expect(repliedText).toContain('Akses ditolak');

    // Admin call
    let adminCard = '';
    const adminCtx: any = {
      from: { id: adminId },
      reply: (msg: string) => {
        adminCard = msg;
      },
    };
    await statsHandler(adminCtx);
    expect(adminCard).toContain('DASHBOARD STATISTIK');
    expect(adminCard).toContain('Total Pengguna Terdaftar');
  });
});
