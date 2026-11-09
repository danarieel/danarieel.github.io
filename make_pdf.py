import os
import sys
import re
from xml.sax.saxutils import escape

from bs4 import BeautifulSoup
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'index.html')

FONT_SETS = [
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
    ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
]

REDACT = [
    (re.compile(r'ChangeNOW', re.I), 'the product'),
    (re.compile(r'(?:MaxPatrol(?: SIEM)?|SearchInform|Wazuh)', re.I), 'SIEM'),
    (re.compile(r'PTAF', re.I), 'WAF'),
    (re.compile(r'\b(?:KAV|KSMG)\b', re.I), 'endpoint/email security'),
    (re.compile(r'\bKomrad\b', re.I), 'security tools'),
    (re.compile(r'since liquidity is sourced from exchanges', re.I), ''),
    (re.compile(r'ликвидность берётся с бирж', re.I), ''),
    (re.compile(r'\(memo\)', re.I), ''),
]


def scrub(s: str) -> str:
    for rx, rep in REDACT:
        s = rx.sub(rep, s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    s = re.sub(r'\b([A-Za-zА-Яа-я/ ]+?)(?:,\s*\1\b)+', r'\1', s, flags=re.I)
    s = re.sub(r'\b([A-Za-zА-Яа-я/ ]+?):\s*\1\b', r'\1:', s, flags=re.I)
    return s


for reg, bold in FONT_SETS:
    if os.path.exists(reg) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont('R', reg, asciiReadable=True))
        pdfmetrics.registerFont(TTFont('B', bold, asciiReadable=True))
        break
else:
    sys.exit('Не найден шрифт с кириллицей: поставь Liberation Sans или DejaVu Sans.')

WHITE = HexColor('#E8E6E1')
DIM = HexColor('#9AA0A6')
ACCENT = HexColor('#E0A030')
INK = HexColor('#14161A')
LINE = HexColor('#2A2E35')
BG = HexColor('#0D0F12')

soup = BeautifulSoup(open(SRC, encoding='utf-8').read(), 'html.parser')


def T(el, l):
    t = el.get('data-ru') if (l == 'ru' and el.has_attr('data-ru')) else el.get_text(' ', strip=True)
    return escape(scrub(t.strip()))


def sec(*names):
    for x in soup.find_all('section'):
        h2 = x.find('h2')
        if h2 and h2.get_text(strip=True) in names:
            return x
    return None


