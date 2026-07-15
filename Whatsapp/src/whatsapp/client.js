import wweb from 'whatsapp-web.js';
import qrcode from 'qrcode-terminal';
import { config } from '../config.js';
import { log } from '../utils/logger.js';
import { createHandler } from './handler.js';
import { createDemoHandler } from './demoHandler.js';

const { Client, LocalAuth } = wweb;

export function startClient() {
  const headless = (process.env.HEADLESS || 'true').toLowerCase() !== 'false';

  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: config.authPath }),
    puppeteer: {
      headless,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    },
    // Pin a known-good WhatsApp Web build. A stale/incompatible version is the
    // usual reason initialize() hangs before ever emitting the QR event.
    webVersionCache: {
      type: 'remote',
      remotePath:
        'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.3000.1043180520-alpha.html',
    },
  });

  let gotQr = false;

  client.on('loading_screen', (percent, message) =>
    log.step('Loading WhatsApp Web…', `${percent}% ${message || ''}`)
  );

  client.on('qr', (qr) => {
    gotQr = true;
    log.info('Scan this QR with WhatsApp (Linked Devices → Link a Device):');
    qrcode.generate(qr, { small: true });
  });

  client.on('authenticated', () => log.info('WhatsApp authenticated ✅'));
  client.on('auth_failure', (m) => log.error('Auth failure:', m));
  client.on('ready', () => log.info('Nyayra is live and listening. 🟢'));
  client.on('change_state', (s) => log.step('State:', s));
  client.on('disconnected', (reason) => log.warn('Disconnected:', reason));

  // If nothing happens in 90s, tell the user instead of leaving a silent hang.
  setTimeout(() => {
    if (!gotQr) {
      log.warn(
        'Still no QR after 90s. WhatsApp Web may be slow or the pinned version is stale.'
      );
      log.warn('Try: stop (Ctrl+C), then run again. Or set HEADLESS=false to watch the browser.');
    }
  }, 90_000);

  const demoMode = (process.env.DEMO_MODE || 'false').toLowerCase() === 'true';
  if (demoMode) log.info('DEMO_MODE on — hardcoded replies, only to the demo number.');
  client.on('message', demoMode ? createDemoHandler(client) : createHandler(client));

  client.initialize();
  return client;
}
