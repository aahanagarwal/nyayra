const ts = () => new Date().toISOString().slice(11, 19);

export const log = {
  info: (...a) => console.log(`\x1b[32m[${ts()}]\x1b[0m`, ...a),
  warn: (...a) => console.warn(`\x1b[33m[${ts()}]\x1b[0m`, ...a),
  error: (...a) => console.error(`\x1b[31m[${ts()}]\x1b[0m`, ...a),
  step: (label, ...a) => console.log(`\x1b[36m[${ts()}] ${label}\x1b[0m`, ...a),
};
