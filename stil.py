# -*- coding: utf-8 -*-
"""Katman stili: e-Plan SLD kutuphanesi -> NCZ'nin kendi renkleri -> yedek.

DOLGU KARARI:
  * yalniz Kapali + Dolu bayrakli PLine alan olur,
  * NCZ'nin katman stili (LEX.ST2) varsa ve dolgu tanimlamiyorsa doldurulmaz,
  * stil yoksa yalniz e-Plan'da alan sinifi olan katmanlar doldurulur.
GORUNUM:
  * e-Plan kurali varsa: resmi tarama karosu / renk / merkez sembolu (eplan_style),
  * yoksa NCZ'nin kendi rengi ve saydamligi (duz renk).
"""
import base64
import os
import tempfile

from . import eplan_cizgi, eslesme
from . import eplan_style as E
from .ncz_okuyucu import palet_rgb, tcolor_rgb


class KatmanStili(object):
    def __init__(self):
        self.spec = None           # e-Plan RuleSpec
        self.yontem = ""
        self.dolgu = False         # bu katmanin kapali+dolu PLine'lari alan olur
        self.dosya_rgb = None      # NCZ'nin kendi dolgu rengi (yedek)
        self.dosya_alfa = 150
        self.cizgi_rgb = (0, 0, 0)
        self.desen = None          # NCZ'nin kendi DL deseni (yedek cizgi)
        self.kalinlik = 0.0
        self.cizgi_mm = None       # altlik cizgisi kalinligi (eslesme.DOSYA_CIZGI)
        self.lejant = None
        self.kaynak = "-"
        self.sembol_var = False    # katmanda sembol nesnesi var -> alan ortasi glifi basilmaz
        self.lt_kural = None       # NCZ cizgi tipi adindan e-Plan cizgi kurali (kaynak, baslik)


def katman_rgb(k):
    if k is None:
        return (0, 0, 0)
    if k.stil is not None and k.stil.renk_rgb:
        return tcolor_rgb(k.stil.renk)
    return palet_rgb(k.renk)


def gorunur(rgb):
    """Beyaz zeminde saf beyaz -> siyah."""
    return (0, 0, 0) if tuple(rgb) == (255, 255, 255) else tuple(rgb)


def _lejant(spec):
    t = (spec.title or "").strip()
    if not t or t.isdigit() or t.startswith(("NIP_", "UIP_", "CDP_")):
        t = E._strip_prefix(E.normalize(spec.source or ""))
    return t.replace("_", " ")


def cozumle(dosya, k, kademe, oncelik="eplan"):
    st = KatmanStili()
    spec, yontem = eslesme.bul(k.ad, kademe)
    st.spec, st.yontem = spec, yontem
    if spec is not None:
        st.lejant = _lejant(spec)

    s = k.stil
    if s is not None:
        st.dolgu = bool((s.duz_dolgu & 0x7F) or s.doku_id or k.tarama)
    else:
        st.dolgu = spec is not None and spec.geom == "polygon"
    # sinir/hat/kisit katmanlari ve e-Plan'da yalniz CIZGI olan siniflar (onlemli alan, plan
    # sinirlari) Netcad'de doldurulmaz; dosya stili dolgu tanimlasa bile
    if (spec is not None and spec.geom == "line") or \
            (k.ad or "").upper().startswith(("SNR_", "KST_", "HAT_")):
        st.dolgu = False
    if st.dolgu:
        st.dosya_rgb = katman_rgb(k)
        if s is not None and s.saydamlik > 1:
            st.dosya_alfa = 255 - s.saydamlik
        e_var = spec is not None and spec.geom == "polygon"
        if oncelik == "dosya" or not e_var:
            st.kaynak = "dosya"
        else:
            st.kaynak = "eplan"

    st.cizgi_rgb = gorunur(katman_rgb(k))
    st.cizgi_mm = eslesme.dosya_cizgi_mm(k.ad)
    lt = (s.cizgi_tipi if s is not None and s.cizgi_tipi else 0) or k.cizgi_tipi
    _ad, st.desen = cizgi_tipi(dosya, lt)
    try:
        st.lt_kural = eslesme.cizgi_tipi_kurali(_ad, kademe)
    except Exception:  # noqa
        st.lt_kural = None
    if s is not None:
        st.kalinlik = s.kalinlik
    return st


def cizgi_tipi(dosya, lt):
    """NCZ'nin kendi cizgi tipi tablosundan (ad, DL deseni)."""
    if lt and 0 < lt < len(dosya.cizgi_tipleri):
        c = dosya.cizgi_tipleri[lt]
        if c and c[0] and c[0].upper() != "DUZ":
            return c[0], (c[1] if len(c) > 1 else None)
    return None, None


# ===================================================================== QGIS
def _qc(rgb, alfa=255):
    from qgis.PyQt.QtGui import QColor
    return QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(max(0, min(255, alfa))))


_QML_DIR = []


def _qml_dir():
    if not _QML_DIR:
        d = os.path.join(tempfile.gettempdir(), "planEa2qgis_qml")
        if not os.path.isdir(d):
            os.makedirs(d)
        _QML_DIR.append(d)
    return _QML_DIR[0]


