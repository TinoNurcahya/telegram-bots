import { Bot } from 'grammy';
import { MusicService } from '../services/music.service.js';
import { LyricsService } from '../services/lyrics.service.js';
import { UserService } from '../services/user.service.js';
import { createUserRepository, IUserRepository } from '../repositories/user.repository.js';
import { registerMusicHandlers } from './handlers/music.handler.js';
import { registerInlineHandlers } from './handlers/inline.handler.js';
import { registerMonetizationHandlers } from './handlers/monetization.handler.js';
import { registerAdminHandlers } from './handlers/admin.handler.js';

export function createBot(
  token: string,
  repository?: IUserRepository,
  databaseUrl?: string,
  adminId: number = 0,
  streamResolverUrl: string = '',
  rapidApiKey: string = ''
) {
  const bot = new Bot(token);
  const repo = repository || createUserRepository(databaseUrl);
  const userService = new UserService(repo, adminId);
  const musicService = new MusicService(streamResolverUrl, rapidApiKey);
  const lyricsService = new LyricsService();

  // Global Error Catcher
  bot.catch((err) => {
    console.error('Unhandled bot error in grammY:', err.error);
  });

  // Register Handlers
  registerMusicHandlers(bot, musicService, lyricsService, userService);
  registerInlineHandlers(bot, musicService, userService);
  registerMonetizationHandlers(bot, userService);
  registerAdminHandlers(bot, userService, adminId);

  return { bot, musicService, lyricsService, userService, repo };
}
