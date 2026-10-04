# -*- coding: utf-8 -*-
"""ساخت نسخه توسعه‌یافته گزارش کارآموزی دماوند انرژی عسلویه (افزودن فصل‌های تصفیه پساب)"""
import re, os, sys, zipfile, shutil, math
from xml.sax.saxutils import escape
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
NS_W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS_WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(BASE, '145624472712978176_1077018538141492.docx')
OUT = os.path.join(BASE, 'گزارش-کارآموزی-دماوند-انرژی-عسلویه-ویرایش-توسعه‌یافته.docx')
WORK = '/tmp/report_builder_unz'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1, c2, c3, c4, c5, c6, c7

BLOCKS = c1.BLOCKS + c2.BLOCKS + c3.BLOCKS + c4.BLOCKS + c5.BLOCKS + c6.BLOCKS

# --- تفکیک پیوست و منابع تکمیلی از فصل ۱۶ ---
idx_app = next(i for i, b in enumerate(c7.BLOCKS) if b[0] == 'h1' and b[1].startswith('پیوست'))
CH16 = c7.BLOCKS[:idx_app]
REST = c7.BLOCKS[idx_app:]
idx_ref = next(i for i, b in enumerate(REST) if b[0] == 'h3' and b[1].startswith('منابع تکمیلی'))
APPENDIX = REST[:idx_ref]
REFS = REST[idx_ref:]

# ---------------------------------------------------------------- helpers
def split_runs(text):
    """تقسیم متن به قطعات فارسی (RTL) و لاتین (LTR) مطابق ساختار سند اصلی.
    فاصله‌ها و نشانه‌های لاتین بدون حرف/رقم به قطعه فارسی مجاور می‌چسبند تا
    تعداد Runها کم و ساختار سند تمیز بماند."""
    raw = [s for s in re.split(r'([\x00-\x7F]+)', text) if s]
    out = []
    for seg in raw:
        if re.search(r'[A-Za-z0-9]', seg):
            out.append((seg, False))
        else:
            if out and out[-1][1]:
                out[-1] = (out[-1][0] + seg, True)
            else:
                out.append((seg, True))
    # چسباندن قطعه‌های فارسی مجاور (در صورت وجود)
    merged = []
    for seg, rtl in out:
        if merged and rtl and merged[-1][1]:
            merged[-1] = (merged[-1][0] + seg, True)
        else:
            merged.append((seg, rtl))
    return merged

def runs_xml(text, bold=False, italic=False):
    xml = ''
    for seg, rtl in split_runs(text):
        rpr = ''
        if bold:
            rpr += '<w:b/>'
        if italic:
            rpr += '<w:i/>'
        if rtl:
            rpr += '<w:rtl/>'
        rpr = '<w:rPr>%s</w:rPr>' % rpr if rpr else ''
        xml += '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, escape(seg))
    return xml

def para_xml(style, text, bold=False, numid=None):
    numpr = '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="%d"/></w:numPr>' % numid if numid else ''
    return ('<w:p><w:pPr><w:pStyle w:val="%s"/>%s<w:bidi/>'
            '<w:spacing w:line="360" w:lineRule="auto"/></w:pPr>%s</w:p>'
            % (style, numpr, runs_xml(text, bold)))

TOTAL_W = 9628

def table_xml(rows):
    ncols = max(len(r) for r in rows)
    gw = TOTAL_W // ncols
    out = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblInd w:w="-5" w:type="dxa"/>'
           '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="55" w:type="dxa"/>'
           '<w:left w:w="55" w:type="dxa"/><w:bottom w:w="55" w:type="dxa"/>'
           '<w:right w:w="55" w:type="dxa"/></w:tblCellMar><w:tblLook w:val="0000" w:firstRow="0" '
           'w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0"/></w:tblPr><w:tblGrid>']
    out.append('<w:gridCol w:w="%d"/>' % gw * ncols)
    out.append('</w:tblGrid>')
    for ri, row in enumerate(rows):
        tr = ['<w:tr>']
        if ri == 0:
            tr.append('<w:trPr><w:tblHeader/></w:trPr>')
        for ci, cell in enumerate(row):
            b = []
            if ri == 0:
                b.append('<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>')
            if ci == 0:
                b.append('<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>')
            b.append('<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>')
            if ci == ncols - 1:
                b.append('<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>')
            style = 'TableHeading' if ri == 0 else 'TableContents'
            jc = '<w:jc w:val="left"/>' if ri == 0 else ''
            cp = ('<w:p><w:pPr><w:pStyle w:val="%s"/><w:bidi/><w:spacing w:line="360" w:lineRule="auto"/>%s</w:pPr>%s</w:p>'
                  % (style, jc, runs_xml(cell)))
            tr.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/><w:tcBorders>%s</w:tcBorders></w:tcPr>%s</w:tc>'
                      % (gw, ''.join(b), cp))
        tr.append('</w:tr>')
        out.append(''.join(tr))
    out.append('</w:tbl>')
    return ''.join(out)

