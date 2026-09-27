const fs = require('fs');
const path = require('path');

function copyDir(src, dest) {
  if (!fs.existsSync(src)) return;
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

const rootDir = path.resolve(__dirname, '..');
const outDir = path.join(rootDir, 'out');

copyDir(path.join(rootDir, 'renderer'), path.join(outDir, 'renderer'));
copyDir(path.join(rootDir, 'assets'), path.join(outDir, 'assets'));

console.log('[BUILD] Assets & renderer files copied to out/');
