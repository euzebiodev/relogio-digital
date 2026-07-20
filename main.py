import sys
import os
import ssl
import random
import threading
import urllib.request
import winreg
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QPushButton, QMenu, QSlider, QFontDialog, QSizePolicy,
    QSystemTrayIcon
)
from PyQt6.QtCore import QTimer, Qt, QTime, QDate, QPoint, QSize, QPointF, QSettings
from PyQt6.QtGui import (
    QFont, QFontMetrics, QFontDatabase, QColor, QPainter, QPainterPath,
    QAction, QPen, QPolygonF, QTransform, QPainterPathStroker, QPixmap, QIcon
)

_REG_RUN  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "RelogioDigital"

def _autostart_cmd():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    pythonw = sys.executable.replace('python.exe', 'pythonw.exe').replace('Python.exe', 'pythonw.exe')
    return f'"{pythonw}" "{os.path.abspath(__file__)}"'

def is_autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_RUN, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, _REG_NAME)
        return True
    except Exception:
        return False

def set_autostart(enable: bool):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_RUN, 0, winreg.KEY_SET_VALUE) as k:
            if enable:
                winreg.SetValueEx(k, _REG_NAME, 0, winreg.REG_SZ, _autostart_cmd())
            else:
                try:
                    winreg.DeleteValue(k, _REG_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass

# Pasta local para fontes baixadas (sem precisar de admin)
FONT_CACHE = os.path.join(os.environ.get('APPDATA', '.'), 'relogio-digital', 'fonts')

# Fontes disponíveis para download automático
DOWNLOADABLE_FONTS = {
    "DSEG7 Classic": {
        "url": "https://raw.githubusercontent.com/rbtdev/spiroplot/master/fonts/DSEG7/Classic/DSEG7Classic-Regular.ttf",
        "filename": "DSEG7Classic-Regular.ttf",
    },
    "DSEG7 Classic Mini": {
        "url": "https://raw.githubusercontent.com/rbtdev/spiroplot/master/fonts/DSEG7/Classic-MINI/DSEG7ClassicMini-Regular.ttf",
        "filename": "DSEG7ClassicMini-Regular.ttf",
    },
    "DSEG7 Modern": {
        "url": "https://raw.githubusercontent.com/rbtdev/spiroplot/master/fonts/DSEG7/Modern/DSEG7Modern-Regular.ttf",
        "filename": "DSEG7Modern-Regular.ttf",
    },
    "DSEG14 Classic": {
        "url": "https://raw.githubusercontent.com/BigBobbas/ESP32-S3-Box3-Custom-ESPHome/main/fonts/DSEG14Classic-Regular.ttf",
        "filename": "DSEG14Classic-Regular.ttf",
    },
    "Bebas Neue": {
        "url": "https://raw.githubusercontent.com/Scrum/font-bebas-neue/master/fonts/BebasNeue.ttf",
        "filename": "BebasNeue.ttf",
    },
    "Orbitron": {
        "url": "https://raw.githubusercontent.com/googlefonts/orbitron-vf/master/fonts/ttf/Orbitron-Medium.ttf",
        "filename": "Orbitron-Medium.ttf",
    },
}

# (rótulo, família Qt, chave em DOWNLOADABLE_FONTS ou None)
FONT_PRESETS = [
    ("7 Segmentos LED  ◀ renderizado (padrão)", "7seg",             None),
    (None, None, None),
    ("DSEG7 Classic  ◀ retro LCD",              "DSEG7 Classic",    "DSEG7 Classic"),
    ("DSEG7 Classic Mini  ◀ LCD compacto",       "DSEG7 Classic Mini","DSEG7 Classic Mini"),
    ("DSEG7 Modern  ◀ LCD moderno",              "DSEG7 Modern",     "DSEG7 Modern"),
    ("DSEG14 Classic  ◀ 14 segmentos",           "DSEG14 Classic",   "DSEG14 Classic"),
    (None, None, None),
    ("Bebas Neue  ◀ cinematic / fogo",            "Bebas Neue",       "Bebas Neue"),
    ("Orbitron  ◀ sci-fi / futurista",           "Orbitron",         "Orbitron"),
    (None, None, None),
    ("Consolas  (texto mono)",                   "Consolas",         None),
    ("Courier New  (clássica)",                  "Courier New",      None),
    ("Lucida Console",                           "Lucida Console",   None),
    ("OCR A Extended  (técnica)",                "OCR A Extended",   None),
]


# ── Temas de cor ──────────────────────────────────────────────────────────────
def _t(on, off, txt, date, btn, bg=(0,8,4), glow=False, scan=False, fire=False):
    return {"on": QColor(*on), "off": QColor(*off), "txt": txt, "date": date,
            "btn": btn, "bg": QColor(*bg), "glow": glow, "scan": scan, "fire": fire}

COLOR_THEMES = {
    "Verde neon":          _t((0,255,80),  (0,45,20),    "#00ff88","#aaffcc","#00ff58"),
    "Verde escuro":        _t((0,160,55),  (0,28,10),    "#00a037","#006622","#00a037"),
    "Âmbar":               _t((255,176,0), (55,38,0),    "#ffb000","#cc8800","#ffb000"),
    "Vermelho LED":        _t((255,55,55), (55,10,10),   "#ff3737","#cc2020","#ff3737"),
    "Branco":              _t((220,220,220),(65,65,65),  "#dcdcdc","#aaaaaa","#dcdcdc"),
    "Preto":               _t((28,28,28),  (185,185,185),"#1c1c1c","#444444","#1c1c1c"),
    "Ciano / Holográfico": _t((0,210,255), (0,38,58),    "#00d2ff","#0098bb","#00d2ff",
                               bg=(0,4,18), glow=True, scan=True),
    "O Problema dos 3 Corpos": _t((255,130,20),(50,8,0),     "#ff8214","#cc5010","#ff8214",
                               bg=(6,1,0),  fire=True),
}

N_FIRE_STRANDS = 7    # fios entrelaçados por segmento

# Camadas de cor para cada fio (multiplicador de espessura, R, G, B, alpha)
FIRE_LAYERS = [
    (5.0, 75,  6,   0,  12),
    (2.8, 165, 32,  0,  28),
    (1.6, 255, 88,  4,  55),
    (0.8, 255, 178, 22, 120),
    (0.38,255, 236, 138,200),
    (0.14,255, 255, 225,255),
]

# ── Estilos ────────────────────────────────────────────────────────────────────

STYLE_DATE = "color: #aaffcc; background: transparent; letter-spacing: 2px;"
STYLE_CLOCK = "color: #00ff88; background: transparent; letter-spacing: 4px;"

STYLE_BTN = """
    QPushButton {
        background: rgba(0,255,136,30); color: #00ff88;
        border: 1px solid rgba(0,255,136,80); border-radius: 4px;
        padding: 2px 8px; font-size: 14px; font-weight: bold;
    }
    QPushButton:hover  { background: rgba(0,255,136,70); }
    QPushButton:pressed{ background: rgba(0,255,136,120); }
"""
STYLE_BTN_ACTIVE = """
    QPushButton {
        background: rgba(0,255,136,120); color: #000;
        border: 1px solid #00ff88; border-radius: 4px;
        padding: 2px 8px; font-size: 14px; font-weight: bold;
    }
    QPushButton:hover { background: rgba(0,255,136,160); }
"""
STYLE_BTN_CLOSE = """
    QPushButton {
        background: rgba(255,50,50,40); color: #ff5555;
        border: 1px solid rgba(255,50,50,80); border-radius: 4px;
        padding: 2px 8px; font-size: 14px; font-weight: bold;
    }
    QPushButton:hover { background: rgba(255,50,50,120); color: #fff; }
"""
STYLE_SLIDER = """
    QSlider::groove:horizontal {
        height: 4px; background: rgba(0,255,136,30); border-radius: 2px;
    }
    QSlider::sub-page:horizontal {
        background: rgba(0,255,136,160); border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #00ff88; border: 1px solid rgba(0,255,136,180);
        width: 10px; height: 10px; margin: -3px 0; border-radius: 5px;
    }
    QSlider::handle:horizontal:hover { background: #aaffcc; }
"""
STYLE_MENU = """
    QMenu {
        background: rgba(10,20,15,220); color: #00ff88;
        border: 1px solid rgba(0,255,136,80); border-radius: 6px; padding: 4px;
    }
    QMenu::item           { padding: 6px 20px; border-radius: 3px; }
    QMenu::item:selected  { background: rgba(0,255,136,60); }
    QMenu::item:checked   { color: #aaffcc; }
    QMenu::item:disabled  { color: rgba(0,255,136,40); }
    QMenu::separator      { height: 1px; background: rgba(0,255,136,40); margin: 4px 8px; }
"""

# ── Display de 7 segmentos ─────────────────────────────────────────────────────

_SEG = {
    '0': (1,1,1,1,1,1,0), '1': (0,1,1,0,0,0,0), '2': (1,1,0,1,1,0,1),
    '3': (1,1,1,1,0,0,1), '4': (0,1,1,0,0,1,1), '5': (1,0,1,1,0,1,1),
    '6': (1,0,1,1,1,1,1), '7': (1,1,1,0,0,0,0), '8': (1,1,1,1,1,1,1),
    '9': (1,1,1,1,0,1,1),
}
_FIRE_COLORS = [QColor(r, g, b, a) for _, r, g, b, a in FIRE_LAYERS]


class SevenSegmentDisplay(QWidget):
    DIGIT_RATIO = 0.55
    COLON_RATIO = 0.25
    SPACING     = 0.06

    def __init__(self, digit_h=72, parent=None):
        super().__init__(parent)
        self._text      = "00:00:00"
        self._digit_h   = digit_h
        self._blink     = True
        self._flicker   = 1.0
        self._jitter    = []          # array plano de gauss para animação de fogo
        self.color_on   = QColor(0, 255, 80)
        self.color_off  = QColor(0, 45, 20)
        self.glow       = False
        self.scanlines  = False
        self.fire_mode  = False
        self._fire_timer = QTimer(self)
        self._fire_timer.timeout.connect(self._update_jitter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_digit_h(self, h):
        if h != self._digit_h:
            self._digit_h = h
            self.updateGeometry()
            self.update()

    def set_text(self, text, blink=True):
        if text != self._text or blink != self._blink:
            self._text  = text
            self._blink = blink
            self.update()

    def sizeHint(self):
        w, h = self._layout_size(self._digit_h)
        return QSize(w, h)

    def _layout_size(self, dh):
        dw = dh * self.DIGIT_RATIO
        cw = dh * self.COLON_RATIO
        sp = dh * self.SPACING
        n_col = self._text.count(':')
        n_dig = len(self._text) - n_col
        w = n_dig * dw + n_col * cw + (len(self._text) - 1) * sp
        return int(w) + 6, int(dh) + 6

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self.parent()
        if p and hasattr(p, '_bg_color') and hasattr(p, '_bg_opacity'):
            bg = p._bg_color
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), QColor(bg.red(), bg.green(), bg.blue(), p._bg_opacity))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if self._flicker < 1.0:
            painter.setOpacity(self._flicker)
        dh = float(self.height() - 6)
        dw = dh * self.DIGIT_RATIO
        cw = dh * self.COLON_RATIO
        sp = dh * self.SPACING
        x, y = 3.0, 3.0
        seg_idx = 0
        for ch in self._text:
            if ch == ':':
                if self.fire_mode:
                    self._draw_fire_colon(painter, x, y, cw, dh, seg_idx)
                else:
                    self._draw_colon(painter, x, y, cw, dh)
                seg_idx += 2
                x += cw + sp
            elif ch in _SEG:
                if self.fire_mode:
                    self._draw_fire_digit(painter, x, y, dw, dh, _SEG[ch], seg_idx)
                else:
                    self._draw_digit(painter, x, y, dw, dh, _SEG[ch])
                seg_idx += 7
                x += dw + sp
        if self.scanlines:
            painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(0, 0, 0, 40), 1))
            for scan_y in range(0, self.height(), 4):
                painter.drawLine(0, scan_y, self.width(), scan_y)

    def _poly_h(self, x, y, w, t, bv):
        return QPolygonF([
            QPointF(x+bv, y), QPointF(x+w-bv, y), QPointF(x+w, y+t*.5),
            QPointF(x+w-bv, y+t), QPointF(x+bv, y+t), QPointF(x, y+t*.5),
        ])

    def _poly_v(self, x, y, h, t, bv):
        return QPolygonF([
            QPointF(x+t*.5, y), QPointF(x+t, y+bv), QPointF(x+t, y+h-bv),
            QPointF(x+t*.5, y+h), QPointF(x, y+h-bv), QPointF(x, y+bv),
        ])

    def _scale_poly(self, poly, scale):
        pts = [poly.at(i) for i in range(poly.count())]
        cx = sum(p.x() for p in pts) / len(pts)
        cy = sum(p.y() for p in pts) / len(pts)
        return QPolygonF([QPointF(cx+(p.x()-cx)*scale, cy+(p.y()-cy)*scale) for p in pts])

    def _paint_seg(self, painter, poly, on):
        painter.setPen(Qt.PenStyle.NoPen)
        if on and self.glow:
            c = self.color_on
            for scale, alpha in [(3.2, 12), (2.0, 22), (1.4, 40)]:
                painter.setBrush(QColor(c.red(), c.green(), c.blue(), alpha))
                painter.drawPolygon(self._scale_poly(poly, scale))
        painter.setBrush(self.color_on if on else self.color_off)
        painter.drawPolygon(poly)

    def _draw_digit(self, painter, ox, oy, dw, dh, segs):
        sa, sb, sc, sd, se, sf, sg = segs
        t = dh * .13; g = dh * .025; bv = t * .45
        hw = dw - 2*(t+g); hx = ox+t+g
        vh = dh/2 - t - 2*g
        vx_l = ox+g; vx_r = ox+dw-g-t
        y_top = oy+g; y_mid = oy+dh/2-t/2; y_bot = oy+dh-g-t
        vy_t = oy+g+t+g; vy_b = oy+dh/2+g
        self._paint_seg(painter, self._poly_h(hx,   y_top, hw, t, bv), sa)
        self._paint_seg(painter, self._poly_v(vx_r, vy_t,  vh, t, bv), sb)
        self._paint_seg(painter, self._poly_v(vx_r, vy_b,  vh, t, bv), sc)
        self._paint_seg(painter, self._poly_h(hx,   y_bot, hw, t, bv), sd)
        self._paint_seg(painter, self._poly_v(vx_l, vy_b,  vh, t, bv), se)
        self._paint_seg(painter, self._poly_v(vx_l, vy_t,  vh, t, bv), sf)
        self._paint_seg(painter, self._poly_h(hx,   y_mid, hw, t, bv), sg)

    def _draw_colon(self, painter, x, y, cw, dh):
        is_on = self._blink
        painter.setPen(Qt.PenStyle.NoPen)
        r = dh * .07; cx = x + cw / 2
        p1 = QPointF(cx, y + dh / 3)
        p2 = QPointF(cx, y + 2 * dh / 3)
        if is_on and self.glow:
            c = self.color_on
            for scale, alpha in [(3.0, 12), (1.8, 28)]:
                painter.setBrush(QColor(c.red(), c.green(), c.blue(), alpha))
                painter.drawEllipse(p1, r * scale, r * scale)
                painter.drawEllipse(p2, r * scale, r * scale)
        painter.setBrush(self.color_on if is_on else self.color_off)
        painter.drawEllipse(p1, r, r)
        painter.drawEllipse(p2, r, r)

    # ── Modo Fogo / Plasma ─────────────────────────────────────────────────────

    def _update_jitter(self):
        # Array grande de valores gaussianos reutilizados por índice
        self._jitter = [random.gauss(0, 1.0) for _ in range(4000)]
        self.update()

    def _j(self, idx):
        return self._jitter[idx % 4000] if self._jitter else 0.0

    def _strand_h(self, x1, y, x2, seg_i, strand_i, amp):
        """Um fio horizontal com Bézier cúbico e desvio caótico."""
        b = (seg_i * 61 + strand_i * 13) % 4000
        w = x2 - x1
        sx  = x1 + self._j(b)   * amp * 0.07
        sy  = y  + self._j(b+1) * amp * 0.14
        ex  = x2 + self._j(b+2) * amp * 0.07
        ey  = y  + self._j(b+3) * amp * 0.14
        cx1 = x1 + w * 0.28 + self._j(b+4) * amp * 0.7
        cy1 = y  + self._j(b+5) * amp * 0.9
        cx2 = x1 + w * 0.72 + self._j(b+6) * amp * 0.7
        cy2 = y  + self._j(b+7) * amp * 0.9
        p = QPainterPath(); p.moveTo(sx, sy); p.cubicTo(cx1, cy1, cx2, cy2, ex, ey)
        return p

    def _strand_v(self, x, y1, y2, seg_i, strand_i, amp):
        """Um fio vertical com Bézier cúbico e desvio caótico."""
        b = (seg_i * 61 + strand_i * 13 + 5) % 4000
        h = y2 - y1
        sx  = x  + self._j(b)   * amp * 0.14
        sy  = y1 + self._j(b+1) * amp * 0.07
        ex  = x  + self._j(b+2) * amp * 0.14
        ey  = y2 + self._j(b+3) * amp * 0.07
        cx1 = x  + self._j(b+4) * amp * 0.9
        cy1 = y1 + h * 0.28 + self._j(b+5) * amp * 0.7
        cx2 = x  + self._j(b+6) * amp * 0.9
        cy2 = y1 + h * 0.72 + self._j(b+7) * amp * 0.7
        p = QPainterPath(); p.moveTo(sx, sy); p.cubicTo(cx1, cy1, cx2, cy2, ex, ey)
        return p

    def _fire_strands(self, painter, paths, base_w):
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for (mult, *_), color in zip(FIRE_LAYERS, _FIRE_COLORS):
            pen = QPen(color, base_w * mult)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            for path in paths:
                painter.drawPath(path)

    def _draw_fire_digit(self, painter, ox, oy, dw, dh, segs, base_idx):
        sa, sb, sc, sd, se, sf, sg = segs
        t   = dh * 0.055   # espessura por fio
        g   = dh * 0.04
        amp = dh * 0.09    # amplitude do desvio — mantém dígito legível
        N   = N_FIRE_STRANDS

        hw  = dw - 2*(t+g); hx1 = ox+t+g; hx2 = hx1+hw
        vh  = dh/2 - t - 2*g
        vxl = ox + g + t*0.5;  vxr = ox + dw - g - t*0.5
        yt  = oy + g + t*0.5;  ym  = oy + dh/2;  yb = oy + dh - g - t*0.5
        vt1 = oy + g + t;      vt2 = vt1 + vh
        vb1 = oy + dh/2 + g;   vb2 = vb1 + vh

        defs = [
            (sa, 'h', hx1, yt,  hx2, 0),
            (sb, 'v', vxr, vt1, vt2, 1),
            (sc, 'v', vxr, vb1, vb2, 2),
            (sd, 'h', hx1, yb,  hx2, 3),
            (se, 'v', vxl, vb1, vb2, 4),
            (sf, 'v', vxl, vt1, vt2, 5),
            (sg, 'h', hx1, ym,  hx2, 6),
        ]
        for active, kind, a1, a2, a3, si in defs:
            if not active:
                continue
            seg_i = base_idx + si
            if kind == 'h':
                paths = [self._strand_h(a1, a2, a3, seg_i, s, amp) for s in range(N)]
            else:
                paths = [self._strand_v(a1, a2, a3, seg_i, s, amp) for s in range(N)]
            self._fire_strands(painter, paths, t)

    def _draw_fire_colon(self, painter, x, y, cw, dh, base_idx):
        if not self._blink:
            return
        t   = dh * 0.048
        amp = dh * 0.10
        cx  = x + cw / 2
        N   = N_FIRE_STRANDS // 2
        for di, dot_y in enumerate([y + dh/3, y + 2*dh/3]):
            paths = []
            for s in range(N):
                b   = (base_idx * 61 + di * 29 + s * 13) % 4000
                r   = dh * 0.085 * (0.75 + abs(self._j(b)) * 0.35)
                ccx = cx    + self._j(b+1) * amp * 0.28
                ccy = dot_y + self._j(b+2) * amp * 0.28
                path = QPainterPath()
                path.addEllipse(QPointF(ccx, ccy), r, r)
                paths.append(path)
            self._fire_strands(painter, paths, t)


