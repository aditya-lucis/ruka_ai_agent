const { execSync } = require('child_process');

// Set compression level to 1 and Node memory to 8GB for memory-safe packaging on large 600MB+ payloads
process.env.ELECTRON_BUILDER_COMPRESSION_LEVEL = '1';
process.env.NODE_OPTIONS = (process.env.NODE_OPTIONS || '') + ' --max-old-space-size=8192';

const fs = require('fs');
const path = require('path');

// Clean win-unpacked before packaging to prevent Windows file-lock errors on existing binaries
const winUnpacked = path.join(process.cwd(), 'release', 'win-unpacked');
if (fs.existsSync(winUnpacked)) {
  console.log('[Ruka Packager] Removing existing release/win-unpacked...');
  try {
    fs.rmSync(winUnpacked, { recursive: true, force: true, maxRetries: 5, retryDelay: 500 });
  } catch (err) {
    console.warn('[Ruka Packager] Warning while removing win-unpacked:', err.message);
  }
}

console.log('[Ruka Packager] Starting build and packaging with compression level 1...');
try {
  execSync('npm run build', { stdio: 'inherit', cwd: process.cwd() });
  console.log('[Ruka Packager] Running electron-builder...');
  execSync('npx electron-builder', { stdio: 'inherit', cwd: process.cwd() });
  console.log('[Ruka Packager] Packaging completed successfully!');
} catch (error) {
  console.error('[Ruka Packager] Build failed:', error);
  process.exit(1);
}
