import { describe, it, expect } from 'vitest';
import handler from '../api/index.js';

function createMockReqRes(method: string, headers: Record<string, string> = {}) {
  const req: any = {
    method,
    headers,
  };

  let statusCode = 200;
  const resHeaders: Record<string, string> = {};
  let body = '';

  const res: any = {
    get statusCode() {
      return statusCode;
    },
    set statusCode(val: number) {
      statusCode = val;
    },
    setHeader(key: string, val: string) {
      resHeaders[key.toLowerCase()] = val;
    },
    end(chunk?: string) {
      if (chunk) body += chunk;
    },
    get body() {
      return body;
    },
    get headers() {
      return resHeaders;
    },
  };

  return { req, res };
}

describe('Vercel Serverless Webhook Handler Tests', () => {
  it('should return 200 OK with service metadata on HTTP GET health check', async () => {
    const { req, res } = createMockReqRes('GET');
    await handler(req, res);

    expect(res.statusCode).toBe(200);
    expect(res.headers['content-type']).toBe('application/json');

    const json = JSON.parse(res.body);
    expect(json.status).toBe('ok');
    expect(json.service).toBe('MusicDownloaderBot');
    expect(json.mode).toBe('vercel-serverless');
  });

  it('should reject unauthorized POST request if secret token is invalid or missing', async () => {
    const { req, res } = createMockReqRes('POST', {
      'x-telegram-bot-api-secret-token': 'wrong_invalid_secret',
    });
    await handler(req, res);

    // If webhookSecret is configured in .env, it should return 403
    if (process.env.WEBHOOK_SECRET) {
      expect(res.statusCode).toBe(403);
      expect(res.body).toContain('Forbidden');
    }
  });

  it('should return 405 Method Not Allowed for unsupported HTTP verbs (e.g. PUT/DELETE)', async () => {
    const { req, res } = createMockReqRes('DELETE');
    await handler(req, res);

    expect(res.statusCode).toBe(405);
    expect(res.body).toContain('Method Not Allowed');
  });
});
