import { spawn } from 'node:child_process';
import ffmpegPath from 'ffmpeg-static';

// Wrap raw PCM (from the TTS model) in a WAV container.
export function pcmToWav(pcm, { sampleRate = 24000, channels = 1, bitDepth = 16 } = {}) {
  const byteRate = (sampleRate * channels * bitDepth) / 8;
  const blockAlign = (channels * bitDepth) / 8;
  const header = Buffer.alloc(44);
  header.write('RIFF', 0);
  header.writeUInt32LE(36 + pcm.length, 4);
  header.write('WAVE', 8);
  header.write('fmt ', 12);
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20); // PCM
  header.writeUInt16LE(channels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitDepth, 34);
  header.write('data', 36);
  header.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([header, pcm]);
}

// Run ffmpeg with the given args, piping `input` to stdin and returning stdout.
function runFfmpeg(args, input) {
  return new Promise((resolve, reject) => {
    const proc = spawn(ffmpegPath, args);
    const out = [];
    const err = [];
    proc.stdout.on('data', (d) => out.push(d));
    proc.stderr.on('data', (d) => err.push(d));
    proc.on('error', reject);
    proc.on('close', (code) => {
      if (code === 0) resolve(Buffer.concat(out));
      else reject(new Error(`ffmpeg exited ${code}: ${Buffer.concat(err).toString().slice(-400)}`));
    });
    if (input) {
      proc.stdin.write(input);
      proc.stdin.end();
    }
  });
}

// Convert a WAV buffer to Ogg/Opus, the format WhatsApp uses for voice notes.
export async function wavToOggOpus(wav) {
  return runFfmpeg(
    ['-hide_banner', '-loglevel', 'error', '-i', 'pipe:0', '-c:a', 'libopus', '-b:a', '32k', '-f', 'ogg', 'pipe:1'],
    wav
  );
}