def eplan_uygula(lyr, st, geometri, olcek=1000):
    """e-Plan kuralini katmana uygular. Basarili ise True."""
    if st.spec is None:
        return False
    if geometri == "line" and st.spec.source != "yol":
        # mevzuat cizgisi: SLD'deki glif/kesik desen birebir (eplan_cizgi)
        eslesme.fontlari_yukle()
        sym = eplan_cizgi.cizgi_sembolu(st.spec.source, st.spec.title, olcek)
        if sym is not None:
            from qgis.core import QgsSingleSymbolRenderer
            lyr.setRenderer(QgsSingleSymbolRenderer(sym))
            return True
    eslesme.fontlari_yukle()
    guvenli = "".join(c if c.isalnum() else "_" for c in lyr.name())[:60]
    yol = os.path.join(_qml_dir(), "%s_%s.qml" % (guvenli, geometri))
    E.write_single_qml(yol, st.spec, geometry=geometri, layer_name=lyr.name())
    sonuc = lyr.loadNamedStyle(yol)
    ok = sonuc[1] if isinstance(sonuc, tuple) and len(sonuc) > 1 else bool(sonuc)
    if not ok:
        return False
    _karolari_gom(lyr)
    if geometri == "line":
        _sembol_seviyeleri(lyr)
    if geometri == "polygon":
        try:
            eplan_cizgi.alan_sembolunu_duzelt(lyr, st.spec, olcek, merkez_glif=not st.sembol_var,
                                              ek_kural=st.lt_kural)
        except Exception as e:  # noqa
            from .aktar import log
            log(u"%s: alan sembolu duzeltilemedi: %s" % (lyr.name(), e), 1)
    return True


def _sembol_seviyeleri(lyr):
    """Cok katmanli cizgi (yol kesiti): once tum objelerin zemini, sonra bantlar cizilsin.
    Yoksa kisa parcalardan olusan yolda her parcanin beyaz zemini oncekinin bandini orter."""
    r = lyr.renderer()
    sym = r.symbol() if r is not None and hasattr(r, "symbol") else None
    if sym is None or sym.symbolLayerCount() < 2:
        return
    for i in range(sym.symbolLayerCount()):
        sym.symbolLayer(i).setRenderingPass(i)
    r.setUsingSymbolLevels(True)


def _karolari_gom(lyr):
    """RasterFill karolarini 'base64:' olarak gomer -> .qgz tasininca da calisir."""
    from qgis.core import QgsRasterFillSymbolLayer, QgsRenderContext
    r = lyr.renderer()
    if r is None:
        return
    try:
        semboller = r.symbols(QgsRenderContext())
    except Exception:
        semboller = []
    for sym in semboller:
        for i in range(sym.symbolLayerCount()):
            sl = sym.symbolLayer(i)
            if isinstance(sl, QgsRasterFillSymbolLayer):
                p = sl.imageFilePath()
                if p and not p.startswith("base64:") and os.path.exists(p):
                    with open(p, "rb") as f:
                        sl.setImageFilePath("base64:" + base64.b64encode(f.read()).decode("ascii"))


def dosya_dolgu_sembolu(st):
    """e-Plan karsiligi yoksa: NCZ'nin kendi rengi, kendi saydamligiyla."""
    from qgis.core import QgsFillSymbol, QgsSimpleFillSymbolLayer, QgsUnitTypes
    from qgis.PyQt.QtCore import Qt
    sym = QgsFillSymbol()
    sym.deleteSymbolLayer(0)
    rgb = st.dosya_rgb or (200, 200, 200)
    sl = QgsSimpleFillSymbolLayer(_qc(rgb, st.dosya_alfa), Qt.SolidPattern,
                                  _qc(st.cizgi_rgb), Qt.SolidLine, 0.15)
    sl.setStrokeWidthUnit(QgsUnitTypes.RenderMillimeters)
    sym.appendSymbolLayer(sl)
    return sym


def dosya_cizgi_sembolu(rgb, desen, kalinlik, olcek, mm=None):
    """NCZ'nin kendi renk ve DL deseniyle cizgi (deger x olcek/1000 metre)."""
    from qgis.core import QgsLineSymbol, QgsSimpleLineSymbolLayer, QgsUnitTypes
    fak = max(olcek, 1.0) / 1000.0
    sl = QgsSimpleLineSymbolLayer(_qc(rgb))
    sl.setWidth(mm if mm else min(0.18 + (kalinlik or 0) * 0.35, 1.2))
    sl.setWidthUnit(QgsUnitTypes.RenderMillimeters)
    if desen and len(desen) >= 2 and any(v < 0 for v in desen):
        pat = [max(abs(v), 0.01) * fak for v in desen]
        if len(pat) % 2:
            pat.append(pat[-1])
        sl.setUseCustomDashPattern(True)
        sl.setCustomDashVector(pat)
        sl.setCustomDashPatternUnit(QgsUnitTypes.RenderMetersInMapUnits)
    sym = QgsLineSymbol()
    sym.deleteSymbolLayer(0)
    sym.appendSymbolLayer(sl)
    return sym
