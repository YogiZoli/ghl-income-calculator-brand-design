"""Build the brand-design duplicate: the original script verbatim, with only the visual layer patched."""
import re
import sys
from pathlib import Path

orig = Path(sys.argv[1]).read_text(encoding="utf-8")
tpl = Path(sys.argv[2]).read_text(encoding="utf-8")
out = Path(sys.argv[3])

scripts = re.findall(r"<script>\n(.*?)\n</script>", orig, flags=re.S)
assert len(scripts) == 1
js = scripts[0]


def sub(old, new, count=1):
    global js
    assert js.count(old) == count, (old, js.count(old))
    js = js.replace(old, new)


# chart colours: role tokens
sub('stroke="var(--grid)"', 'stroke="var(--line)"')
sub('stroke="var(--chart-b)"', 'stroke="var(--navy)"')
sub('stroke="var(--chart-a)"', 'stroke="var(--teal)"')

# PDF: Open Sans when the font files load, Helvetica otherwise
sub('''  function buildPdf(name, r){
    var doc = new window.jspdf.jsPDF({ unit:"pt", format:"a4" });''',
    '''  /* Open Sans for the PDF, loaded from the files next to this page. If they cannot load, the PDF uses Helvetica. */
  var PDF_FONTS = null;
  function fontData(url){
    return fetch(url).then(function(res){
      if(!res.ok) throw new Error("font");
      return res.arrayBuffer();
    }).then(function(buf){
      var bytes = new Uint8Array(buf), bin = "", i;
      for(i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      return btoa(bin);
    });
  }
  var fontsReady = Promise.race([
    Promise.all([fontData("fonts/OpenSans-400.ttf"), fontData("fonts/OpenSans-700.ttf")]),
    new Promise(function(_, reject){ setTimeout(function(){ reject(new Error("timeout")); }, 5000); })
  ]).then(function(f){ PDF_FONTS = f; log("PDF fonts loaded"); },
          function(e){ PDF_FONTS = null; log("PDF fonts did not load, the PDF will use Helvetica", errText(e)); });

  function buildPdf(name, r){
    var doc = new window.jspdf.jsPDF({ unit:"pt", format:"a4" });
    var FONT = "helvetica";
    if(PDF_FONTS && !PLAIN_PDF){
      doc.addFileToVFS("OpenSans-400.ttf", PDF_FONTS[0]); doc.addFont("OpenSans-400.ttf", "OpenSans", "normal");
      doc.addFileToVFS("OpenSans-700.ttf", PDF_FONTS[1]); doc.addFont("OpenSans-700.ttf", "OpenSans", "bold");
      FONT = "OpenSans";
    }''')
sub('doc.setFont("helvetica","italic")', 'doc.setFont(FONT,"normal")')
js = js.replace('doc.setFont("helvetica",', 'doc.setFont(FONT,')
assert '"helvetica",' not in js
sub('.test(name)){', '.test(name) && (FONT === "helvetica" || /[^\\x20-\\u024F]/.test(name))){')

# PDF colours: the page palette. Text #0F172A, muted #475569 (already the original muted), Teal, Navy, Emerald, Amber.
sub('doc.setTextColor(30,41,59)', 'doc.setTextColor(15,23,42)')
sub('doc.setFillColor(4,120,87); doc.rect(0, 0, W, 118, "F");',
    'doc.setFillColor(14,116,144); doc.rect(0, 0, W, 118, "F");\n'
    '    doc.setFillColor(30,58,138); doc.rect(0, 118, W, 4, "F");')
sub('doc.setFillColor(236,253,245); doc.roundedRect(M, y, CW, 76, 10, 10, "F");',
    'var sk = skinFor(n);\n'
    '      doc.setFillColor(sk.t[0],sk.t[1],sk.t[2]); doc.rect(M, y, CW, 76, "F");\n'
    '      doc.setFillColor(sk.s[0],sk.s[1],sk.s[2]); doc.rect(M, y, 4, 76, "F");')
sub('doc.setFillColor(4,120,87); doc.circle', 'doc.setFillColor(sk.s[0],sk.s[1],sk.s[2]); doc.circle')
sub('doc.setTextColor(4,120,87)', 'doc.setTextColor(sk.d[0],sk.d[1],sk.d[2])')
sub('ink(); doc.setFontSize(22);', 'doc.setTextColor(sk.d[0],sk.d[1],sk.d[2]); doc.setFontSize(22);')
sub('doc.setDrawColor(203,213,225)', 'doc.setDrawColor(226,232,240)')
sub('doc.setFillColor(4,120,87); doc.roundedRect(M, cy', 'doc.setFillColor(14,116,144); doc.roundedRect(M, cy')
assert '4,120,87' not in js
sub('doc.text("Your numbers", M, y);', 'doc.text("Your numbers", M, y);\n    doc.setFillColor(14,116,144); doc.rect(M, y + 5, 40, 3, "F");')
sub('''    rows.forEach(function(row){
      y += 20;''', '''    rows.forEach(function(row, i){
      y += 20;
      if(i % 2 === 0){ doc.setFillColor(230,244,247); doc.rect(M - 6, y - 13.5, CW + 12, 20, "F"); }''')
# block colours, same rotation as the page: Teal, Navy, Emerald. Block 1 follows the result: Emerald on track, Amber when not.
sub('    var FONT = "helvetica";', '''    var FONT = "helvetica";
    var SKINS = {
      teal:  { t:[230,244,247], s:[14,116,144], d:[14,116,144] },
      navy:  { t:[232,237,251], s:[30,58,138],  d:[30,58,138] },
      em:    { t:[231,246,240], s:[4,120,87],   d:[4,120,87] },
      amber: { t:[254,243,226], s:[180,83,9],   d:[146,64,14] }
    };
    function skinFor(n){ return [r.onTrack ? SKINS.em : SKINS.amber, SKINS.teal, SKINS.navy][n - 1]; }''')

# the PDF waits for the fonts, but never longer than 5 seconds
sub('var pdfAssetsReady = Promise.resolve();', 'var pdfAssetsReady = fontsReady;')

assert tpl.count("@@SCRIPT@@") == 1
out.write_text(tpl.replace("@@SCRIPT@@", js), encoding="utf-8", newline="\n")
print("ok", len(js))
