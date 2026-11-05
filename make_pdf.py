"""Собирает vitalyv_cv_en.pdf и vitalyv_cv_ru.pdf из index.html (весь текст берётся оттуда).

Запуск:  python3 make_pdf.py        (index.html лежит рядом со скриптом)
Нужно:   pip install beautifulsoup4 reportlab pypdf ; шрифт с кириллицей (Liberation Sans / DejaVu Sans / Arial).
"""
import os
import sys
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
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
    ('C:/Windows/Fonts/arial.ttf', 'C:/Windows/Fonts/arialbd.ttf'),
]
for reg, bold in FONT_SETS:
    if os.path.exists(reg) and os.path.exists(bold):
        pdfmetrics.registerFont(TTFont('R', reg))
        pdfmetrics.registerFont(TTFont('B', bold))
        break
else:
    sys.exit('Не найден шрифт с кириллицей: поставь Liberation Sans или DejaVu Sans.')

INK, GRAY, AC, LINE = HexColor('#14161A'), HexColor('#5A5E66'), HexColor('#E0A030'), HexColor('#C9CBCF')
soup = BeautifulSoup(open(SRC, encoding='utf-8').read(), 'html.parser')


def T(el, l):
    """Текст элемента на нужном языке (RU берётся из data-ru, если он есть)."""
    t = el.get('data-ru') if (l == 'ru' and el.has_attr('data-ru')) else el.get_text(' ', strip=True)
    return escape(t.strip())


def sec(*names):
    for x in soup.find_all('section'):
        h2 = x.find('h2')
        if h2 and h2.get_text(strip=True) in names:
            return x
    return None


def build(l, out, scale=1.0):
    def st(n, **k):
        return ParagraphStyle(n, fontName=k.pop('f', 'R'), fontSize=k.pop('s', 9.3) * scale,
                              leading=k.pop('ld', 12.4) * scale, textColor=k.pop('c', INK), **k)

    body, small = st('b'), st('s', c=GRAY, s=9, ld=12)
    h2 = st('h', f='B', s=8, c=GRAY, spaceBefore=11, spaceAfter=2, ld=10)
    bul = st('bl', leftIndent=10, bulletIndent=0, spaceBefore=1.6)

    def head(t):
        return [Paragraph(t.upper(), h2), HRFlowable(width='100%', thickness=.5, color=LINE, spaceAfter=4)]

    def entries(section):
        """Блоки Projects / Experience: заголовок + дата, подпись, маркеры."""
        flow = []
        for job in section.find_all('article'):
            row = Table([[Paragraph(T(job.find('h3'), l), st('j', f='B')),
                          Paragraph(T(job.find('span', class_='date'), l), st('d', c=GRAY, s=8.5, alignment=2))]],
                        colWidths=[None, 40 * mm])
            row.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                     ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
            flow += [row, Paragraph(T(job.find('p', class_='co'), l), small)]
            flow += [Paragraph(T(li, l), bul, bulletText='–') for li in job.find_all('li')]
        return flow

    # ---- основная колонка
    M = []
    profile = sec('Profile')
    M += head(T(profile.find('h2'), l))
    raw = profile.find('p', class_='profile')
    text = (raw.get('data-ru') if l == 'ru' else raw.get_text()).strip()
    for para in text.split('\n\n'):
        M.append(Paragraph(escape(' '.join(para.split())), st('p', ld=13.4, spaceAfter=3)))
    for names in (('Projects',), ('Experience',)):
        s = sec(*names)
        if s is not None:
            M += head(T(s.find('h2'), l)) + entries(s)

    # ---- боковая колонка
    Sd = head(T(sec('Skills').find('h2'), l))
    for kv in sec('Skills').find_all('div', class_='kv'):
        a, b = kv.find_all('span', recursive=False)
        Sd += [Paragraph(T(a, l), st('k', c=GRAY, s=8, ld=10, spaceBefore=3)), Paragraph(T(b, l), st('v', s=9.1, ld=11.8))]
    Sd += head(T(sec('Education').find('h2'), l))
    for kv in sec('Education').find_all('div', class_='kv'):
        y, n, p = kv.find_all('span', recursive=False)
        Sd += [Paragraph(T(y, l), st('k', c=GRAY, s=8, ld=10)), Paragraph(T(n, l), st('v', s=9.1, ld=11.8)), Paragraph(T(p, l), small)]
    Sd += head(T(sec('Courses').find('h2'), l))
    for kv in sec('Courses').find_all('div', class_='kv'):
        y, n, p = kv.find_all('span', recursive=False)
        Sd += [Paragraph('%s · %s' % (T(y, l), T(p, l)), st('k', c=GRAY, s=8, ld=10, spaceBefore=3)),
               Paragraph(T(n, l), st('v', s=9.1, ld=11.8))]

    # ---- шапка
    name = ' '.join(T(x, l) for x in soup.find('h1').find_all('span'))
    site = 'Site' if l == 'en' else 'Сайт'
    H = [Paragraph(name, st('n', f='B', s=22, ld=25)),
         Paragraph(T(soup.find('p', class_='role'), l), st('r', c=GRAY, s=10, ld=13, spaceBefore=2)),
         Paragraph('qbwrkr@gmail.com  |  Telegram: @qbwrkr  |  GitHub: github.com/danarieel  |  %s: danarieel.github.io' % site,
                   st('c', s=8.8, spaceBefore=3)),
         Spacer(1, 5), HRFlowable(width='100%', thickness=1.6, color=AC, spaceAfter=0), Spacer(1, 4)]

    W = A4[0] - 28 * mm - 12
    body_t = Table([[M, Sd]], colWidths=[W - 54 * mm, 54 * mm], hAlign='LEFT')
    body_t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                ('RIGHTPADDING', (0, 0), (0, 0), 12), ('RIGHTPADDING', (1, 0), (1, 0), 0),
                                ('TOPPADDING', (0, 0), (-1, -1), 0)]))
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=10 * mm,
                            title='Vitaly Vasilchenko — CV' if l == 'en' else 'Васильченко Виталий — резюме',
                            author='Vitaly Vasilchenko')
    doc.build(H + [body_t])

    try:  # число страниц нужно для автоподгонки
        from pypdf import PdfReader
        return len(PdfReader(out).pages)
    except ImportError:
        return 1


def build_fit(l, out):
    """Уменьшает шрифт ступеньками, пока резюме не уместится на одной странице."""
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
