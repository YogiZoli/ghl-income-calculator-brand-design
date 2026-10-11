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
sub('stroke="var(--grid)"', 'stroke="var(--border)"')
sub('stroke="var(--chart-b)"', 'stroke="var(--primary)"')
sub('stroke="var(--chart-a)"', 'stroke="var(--live)"')

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

# PDF colours: Shine tokens
sub('doc.setTextColor(30,41,59)', 'doc.setTextColor(14,19,48)')      # ink
sub('doc.setTextColor(71,85,105)', 'doc.setTextColor(102,108,132)')  # muted text
sub('doc.setFillColor(4,120,87); doc.rect(0, 0, W, 118, "F");',
    'doc.setFillColor(217,30,80); doc.rect(0, 0, W, 118, "F");\n'
    '    doc.setFillColor(0,177,176); doc.rect(0, 118, W, 4, "F");')
sub('doc.setFillColor(236,253,245); doc.roundedRect(M, y, CW, 76, 10, 10, "F");',
    'var skin = [[255,233,239,249,163,184],[227,247,246,85,202,200],[251,242,221,254,200,77]][n - 1];\n'
    '      doc.setFillColor(skin[0],skin[1],skin[2]); doc.setDrawColor(skin[3],skin[4],skin[5]); doc.setLineWidth(1.2);\n'
    '      doc.roundedRect(M, y, CW, 76, 10, 10, "FD");')
sub('doc.setFillColor(4,120,87); doc.circle', 'doc.setFillColor(217,30,80); doc.circle')  # step number: fuchsia
sub('doc.setTextColor(4,120,87)', 'doc.setTextColor(163,20,58)')       # fuchsia 800
sub('doc.setDrawColor(203,213,225)', 'doc.setDrawColor(230,232,240)')  # border
sub('doc.setFillColor(4,120,87); doc.roundedRect(M, cy', 'doc.setFillColor(217,30,80); doc.roundedRect(M, cy')  # CTA
assert '4,120,87' not in js
sub('doc.text("Your numbers", M, y);', 'doc.setTextColor(179,22,63); doc.text("Your numbers", M, y);')
sub('''    rows.forEach(function(row){
      y += 20;''', '''    rows.forEach(function(row, i){
      y += 20;
      if(i % 2 === 0){ doc.setFillColor(227,247,246); doc.rect(M - 6, y - 13.5, CW + 12, 20, "F"); }''')

# the PDF waits for the fonts, but never longer than 5 seconds
sub('var pdfAssetsReady = Promise.resolve();', 'var pdfAssetsReady = fontsReady;')

assert tpl.count("@@SCRIPT@@") == 1
out.write_text(tpl.replace("@@SCRIPT@@", js), encoding="utf-8", newline="\n")
print("ok", len(js))
