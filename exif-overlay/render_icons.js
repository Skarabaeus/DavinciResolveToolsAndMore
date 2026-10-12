const fs = require('fs'), path = require('path');
const sharp = require(process.argv[2] + '/node_modules/sharp');
const src = process.argv[2] + '/node_modules/lucide-static/icons';
const out = process.argv[3];
const map = { camera: 'camera', lens: 'focus', focal: 'ruler-dimension-line', iso: 'gauge', shutter: 'timer', aperture: 'aperture' };
(async () => {
  for (const [name, icon] of Object.entries(map)) {
    let svg = fs.readFileSync(path.join(src, icon + '.svg'), 'utf8')
      .replace(/currentColor/g, '#ffffff')
      .replace(/width="24"/, 'width="256"').replace(/height="24"/, 'height="256"');
    await sharp(Buffer.from(svg)).png().toFile(path.join(out, name + '.png'));
    console.log(name, icon);
  }
})();
