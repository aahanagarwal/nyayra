import { assertConfig } from './config.js';
import { log } from './utils/logger.js';
import { startClient } from './whatsapp/client.js';

function main() {
  try {
    assertConfig();
  } catch (e) {
    log.error(e.message);
    process.exit(1);
  }

  // A single bad message or library glitch should never take the bot down.
  process.on('unhandledRejection', (reason) =>
    log.error('unhandledRejection:', reason?.message || reason)
  );
  process.on('uncaughtException', (err) => log.error('uncaughtException:', err?.message || err));

  log.info('Starting Nyayra WhatsApp bot…');
  const client = startClient();

  const shutdown = async () => {
    log.info('Shutting down…');
    try {
      await client.destroy();
    } catch {}
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

main();