NUMID_START = 100

def blocks_to_xml(blocks):
    """تبدیل بلوک‌ها به XML؛ هر فهرست گلوله‌ای numId مستقل می‌گیرد"""
    xml = []
    numid = NUMID_START
    used_numids = []
    for kind, val in blocks:
        if kind == 'h1':
            xml.append(para_xml('Heading1', val))
        elif kind == 'h2':
            xml.append(para_xml('Heading2', val))
        elif kind == 'h3':
            xml.append(para_xml('Heading3', val))
        elif kind == 'h4':
            xml.append(para_xml('Heading4', val))
        elif kind == 'p':
            xml.append(para_xml('BodyText', val))
        elif kind == 'cap':
            xml.append(para_xml('BodyText', val, bold=True))
        elif kind == 'bullets':
            for item in val:
                xml.append(para_xml('BodyText', item, numid=numid))
            used_numids.append(numid)
            numid += 1
        elif kind == 'tbl':
            xml.append(table_xml(val))
        else:
            raise ValueError(kind)
    return ''.join(xml), used_numids

# ---------------------------------------------------------------- parse source
if os.path.isdir(WORK):
    shutil.rmtree(WORK)
os.makedirs(WORK)
with zipfile.ZipFile(SRC) as z:
    names = z.namelist()
    z.extractall(WORK)

doc_path = os.path.join(WORK, 'word/document.xml')
parser = etree.XMLParser(remove_blank_text=False)
tree = etree.parse(doc_path, parser)
root = tree.getroot()
body = root.find(W + 'body')

def ptext(el):
    return ''.join(t.text or '' for t in el.iter(W + 't'))

def find_p(match):
    for i, el in enumerate(list(body)):
        if etree.QName(el).localname == 'p' and match(ptext(el).strip()):
            return i, el
    raise KeyError(match)

def xml_elems(xmlstr):
    wrapper = ('<w:root xmlns:w="%s" xmlns:wp="%s">%s</w:root>' % (NS_W, NS_WP, xmlstr))
    r = etree.fromstring(wrapper.encode('utf-8'))
    return list(r)

ch_xml, numids_ch = blocks_to_xml(BLOCKS + CH16)
app_xml, numids_app = blocks_to_xml(APPENDIX)
ref_xml, numids_ref = blocks_to_xml(REFS)
all_numids = numids_ch + numids_app + numids_ref

# ۱) درج فصل‌های جدید پیش از «فصل دهم» (جمع‌بندی)
i_old10, el_old10 = find_p(lambda t: t == 'فصل دهم')
for e in reversed(xml_elems(ch_xml)):
    body.insert(i_old10, e)

# ۲) تغییر شماره فصل جمع‌بندی و بخش‌های آن به ۱۷
el_old10.find(W + 'r').find(W + 't').text = 'فصل هفدهم'
for el in body.iter(W + 'p'):
    st = el.find(W + 'pPr/' + W + 'pStyle')
    if st is None or st.get(W + 'val') != 'Heading3':
        continue
    p = ptext(el)
    m = re.match(r'^(۱۰)-([۱-۴]) ', p)
    if m:
        for r in el.findall(W + 'r'):
            t = r.find(W + 't')
            if t is not None and t.text and t.text.startswith('۱۰-'):
                t.text = re.sub(r'^۱۰-', '۱۷-', t.text)
                break

# ۳) درج پیوست و منابع تکمیلی پیش از «صفحه تأیید و امضا»
i_sign, el_sign = find_p(lambda t: t == 'صفحه تأیید و امضا')
for e in reversed(xml_elems(app_xml)):
    body.insert(i_sign, e)
for e in reversed(xml_elems(ref_xml)):
    body.insert(i_sign, e)

# ۴) افزودن numIdهای جدید برای فهرست‌های گلوله‌ای
num_path = os.path.join(WORK, 'word/numbering.xml')
ntree = etree.parse(num_path, parser)
nroot = ntree.getroot()
for nid in all_numids:
    el = etree.SubElement(nroot, W + 'num')
    el.set(W + 'numId', str(nid))
    a = etree.SubElement(el, W + 'abstractNumId')
    a.set(W + 'val', '5')  # فهرست گلوله‌ای (bullet) موجود
ntree.write(num_path, xml_declaration=True, encoding='UTF-8', standalone=True)

# ۵) ذخیره سند
tree.write(doc_path, xml_declaration=True, encoding='UTF-8', standalone=True)

# ۶) بسته‌بندی مجدد docx
if os.path.exists(OUT):
    os.remove(OUT)
zin = zipfile.ZipFile(SRC)
zout = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED)
for name in names:
    zout.writestr(name, open(os.path.join(WORK, name), 'rb').read())
zout.close()
zin.close()
print('written:', OUT, os.path.getsize(OUT))
