# -*- coding: utf-8 -*-
"""تخمین تعداد صفحات با مدل چیدمان (Line-layout model) — کالیبره‌شده روی سند اصلی"""
import sys, math, zipfile, io
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'

TEXT_W = 481.9   # pt (17 cm)
TEXT_H = 728.5   # pt (25.7 cm)
CM2PT = 28.3465

STYLE_SIZE = {'Heading1': 18.0, 'Heading2': 16.0, 'Heading3': 14.0, 'Heading4': 13.0,
              'BodyText': 12.0, 'TableContents': 12.0, 'TableHeading': 12.0, 'Normal': 12.0}
STYLE_BEFORE = {'Heading1': 12.0, 'Heading2': 10.0, 'Heading3': 7.0, 'Heading4': 6.0, 'BodyText': 0.0}
STYLE_AFTER = {'Heading1': 6.0, 'Heading2': 6.0, 'Heading3': 6.0, 'Heading4': 6.0, 'BodyText': 7.0}

def doc_text_width(chars, size, p_persian=0.44):
    """تخمین عرض متن (pt)"""
    em = size
    total = 0.0
    for ch in chars:
        o = ord(ch)
        if ch == ' ':
            total += 0.25 * em
        elif 0x0600 <= o <= 0x06FF or 0x200c <= o <= 0x200f or 0xFB50 <= o <= 0xFEFF:
            total += p_persian * em
        elif o < 128:
            total += 0.5 * em
        else:
            total += 0.5 * em
    return total

def para_height(el, p_persian=0.44):
    """ارتفاع تخمینی یک پاراگراف (pt) و نوع آن"""
    ppr = el.find(W + 'pPr')
    style = 'Normal'
    numpr = False
    if ppr is not None:
        st = ppr.find(W + 'pStyle')
        if st is not None:
            style = st.get(W + 'val')
        numpr = ppr.find(W + 'numPr') is not None
    size = STYLE_SIZE.get(style, 12.0)
    lh = 1.5 * 1.15 * size
    text = ''.join(t.text or '' for t in el.iter(W + 't'))
    indent = 0.0
    if numpr:
        indent = 35.0   # 709 twips
    avail = TEXT_W - indent
    wid = doc_text_width(text, size, p_persian)
    lines = max(1, math.ceil(wid / avail - 1e-6)) if text.strip() else 1
    h = lines * lh + STYLE_BEFORE.get(style, 0) + STYLE_AFTER.get(style, 0)
    return h, style, numpr

def table_height(el):
    """ارتفاع تخمینی جدول (pt)"""
    total = 0.0
    ncols = len(el.findall(W + 'tblGrid/' + W + 'gridCol'))
    if ncols == 0:
        ncols = 1
    grid = [int(g.get(W + 'w')) for g in el.findall(W + 'tblGrid/' + W + 'gridCol')]
    for tr in el.findall(W + 'tr'):
        rowmax = 0.0
        for ci, tc in enumerate(tr.findall(W + 'tc')):
            cw = (grid[ci] if ci < len(grid) else grid[0]) - 10  # حذف حاشیه
            cw_pt = cw / 20.0  # twips -> pt
            txt = ''.join(t.text or '' for t in tc.iter(W + 't'))
            size = 12.0
            wid = doc_text_width(txt, size)
            lines = max(1, math.ceil(wid / cw_pt - 1e-6)) if txt.strip() else 1
            h = lines * (1.5 * 1.15 * size) + 5.5  # حاشیه بالا و پایین سلول
            rowmax = max(rowmax, h)
        total += rowmax
    return total

def estimate(path):
    with zipfile.ZipFile(path) as z:
        x = z.read('word/document.xml')
    root = etree.fromstring(x)
    body = root.find(W + 'body')
    heights = []
    for el in body:
        tag = etree.QName(el).localname
        if tag == 'p':
            # شکست صفحه دستی
            if any(b.get(W + 'type') == 'page' for b in el.iter(W + 'br')):
                heights.append(('PAGEBREAK', 0))
            h, style, numpr = para_height(el)
            imgs = [int(e.get('cy')) / 360000 * CM2PT for e in el.iter(WP + 'extent')]
            heights.append(('p', h + sum(imgs)))
        elif tag == 'tbl':
            heights.append(('t', table_height(el)))
    # چیدمان
    page = 1
    y = 0.0
    pages_fill = {}
    for kind, h in heights:
        if kind == 'PAGEBREAK':
            page += 1
            y = 0
            continue
        if y + h > TEXT_H and h < TEXT_H:
            page += 1
            y = 0
        y += h
    return page, sum(h for k, h in heights if k != 'PAGEBREAK')

if __name__ == '__main__':
    for path, label in [(sys.argv[1], 'original'), (sys.argv[2], 'new')]:
        p, tot = estimate(path)
        print(f"{label}: estimated pages = {p}   (total content height = {tot:.0f} pt = {tot/TEXT_H:.1f} page-heights)")