# ── Display de fogo para fontes de texto ──────────────────────────────────────

class FireTextDisplay(QWidget):
    """Renderiza qualquer fonte com efeito de fios de fogo entrelaçados."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text        = "00:00:00"
        self._font_name   = "Consolas"
        self._font_size   = 72
        self._jitter      = []
        self._text_path   = None
        self._path_key    = None
        self._fire_timer  = QTimer(self)
        self._fire_timer.timeout.connect(self._upd_jitter)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def set_font(self, name, size):
        self._font_name = name
        self._font_size = size
        self.updateGeometry()
        self.update()

    def set_text(self, text):
        if text != self._text:
            self._text = text
            self.update()

    def start_fire(self):
        self._fire_timer.start(65)

    def stop_fire(self):
        self._fire_timer.stop()
        self._jitter = []

    def _upd_jitter(self):
        self._jitter = [random.gauss(0, 1.0) for _ in range(2000)]
        self.update()

    def _j(self, idx):
        return self._jitter[idx % 2000] if self._jitter else 0.0

    def _qfont(self):
        return QFont(self._font_name, self._font_size, QFont.Weight.Bold)

    def sizeHint(self):
        fm = QFontMetrics(self._qfont())
        pad = int(self._font_size * 0.35)
        return QSize(fm.horizontalAdvance(self._text) + pad * 2,
                     fm.height() + pad * 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = self._qfont()
        fm   = QFontMetrics(font)
        pad  = self._font_size * 0.25
        tw   = fm.horizontalAdvance(self._text)
        tx   = (self.width()  - tw) / 2
        ty   = pad + fm.ascent()

        t = self._font_size * 0.038

        path_key = (self._text, self._font_name, self._font_size, tx, ty)
        if self._path_key != path_key:
            self._text_path = QPainterPath()
            self._text_path.addText(tx, ty, font, self._text)
            self._path_key = path_key
        text_path = self._text_path

        N   = N_FIRE_STRANDS
        amp = self._font_size * 0.045
        offsets = [(self._j(s * 5) * amp, self._j(s * 5 + 1) * amp * 0.55)
                   for s in range(N)]

        # Por camada: cria banda ao redor das bordas e remove o interior sólido
        # com .subtracted() — evita que o fogo preencha o interior dos dígitos
        painter.setPen(Qt.PenStyle.NoPen)
        for mult, r, g, b, a in FIRE_LAYERS:
            stroker = QPainterPathStroker()
            stroker.setWidth(max(1.5, t * mult * 2.8))
            stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
            stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            band = stroker.createStroke(text_path).subtracted(text_path)
            painter.setBrush(QColor(r, g, b, a))
            for dx, dy in offsets:
                painter.drawPath(QTransform().translate(dx, dy).map(band))



# ── Janela principal ───────────────────────────────────────────────────────────

class DigitalClock(QWidget):
    def __init__(self):
        super().__init__()
        self.font_size     = 72
        self.font_name     = "7seg"
        self.always_on_top = True
        self._drag_pos     = None
        self._bg_opacity   = 180
        self._downloading  = set()
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status)
        self.color_theme   = "Verde neon"
        self._bg_color     = QColor(0, 8, 4)
        self._holo_timer   = None

        self._avail_fonts = set(QFontDatabase.families())
        self._load_cached_fonts()
        self._load_settings()

        self._init_window()
        self._build_ui()
        self._start_timer()
        self._init_tray()
        QApplication.instance().aboutToQuit.connect(self._save_settings)

    # ── Persistência de configurações ─────────────────────────────────────────

    def _qsettings(self):
        path = os.path.join(os.environ.get('APPDATA', '.'), 'relogio-digital', 'settings.ini')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return QSettings(path, QSettings.Format.IniFormat)

    def _load_settings(self):
        s = self._qsettings()
        self.font_name     = str(s.value("font_name", "7seg"))
        self.color_theme   = str(s.value("color_theme", "Verde neon"))
        self.always_on_top = s.value("always_on_top", True, type=bool)
        try:
            self.font_size = max(20, min(240, int(s.value("font_size", 72))))
        except (ValueError, TypeError):
            self.font_size = 72
        try:
            self._bg_opacity = max(20, min(245, int(s.value("bg_opacity", 180))))
        except (ValueError, TypeError):
            self._bg_opacity = 180
        if self.color_theme not in COLOR_THEMES:
            self.color_theme = "Verde neon"
        if self.font_name != "7seg" and self.font_name not in self._avail_fonts:
            self.font_name = "7seg"
        self._bg_color = COLOR_THEMES[self.color_theme]["bg"]

    def _save_settings(self):
        s = self._qsettings()
        s.setValue("font_name",    self.font_name)
        s.setValue("font_size",    self.font_size)
        s.setValue("color_theme",  self.color_theme)
        s.setValue("bg_opacity",   self._bg_opacity)
        s.setValue("always_on_top", self.always_on_top)
        s.sync()

    def _schedule_save(self):
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_settings)
        self._save_timer.start(600)

    # ── Inicialização ──────────────────────────────────────────────────────────

    def _init_window(self):
        self._apply_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Relógio Digital")
        self.setMinimumSize(280, 120)

    def _apply_flags(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _load_cached_fonts(self):
        """Carrega fontes baixadas anteriormente da pasta de cache."""
        if not os.path.isdir(FONT_CACHE):
            return
        for fname in os.listdir(FONT_CACHE):
            if fname.lower().endswith(('.ttf', '.otf')):
                fid = QFontDatabase.addApplicationFont(os.path.join(FONT_CACHE, fname))
                if fid >= 0:
                    for fam in QFontDatabase.applicationFontFamilies(fid):
                        self._avail_fonts.add(fam)

    def _build_ui(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(16, 12, 16, 10)
        self._root.setSpacing(4)

        self.seg_display = SevenSegmentDisplay(self.font_size, self)

        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(STYLE_CLOCK)
        self.time_label.hide()

        self.fire_text = FireTextDisplay(self)
        self.fire_text.hide()

        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet(STYLE_DATE)

        self._ctrl_bar = QWidget(self)
        self._ctrl_bar.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._ctrl_bar.setAutoFillBackground(False)
        self._ctrl_bar.hide()
        ctrl = QHBoxLayout(self._ctrl_bar)
        ctrl.setContentsMargins(0, 0, 0, 0)
        ctrl.setSpacing(4)

        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedSize(28, 24)
        self.btn_minus.setStyleSheet(STYLE_BTN)
        self.btn_minus.setToolTip("Diminuir tamanho (scroll ↓)")
        self.btn_minus.clicked.connect(self.decrease_size)

        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(28, 24)
        self.btn_plus.setStyleSheet(STYLE_BTN)
        self.btn_plus.setToolTip("Aumentar tamanho (scroll ↑)")
        self.btn_plus.clicked.connect(self.increase_size)

        self.btn_font = QPushButton("Aa")
        self.btn_font.setFixedSize(28, 24)
        self.btn_font.setStyleSheet(STYLE_BTN)
        self.btn_font.setToolTip("Escolher fonte")
        self.btn_font.clicked.connect(self._show_font_menu)

        self.btn_color = QPushButton("●")
        self.btn_color.setFixedSize(28, 24)
        self.btn_color.setToolTip("Cor dos dígitos")
        self.btn_color.clicked.connect(self._show_color_menu)

        self.btn_pin = QPushButton("📌")
        self.btn_pin.setFixedSize(28, 24)
        self.btn_pin.clicked.connect(self.toggle_always_on_top)
        self._update_pin_style()

        opacity_label = QLabel("◑")
        opacity_label.setStyleSheet(
            "color: rgba(0,255,136,140); background: transparent; font-size: 13px;"
        )

        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 245)
        self.slider_opacity.setValue(self._bg_opacity)
        self.slider_opacity.setFixedWidth(72)
        self.slider_opacity.setFixedHeight(24)
        self.slider_opacity.setStyleSheet(STYLE_SLIDER)
        self.slider_opacity.setToolTip(f"Transparência: {self._bg_opacity}")
        self.slider_opacity.valueChanged.connect(self._on_opacity_changed)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(28, 24)
        self.btn_close.setStyleSheet(STYLE_BTN_CLOSE)
        self.btn_close.setToolTip("Minimizar para a bandeja do sistema")
        self.btn_close.clicked.connect(self.hide)

        ctrl.addWidget(self.btn_minus)
        ctrl.addWidget(self.btn_plus)
        ctrl.addWidget(self.btn_font)
        ctrl.addWidget(self.btn_color)
        ctrl.addWidget(self.btn_pin)
        ctrl.addStretch()
        ctrl.addWidget(opacity_label)
        ctrl.addWidget(self.slider_opacity)
        ctrl.addStretch()
        ctrl.addWidget(self.btn_close)

        self._root.addWidget(self.seg_display, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._root.addWidget(self.time_label)
        self._root.addWidget(self.fire_text)
        self._root.addWidget(self.date_label)
        self._root.addWidget(self._ctrl_bar)

        self._update_fonts()

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)
        self._tick()
        self._hide_ctrl_timer = QTimer(self)
        self._hide_ctrl_timer.setSingleShot(True)
        self._hide_ctrl_timer.setInterval(500)
        self._hide_ctrl_timer.timeout.connect(self._hide_controls)

    def _show_controls(self):
        self._hide_ctrl_timer.stop()
        if not self._ctrl_bar.isVisible():
            self._ctrl_bar.show()
            self.adjustSize()

    def _hide_controls(self):
        if self._ctrl_bar.isVisible():
            self._ctrl_bar.hide()
            self.adjustSize()

    def enterEvent(self, event):
        self._show_controls()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hide_ctrl_timer.start()
        super().leaveEvent(event)

    def _tick(self):
        now   = QTime.currentTime()
        blink = now.second() % 2 == 0

        time_str   = now.toString("hh:mm:ss")
        time_blink = now.toString("hh mm ss").replace(" ", ":") if not blink else time_str
        is_fire    = COLOR_THEMES[self.color_theme]["fire"]

        if self.font_name == "7seg":
            self.seg_display.set_text(time_str, blink)
        elif is_fire:
            self.fire_text.set_text(time_blink)
        else:
            self.time_label.setText(time_blink)

        if not getattr(self, '_status_active', False):
            today  = QDate.currentDate()
            days   = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
            months = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
            self.date_label.setText(
                f"{days[today.dayOfWeek()-1]}, {today.day():02d} {months[today.month()-1]} {today.year()}"
            )

    def _update_fonts(self):
        is_fire = COLOR_THEMES[self.color_theme]["fire"]
        if self.font_name == "7seg":
            w, h = self.seg_display._layout_size(self.font_size)
            self.seg_display.set_digit_h(self.font_size)
            self.seg_display.setFixedSize(w, h)
        elif is_fire:
            self.fire_text.set_font(self.font_name, self.font_size)
        else:
            font = QFont(self.font_name, self.font_size, QFont.Weight.Bold)
            self.time_label.setFont(font)
            self.time_label.setStyleSheet(STYLE_CLOCK + f"font-size: {self.font_size}px;")

        date_size = max(10, self.font_size // 5)
        self.date_label.setFont(QFont("Consolas", date_size))
        self._apply_theme()
        self.adjustSize()

    def _update_pin_style(self):
        if self.always_on_top:
            self.btn_pin.setStyleSheet(STYLE_BTN_ACTIVE)
            self.btn_pin.setToolTip("Sempre no topo: LIGADO (clique para desligar)")
        else:
            self.btn_pin.setStyleSheet(STYLE_BTN)
            self.btn_pin.setToolTip("Sempre no topo: desligado (clique para ligar)")

    # ── Temas de cor ──────────────────────────────────────────────────────────

    def _apply_theme(self):
        t = COLOR_THEMES[self.color_theme]
        self._bg_color = t["bg"]

        self.seg_display.color_on  = t["on"]
        self.seg_display.color_off = t["off"]
        self.seg_display.glow      = t["glow"]
        self.seg_display.scanlines = t["scan"]
        self.seg_display.fire_mode = t["fire"]
        if t["fire"]:
            self.seg_display._fire_timer.start(65)
        else:
            self.seg_display._fire_timer.stop()
            self.seg_display._jitter = []
        self.seg_display.update()

        date_size = max(10, self.font_size // 5)
        self.time_label.setStyleSheet(
            f"color:{t['txt']}; background:transparent; letter-spacing:4px;"
            f"font-size:{self.font_size}px;"
        )
        self.date_label.setStyleSheet(
            f"color:{t['date']}; background:transparent; letter-spacing:2px;"
            f"font-size:{date_size}px;"
        )
        self.btn_color.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,0,0,0); color: {t['btn']};
                border: 1px solid {t['btn']}88;
                border-radius: 4px; font-size: 16px;
            }}
            QPushButton:hover {{ background: {t['btn']}22; }}
        """)
        self.update()  # redesenha o fundo com nova cor
        if hasattr(self, '_tray') and self._tray:
            self._tray.setIcon(self._make_tray_icon())

        # Fire text display (fontes de texto no modo fogo)
        if t["fire"] and self.font_name != "7seg":
            self.fire_text.start_fire()
        else:
            self.fire_text.stop_fire()
        self._show_active_display()

        # Timer de flicker para o modo holográfico
        if t["glow"]:
            if not self._holo_timer:
                self._holo_timer = QTimer(self)
                self._holo_timer.timeout.connect(self._holo_tick)
            self._holo_timer.start(120)
        else:
            if self._holo_timer:
                self._holo_timer.stop()
            self.seg_display._flicker = 1.0

    def _holo_tick(self):
        # Flicker sutil: 8% de chance de variar levemente a opacidade
        self.seg_display._flicker = random.uniform(0.78, 0.96) if random.random() < 0.08 else 1.0
        self.seg_display.update()

    # ── Bandeja do sistema ─────────────────────────────────────────────────────

    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._make_tray_icon())
        self._tray.setToolTip("Relógio Digital")

        menu = QMenu()
        menu.setStyleSheet(STYLE_MENU)

        act_show = QAction("  Mostrar / Ocultar", menu)
        act_show.triggered.connect(self._toggle_visible)
        menu.addAction(act_show)

        menu.addSeparator()

        self._act_startup = QAction("  Iniciar com o Windows", menu)
        self._act_startup.setCheckable(True)
        self._act_startup.setChecked(is_autostart_enabled())
        self._act_startup.triggered.connect(lambda checked: set_autostart(checked))
        menu.addAction(self._act_startup)

        menu.addSeparator()

        act_quit = QAction("  Fechar", menu)
        act_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_quit)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _make_tray_icon(self):
        t = COLOR_THEMES[self.color_theme]
        c  = t["on"]
        bg = t["bg"]
        size = 32
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = cy = size / 2
        r = size / 2 - 2
        p.setBrush(QColor(bg.red(), bg.green(), bg.blue(), 230))
        p.setPen(QPen(c, 1.5))
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.setPen(QPen(c, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        # ponteiro hora (~10h)
        p.save(); p.translate(cx, cy); p.rotate(-60)
        p.drawLine(QPointF(0, 0), QPointF(0, -(r * 0.50))); p.restore()
        # ponteiro minuto (~2h)
        p.save(); p.translate(cx, cy); p.rotate(60)
        p.drawLine(QPointF(0, 0), QPointF(0, -(r * 0.72))); p.restore()
        p.setBrush(c); p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), 1.8, 1.8)
        p.end()
        return QIcon(pm)

    def _toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_visible()

    def _show_color_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(STYLE_MENU)
        for name in COLOR_THEMES:
            act = QAction(f"  ● {name}", self)
            act.setCheckable(True)
            act.setChecked(name == self.color_theme)
            act.triggered.connect(lambda checked, n=name: self._set_color_theme(n))
            menu.addAction(act)
        menu.exec(self.btn_color.mapToGlobal(QPoint(0, self.btn_color.height())))

    def _set_color_theme(self, name):
        self.color_theme = name
        self._apply_theme()
        self._schedule_save()

    # ── Status temporário no date_label ───────────────────────────────────────

    def _show_status(self, msg, duration_ms=0):
        self._status_active = True
        self.date_label.setText(msg)
        self._status_timer.stop()
        if duration_ms > 0:
            self._status_timer.start(duration_ms)

    def _clear_status(self):
        self._status_active = False
        self._tick()

    # ── Seleção de fonte ───────────────────────────────────────────────────────

    def _show_font_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(STYLE_MENU)
        self._populate_font_menu(menu)
        menu.exec(self.btn_font.mapToGlobal(QPoint(0, self.btn_font.height())))

    def _populate_font_menu(self, menu):
        for label, family, dl_key in FONT_PRESETS:
            if label is None:
                menu.addSeparator()
                continue

            if family == "7seg":
                act = QAction(f"  {label}", self)
                act.setCheckable(True)
                act.setChecked(self.font_name == "7seg")
                act.triggered.connect(lambda: self._set_font("7seg"))
                menu.addAction(act)
                continue

            available = family in self._avail_fonts

            if available:
                act = QAction(f"  {label}", self)
                act.setCheckable(True)
                act.setChecked(family == self.font_name)
                act.triggered.connect(lambda checked, f=family: self._set_font(f))
            elif dl_key and dl_key in DOWNLOADABLE_FONTS:
                if dl_key in self._downloading:
                    act = QAction(f"  ⏳ Baixando {label}...", self)
                    act.setEnabled(False)
                else:
                    act = QAction(f"  ⬇  Baixar e instalar: {label}", self)
                    act.triggered.connect(lambda checked, k=dl_key: self._download_font(k))
            else:
                act = QAction(f"  {label}  [instalar manualmente]", self)
                act.setEnabled(False)

            menu.addAction(act)

        menu.addSeparator()
        act_other = QAction("  Outras fontes...", self)
        act_other.triggered.connect(self._open_font_dialog)
        menu.addAction(act_other)

    def _set_font(self, family):
        self.font_name = family
        self._show_active_display()
        self._update_fonts()
        self._schedule_save()

    def _show_active_display(self):
        is_fire = COLOR_THEMES[self.color_theme]["fire"]
        use_seg  = self.font_name == "7seg"
        use_fire = not use_seg and is_fire
        use_text = not use_seg and not is_fire
        self.seg_display.setVisible(use_seg)
        self.fire_text.setVisible(use_fire)
        self.time_label.setVisible(use_text)

    def _open_font_dialog(self):
        initial = QFont("Consolas" if self.font_name == "7seg" else self.font_name, self.font_size)
        font, ok = QFontDialog.getFont(initial, self, "Escolher fonte do relógio")
        if ok:
            self._set_font(font.family())

    # ── Download automático de fontes ──────────────────────────────────────────

    def _download_font(self, dl_key):
        if dl_key in self._downloading:
            return
        self._downloading.add(dl_key)
        self._show_status(f"⬇ Baixando {dl_key}...")

        info = DOWNLOADABLE_FONTS[dl_key]
        os.makedirs(FONT_CACHE, exist_ok=True)
        dest = os.path.join(FONT_CACHE, info['filename'])
        url  = info['url']

        def do_download():
            try:
                ctx = ssl.create_default_context()
                req = urllib.request.Request(url, headers={"User-Agent": "RelogioDigital/1.0"})
                with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                    data = resp.read()
                with open(dest, 'wb') as f:
                    f.write(data)
                QTimer.singleShot(0, lambda: self._on_font_downloaded(dl_key, dest))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._on_font_error(dl_key, str(e)))

        threading.Thread(target=do_download, daemon=True).start()

    def _on_font_downloaded(self, dl_key, path):
        self._downloading.discard(dl_key)
        fid = QFontDatabase.addApplicationFont(path)
        if fid >= 0:
            families = QFontDatabase.applicationFontFamilies(fid)
            for fam in families:
                self._avail_fonts.add(fam)
            target = families[0] if families else dl_key
            self._show_status(f"✔ {dl_key} instalada!", duration_ms=3000)
            self._set_font(target)
        else:
            self._on_font_error(dl_key, "arquivo inválido")

    def _on_font_error(self, dl_key, msg):
        self._downloading.discard(dl_key)
        self._show_status(f"✘ Erro ao baixar {dl_key}: {msg}", duration_ms=4000)

    # ── Controle de opacidade ──────────────────────────────────────────────────

    def _on_opacity_changed(self, value):
        self._bg_opacity = value
        self.slider_opacity.setToolTip(f"Transparência: {value}")
        self.update()
        self._schedule_save()

    # ── Tamanho da fonte ───────────────────────────────────────────────────────

    def increase_size(self):
        if self.font_size < 240:
            self.font_size += 12
            self._update_fonts()
            self._schedule_save()

    def decrease_size(self):
        if self.font_size > 20:
            self.font_size -= 12
            self._update_fonts()
            self._schedule_save()

    # ── Sempre no topo ─────────────────────────────────────────────────────────

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self._apply_flags()
        self.show()
        self._update_pin_style()
        self._schedule_save()

    # ── Arraste com mouse ──────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Scroll redimensiona ────────────────────────────────────────────────────

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.increase_size()
        else:
            self.decrease_size()

    # ── Menu de contexto (botão direito) ───────────────────────────────────────

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet(STYLE_MENU)

        act_plus = QAction("  Aumentar tamanho  (+)", self)
        act_plus.triggered.connect(self.increase_size)
        menu.addAction(act_plus)

        act_minus = QAction("  Diminuir tamanho  (−)", self)
        act_minus.triggered.connect(self.decrease_size)
        menu.addAction(act_minus)

        menu.addSeparator()

        font_menu = menu.addMenu("  Fonte")
        font_menu.setStyleSheet(STYLE_MENU)
        self._populate_font_menu(font_menu)

        color_menu = menu.addMenu("  Cor dos dígitos")
        color_menu.setStyleSheet(STYLE_MENU)
        for name in COLOR_THEMES:
            act = QAction(f"  ● {name}", self)
            act.setCheckable(True)
            act.setChecked(name == self.color_theme)
            act.triggered.connect(lambda checked, n=name: self._set_color_theme(n))
            color_menu.addAction(act)

        menu.addSeparator()

        act_opaque = QAction("  Fundo mais opaco  (▲)", self)
        act_opaque.triggered.connect(
            lambda: self.slider_opacity.setValue(min(245, self._bg_opacity + 20))
        )
        menu.addAction(act_opaque)

        act_transp = QAction("  Fundo mais transparente  (▼)", self)
        act_transp.triggered.connect(
            lambda: self.slider_opacity.setValue(max(20, self._bg_opacity - 20))
        )
        menu.addAction(act_transp)

        menu.addSeparator()

        pin_label = "  ✔ Sempre no topo (desligar)" if self.always_on_top else "  Sempre no topo (ligar)"
        act_pin = QAction(pin_label, self)
        act_pin.triggered.connect(self.toggle_always_on_top)
        menu.addAction(act_pin)

        menu.addSeparator()

        act_close = QAction("  Fechar", self)
        act_close.triggered.connect(QApplication.instance().quit)
        menu.addAction(act_close)

        menu.exec(event.globalPos())

    # ── Fundo arredondado translúcido ──────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        bg = self._bg_color
        painter.fillPath(path, QColor(bg.red(), bg.green(), bg.blue(), self._bg_opacity))
        t = COLOR_THEMES[self.color_theme]
        border = t["on"]
        painter.setPen(QPen(QColor(border.red(), border.green(), border.blue(), 55), 1))
        painter.drawPath(path)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    clock = DigitalClock()
    clock.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