def build(l, out, scale=1.0):
    def st(n, **k):
        return ParagraphStyle(n, fontName=k.pop('f', 'R'), fontSize=k.pop('s', 9.3) * scale,
                              leading=k.pop('ld', 12.4) * scale, textColor=k.pop('c', WHITE), **k)

    body, small = st('b'), st('s', c=DIM, s=9, ld=12)
    h2 = st('h', f='B', s=8, c=ACCENT, spaceBefore=14, spaceAfter=4, ld=10)
    bul = st('bl', leftIndent=10, bulletIndent=0, spaceBefore=2.5, c=WHITE, ld=12.2)

    def head(t):
        return [Paragraph(t.upper(), h2), HRFlowable(width='100%', thickness=.5, color=LINE, spaceAfter=6)]

    def entries(section):
        flow = []
        arts = section.find_all('article')
        for i, job in enumerate(arts):
            if i > 0:
                flow.append(Spacer(1, 10))
            row = Table([[Paragraph(T(job.find('h3'), l), st('j', f='B')),
                          Paragraph(T(job.find('span', class_='date'), l), st('d', c=DIM, s=8.5, alignment=2))]],
                        colWidths=[None, 40 * mm])
            row.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                     ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
            flow += [row]
            co = job.find('p', class_='co')
            if co is not None:
                flow += [Paragraph(T(co, l), small)]
            flow += [Paragraph(T(li, l), bul, bulletText='–') for li in job.find_all('li')]
        return flow

    name = ' '.join(T(x, l) for x in soup.find('h1').find_all('span'))
    site = 'Site' if l == 'en' else 'Сайт'
    H = [Paragraph(name, st('n', f='B', s=22, ld=25, c=WHITE)),
         Paragraph(T(soup.find('p', class_='role'), l), st('r', c=DIM, s=10, ld=13, spaceBefore=2)),
         Paragraph('qbwrkr@gmail.com  |  Telegram: @qbwrkr  |  GitHub: github.com/danarieel  |  %s: danarieel.github.io' % site,
                   st('c', c=DIM, s=8.0, spaceBefore=3)),
         Spacer(1, 5), HRFlowable(width='100%', thickness=1.6, color=ACCENT, spaceAfter=0), Spacer(1, 4)]

    P = []
    profile = sec('Profile')
    P += head(T(profile.find('h2'), l))
    raw = profile.find('p', class_='profile')
    text = (raw.get('data-ru') if l == 'ru' else raw.get_text()).strip()
    for para in text.split('\n\n'):
        P.append(Paragraph(escape(' '.join(para.split())), st('p', ld=13.4, spaceAfter=3)))

    M = []
    proj = sec('Projects')
    if proj is not None:
        M += head(T(proj.find('h2'), l)) + entries(proj)
    exp = sec('Experience')
    if exp is not None:
        M += head(T(exp.find('h2'), l)) + entries(exp)

    Sd = []
    sk = sec('Skills')
    if sk is not None:
        Sd += head(T(sk.find('h2'), l))
        for kv in sk.find_all('div', class_='kv'):
            a, b = kv.find_all('span', recursive=False)
            Sd += [Paragraph(T(a, l), st('k', c=DIM, s=8, ld=10, spaceBefore=3)), Paragraph(T(b, l), st('v', s=9.1, ld=11.8))]
    ed = sec('Education')
    if ed is not None:
        Sd += head(T(ed.find('h2'), l))
        for kv in ed.find_all('div', class_='kv'):
            y, n, p = kv.find_all('span', recursive=False)
            Sd += [Paragraph(T(y, l), st('k', c=DIM, s=8, ld=10)), Paragraph(T(n, l), st('v', s=9.1, ld=11.8)), Paragraph(T(p, l), small)]
    co = sec('Courses')
    if co is not None:
        Sd += head(T(co.find('h2'), l))
        for kv in co.find_all('div', class_='kv'):
            y, n, p = kv.find_all('span', recursive=False)
            Sd += [Paragraph('%s · %s' % (T(y, l), T(p, l)), st('k', c=DIM, s=8, ld=10, spaceBefore=3)),
                   Paragraph(T(n, l), st('v', s=9.1, ld=11.8))]

    W = A4[0] - 28 * mm - 12

    profile_t = Table([[P]], colWidths=[W], hAlign='LEFT')
    profile_t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                   ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))

    body_t = Table([[M, Sd]], colWidths=[W - 54 * mm, 54 * mm], hAlign='LEFT')
    body_t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                ('RIGHTPADDING', (0, 0), (0, 0), 14), ('RIGHTPADDING', (1, 0), (1, 0), 0),
                                ('TOPPADDING', (0, 0), (-1, -1), 0)]))

    def _dark_bg(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0, 0, A4[0], A4[1], stroke=0, fill=1)
        canvas.restoreState()

    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=10 * mm,
                            title='Vitaly Vasilchenko — CV' if l == 'en' else 'Васильченко Виталий — резюме',
                            author='Vitaly Vasilchenko')
    doc.build(H + [profile_t, Spacer(1, 14), body_t], onFirstPage=_dark_bg, onLaterPages=_dark_bg)

    try:
        from pypdf import PdfReader
        return len(PdfReader(out).pages)
    except ImportError:
        return 1


def build_fit(l, out):
    scale = 1.0
    while True:
        pages = build(l, out, scale)
        if pages == 1 or scale <= 0.84:
            break
        scale = round(scale - 0.02, 2)
    note = '' if pages == 1 else '  <-- НЕ ВЛЕЗЛО, сократи текст в index.html'
    print('%s: %d стр., масштаб шрифта %.2f%s' % (os.path.basename(out), pages, scale, note))


build_fit('en', os.path.join(HERE, 'vitalyv_cv_en.pdf'))
build_fit('ru', os.path.join(HERE, 'vitalyv_cv_ru.pdf'))
