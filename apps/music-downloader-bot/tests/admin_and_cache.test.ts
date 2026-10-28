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

    // Dual-key caching: retrieval by different trackId but same title and artist
    await service.saveAudioCache(99991, '160', 'tg_file_id_tulus', 'Hati Hati di Jalan', 'Tulus');
    // Different ID (e.g. from album search), but exact same song title & artist
    const hitBySlug = await service.getAudioCache(99992, '160', 'Hati Hati di Jalan', 'Tulus');
    expect(hitBySlug).toBe('tg_file_id_tulus');
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

  it('should automatically grant admin owner lifetime VIP and allow /grant command', async () => {
    const repo = new MemoryUserRepository();
    const adminId = 7741750167;
    const service = new UserService(repo, adminId);

    // Verify owner profile is recognized as lifetime VIP
    const ownerProfile = await service.getUserProfile(adminId);
    expect(ownerProfile.isPremium).toBe(true);
    expect(ownerProfile.isOwner).toBe(true);
    expect(ownerProfile.daysLeft).toBe(9999);

    const ownerQuota = await service.checkDailyQuota(adminId);
    expect(ownerQuota.canDownload).toBe(true);
    expect(ownerQuota.maxLimit).toBe(999999);

    // Mock bot for grant command
    const mockBot: any = {
      commands: new Map<string, Function>(),
      command(names: string | string[], fn: Function) {
        const list = Array.isArray(names) ? names : [names];
        list.forEach((n) => this.commands.set(n, fn));
      },
    };
    registerAdminHandlers(mockBot, service, adminId);
    const grantHandler = mockBot.commands.get('grant');
    expect(grantHandler).toBeDefined();

    let grantReply = '';
    const grantCtx: any = {
      from: { id: adminId },
      message: { text: '/grant 555555 30' },
      match: '555555 30',
      reply: (msg: string) => {
        grantReply = msg;
      },
    };

    await grantHandler(grantCtx);
    expect(grantReply).toContain('Berhasil');
    expect(grantReply).toContain('555555');

    const grantedUser = await service.getUserProfile(555555);
    expect(grantedUser.isPremium).toBe(true);
    expect(grantedUser.daysLeft).toBe(30);
  });

  it('should list registered users via /users command for admin', async () => {
    const repo = new MemoryUserRepository();
    const service = new UserService(repo);
    const adminId = 999999;

    await service.ensureUser(111, 'alice', 'Alice');
    await service.ensureUser(222, 'bob', 'Bob');

    const mockBot: any = {
      commands: new Map<string, Function>(),
      command(names: string | string[], fn: Function) {
        const list = Array.isArray(names) ? names : [names];
        list.forEach((n) => this.commands.set(n, fn));
      },
      callbackQuery() {},
    };

    registerAdminHandlers(mockBot, service, adminId);
    const usersHandler = mockBot.commands.get('users');
    expect(usersHandler).toBeDefined();

    let replyText = '';
    const ctx: any = {
      from: { id: adminId },
      message: { text: '/users' },
      reply: (msg: string) => {
        replyText = msg;
      },
    };

    await usersHandler(ctx);
    expect(replyText).toContain('DAFTAR PENGGUNA TERDAFTAR');
    expect(replyText).toContain('Alice');
    expect(replyText).toContain('Bob');
    expect(replyText).toContain('111');
    expect(replyText).toContain('222');
  });

  it('should broadcast message to all users via /broadcast command for admin', async () => {
    const repo = new MemoryUserRepository();
    const service = new UserService(repo);
    const adminId = 999999;

    await service.ensureUser(101, 'user1', 'User One');
    await service.ensureUser(102, 'user2', 'User Two');

    const userIds = await service.getAllUserIds();
    expect(userIds).toEqual(expect.arrayContaining([101, 102]));

    const mockBot: any = {
      commands: new Map<string, Function>(),
      command(names: string | string[], fn: Function) {
        const list = Array.isArray(names) ? names : [names];
        list.forEach((n) => this.commands.set(n, fn));
      },
      callbackQuery() {},
    };

    registerAdminHandlers(mockBot, service, adminId);
    const broadcastHandler = mockBot.commands.get('broadcast');
    expect(broadcastHandler).toBeDefined();

    // 1. Non-admin call should be rejected
    let nonAdminReply = '';
    const nonAdminCtx: any = {
      from: { id: 101 },
      message: { text: '/broadcast Halo' },
      reply: (msg: string) => {
        nonAdminReply = msg;
      },
    };
    await broadcastHandler(nonAdminCtx);
    expect(nonAdminReply).toContain('Akses ditolak');

    // 2. Admin call without message shows guide
    let guideReply = '';
    const emptyCtx: any = {
      from: { id: adminId },
      message: { text: '/broadcast' },
      reply: (msg: string) => {
        guideReply = msg;
      },
    };
    await broadcastHandler(emptyCtx);
    expect(guideReply).toContain('PANDUAN BROADCAST');

    // 3. Admin broadcast execution
    const sentMessages: { targetId: number; text: string }[] = [];
    let initialStatusReply = '';
    let editedReport = '';

    const adminCtx: any = {
      from: { id: adminId },
      chat: { id: adminId },
      message: { text: '/broadcast Pengumuman Penting Server' },
      reply: (msg: string) => {
        initialStatusReply = msg;
        return { message_id: 1234 };
      },
      api: {
        sendMessage: async (targetId: number, text: string) => {
          sentMessages.push({ targetId, text });
        },
        editMessageText: async (_chatId: number, _msgId: number, text: string) => {
          editedReport = text;
        },
      },
    };

    await broadcastHandler(adminCtx);

    expect(initialStatusReply).toContain('Memulai pengiriman broadcast');
    expect(sentMessages.length).toBe(2);
    expect(sentMessages[0].text).toBe('Pengumuman Penting Server');
    expect(sentMessages[1].text).toBe('Pengumuman Penting Server');
    expect(editedReport).toContain('LAPORAN HASIL PENGIRIMAN BROADCAST');
    expect(editedReport).toContain('Berhasil Terkirim:* 2 user');
  });
});
