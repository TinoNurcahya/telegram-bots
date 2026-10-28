import { describe, it, expect, vi } from 'vitest';
import { registerInlineHandlers } from '../src/bot/handlers/inline.handler.js';
import { registerMusicHandlers } from '../src/bot/handlers/music.handler.js';
import { MemoryUserRepository } from '../src/repositories/user.repository.js';
import { UserService } from '../src/services/user.service.js';
import { MusicService } from '../src/services/music.service.js';
import { LyricsService } from '../src/services/lyrics.service.js';

describe('Inline Query Handler & Hybrid Delivery Unit Tests', () => {
  it('should return prompt button when inline query is empty', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();

    let registeredHandler: Function | undefined;
    const mockBot = {
      on(event: string, fn: Function) {
        if (event === 'inline_query') registeredHandler = fn;
      },
    };

    registerInlineHandlers(mockBot, musicService, userService);
    expect(registeredHandler).toBeDefined();

    let answeredResults: any[] = [];
    let answeredOptions: any = {};
    const ctx: any = {
      inlineQuery: { query: '' },
      from: { id: 12345 },
      me: { username: 'Musicdownloader2001_bot' },
      answerInlineQuery: async (results: any[], options: any) => {
        answeredResults = results;
        answeredOptions = options;
      },
    };

    await registeredHandler!(ctx);
    expect(answeredResults).toEqual([]);
    expect(answeredOptions.button?.text).toContain('Ketik judul lagu');
  });

  it('should display quota limit card when user has exhausted daily quota', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();

    const userId = 88888;
    await userService.ensureUser(userId);

    // Consume all 5 daily downloads for free user
    const cycle = userService.getQuotaCycleKey(false);
    for (let i = 0; i < 5; i++) {
      await repo.incrementDailyDownload(userId, cycle);
    }

    let inlineHandler: Function | undefined;
    const mockBot = {
      on(event: string, fn: Function) {
        if (event === 'inline_query') inlineHandler = fn;
      },
    };

    registerInlineHandlers(mockBot, musicService, userService);

    let answeredResults: any[] = [];
    const ctx: any = {
      inlineQuery: { query: 'Coldplay Yellow' },
      from: { id: userId },
      me: { username: 'Musicdownloader2001_bot' },
      answerInlineQuery: async (results: any[]) => {
        answeredResults = results;
      },
    };

    await inlineHandler!(ctx);
    expect(answeredResults.length).toBe(1);
    expect(answeredResults[0].type).toBe('article');
    expect(answeredResults[0].id).toBe('quota_limit_exceeded');
    expect(answeredResults[0].title).toContain('Batas Kuota Unduhan Tercapai');
  });

  it('should prioritize cached audio file_id when song is already in Telegram cache', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();

    // Cache a known track
    await userService.saveAudioCache('1001', '160', 'tg_file_id_cached_song_1001', 'Test Song', 'Test Artist');

    // Mock searchTracks to return this track
    vi.spyOn(musicService, 'searchTracks').mockResolvedValue([
      {
        id: 1001,
        title: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
        duration: 200,
        durationFormatted: '03:20',
        coverUrl: 'https://example.com/cover.jpg',
        previewUrl: 'https://example.com/preview.mp3',
        externalUrl: '',
        source: 'deezer',
      },
    ]);

    let inlineHandler: Function | undefined;
    const mockBot = {
      on(event: string, fn: Function) {
        if (event === 'inline_query') inlineHandler = fn;
      },
    };

    registerInlineHandlers(mockBot, musicService, userService);

    let answeredResults: any[] = [];
    const ctx: any = {
      inlineQuery: { query: 'Test Song' },
      from: { id: 99999 },
      me: { username: 'Musicdownloader2001_bot' },
      answerInlineQuery: async (results: any[]) => {
        answeredResults = results;
      },
    };

    await inlineHandler!(ctx);
    expect(answeredResults.length).toBe(1);
    expect(answeredResults[0].type).toBe('audio');
    expect(answeredResults[0].audio_file_id).toBe('tg_file_id_cached_song_1001');
    expect(answeredResults[0].id).toContain('audio_cached_1001');
  });

  it('should provide full stream URL when resolved via JioSaavn and not in cache', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();

    vi.spyOn(musicService, 'searchTracks').mockResolvedValue([
      {
        id: 2002,
        title: 'Saavn Hit Song',
        artist: 'Saavn Singer',
        album: 'Hit Album',
        duration: 180,
        durationFormatted: '03:00',
        coverUrl: 'https://example.com/cover.jpg',
        previewUrl: 'https://example.com/preview.mp3',
        externalUrl: '',
        source: 'deezer',
      },
    ]);

    vi.spyOn(musicService, 'resolveViaJioSaavn').mockResolvedValue('https://saavncdn.com/song_160.mp4');

    let inlineHandler: Function | undefined;
    const mockBot = {
      on(event: string, fn: Function) {
        if (event === 'inline_query') inlineHandler = fn;
      },
    };

    registerInlineHandlers(mockBot, musicService, userService);

    let answeredResults: any[] = [];
    const ctx: any = {
      inlineQuery: { query: 'Saavn Hit Song' },
      from: { id: 99999 },
      me: { username: 'Musicdownloader2001_bot' },
      answerInlineQuery: async (results: any[]) => {
        answeredResults = results;
      },
    };

    await inlineHandler!(ctx);
    expect(answeredResults.length).toBe(1);
    expect(answeredResults[0].type).toBe('audio');
    expect(answeredResults[0].audio_url).toBe('https://saavncdn.com/song_160.mp4');
    expect(answeredResults[0].id).toContain('audio_saavn_2002');
  });

  it('should fallback to article card with deep-link when neither cache nor JioSaavn is available', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();

    vi.spyOn(musicService, 'searchTracks').mockResolvedValue([
      {
        id: 3003,
        title: 'Rare Indie Song',
        artist: 'Indie Band',
        album: 'Indie Album',
        duration: 240,
        durationFormatted: '04:00',
        coverUrl: 'https://example.com/cover.jpg',
        previewUrl: 'https://example.com/preview.mp3',
        externalUrl: '',
        source: 'deezer',
      },
    ]);

    vi.spyOn(musicService, 'resolveViaJioSaavn').mockResolvedValue(null);

    let inlineHandler: Function | undefined;
    const mockBot = {
      on(event: string, fn: Function) {
        if (event === 'inline_query') inlineHandler = fn;
      },
    };

    registerInlineHandlers(mockBot, musicService, userService);

    let answeredResults: any[] = [];
    const ctx: any = {
      inlineQuery: { query: 'Rare Indie Song' },
      from: { id: 99999 },
      me: { username: 'Musicdownloader2001_bot' },
      answerInlineQuery: async (results: any[]) => {
        answeredResults = results;
      },
    };

    await inlineHandler!(ctx);
    expect(answeredResults.length).toBe(1);
    expect(answeredResults[0].type).toBe('article');
    expect(answeredResults[0].id).toContain('article_dl_3003');
    expect(answeredResults[0].title).toBe('Rare Indie Song — Indie Band');
    expect(answeredResults[0].reply_markup?.inline_keyboard[0][0].url).toContain('start=dl_3003');
  });

  it('should deduct quota via chosen_inline_result when audio result is sent', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();

    const userId = 77777;
    await userService.ensureUser(userId);

    let chosenHandler: Function | undefined;
    const mockBot = {
      on(event: string, fn: Function) {
        if (event === 'chosen_inline_result') chosenHandler = fn;
      },
    };

    registerInlineHandlers(mockBot, musicService, userService);
    expect(chosenHandler).toBeDefined();

    // 1. Audio result selected -> quota should increment
    const audioCtx: any = {
      chosenInlineResult: { result_id: 'audio_cached_1001_0' },
      from: { id: userId },
    };
    await chosenHandler!(audioCtx);

    let profile = await userService.getUserProfile(userId);
    expect(profile.dailyDownloadCount).toBe(1);
    expect(profile.totalDownloads).toBe(1);

    // 2. Article result selected -> quota should NOT increment
    const articleCtx: any = {
      chosenInlineResult: { result_id: 'article_dl_3003_0' },
      from: { id: userId },
    };
    await chosenHandler!(articleCtx);

    profile = await userService.getUserProfile(userId);
    expect(profile.dailyDownloadCount).toBe(1); // Still 1
  });

  it('should render player card when /start dl_<trackId> deep-link is opened', async () => {
    const repo = new MemoryUserRepository();
    const userService = new UserService(repo);
    const musicService = new MusicService();
    const lyricsService = new LyricsService();

    vi.spyOn(musicService, 'getTrackById').mockResolvedValue({
      id: 5555,
      title: 'Deep Link Song',
      artist: 'Deep Link Artist',
      album: 'Deep Link Album',
      duration: 210,
      durationFormatted: '03:30',
      coverUrl: 'https://example.com/cover.jpg',
      previewUrl: 'https://example.com/preview.mp3',
      externalUrl: '',
      source: 'deezer',
    });

    const commands = new Map<string, Function>();
    const mockBot: any = {
      command(name: string, fn: Function) {
        commands.set(name, fn);
      },
      on() {},
    };

    registerMusicHandlers(mockBot, musicService, lyricsService, userService);
    const startHandler = commands.get('start');
    expect(startHandler).toBeDefined();

    let repliedPhoto = '';
    let repliedOptions: any = {};
    const ctx: any = {
      from: { id: 123123, first_name: 'Tester' },
      match: 'dl_5555',
      chat: { id: 123123 },
      reply: async () => ({ message_id: 111 }),
      replyWithPhoto: async (photo: string, opts: any) => {
        repliedPhoto = photo;
        repliedOptions = opts;
      },
      api: {
        deleteMessage: async () => {},
      },
    };

    await startHandler!(ctx);
    expect(repliedPhoto).toBe('https://example.com/cover.jpg');
    expect(repliedOptions.caption).toContain('Deep Link Song');
    expect(repliedOptions.caption).toContain('Deep Link Artist');
    expect(repliedOptions.reply_markup).toBeDefined();
  });
});
