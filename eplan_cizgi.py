# -*- coding: utf-8 -*-
"""e-Plan SLD cizgi gosterimi -> QGIS (mevzuattaki lejand cizgileri).

e-Plan SLD'lerinde sinir/hat cizgilerinin cogu GeoServer GraphicStroke ile tanimli:

  <LineSymbolizer uom=metre>
    <Stroke>
      <GraphicStroke><Graphic><Mark><WellKnownName>ttf://OG_V_1_1#0x0052</WellKnownName>
           <Fill>renk</Fill></Mark><Size>15</Size></Graphic></GraphicStroke>
      <CssParameter name="stroke-dasharray">16 2</CssParameter>
    </Stroke>
    <PerpendicularOffset>..</PerpendicularOffset>
  </LineSymbolizer>

Yorum (GeoServer):
  * glif en buyuk boyutu Size olacak sekilde olceklenir, cizgi yonunde dondurulur,
    sinir kutusunun ortasi cizginin uzerine gelir;
  * dasharray varsa her (cizgi + bosluk) periyodunda bir glif, cizgi parcasinin ortasina;
    yoksa glifler uc uca (aralik = glif boyu).
  * Degerler pafta milimetresi gibidir (NIP ve UIP'te ayni sayilar): dunya boyu =
    deger x plan olcegi / 1000 metre. Kontrol: NIP ilce sinirinda 1/25000'de 18 mm periyot.
Duz (glifsiz) cizgilerde stroke, stroke-width, stroke-dasharray, PerpendicularOffset ayni
olcekle uygulanir.
"""
import os
import re
import xml.etree.ElementTree as ET  # nosec B405 - yalniz eklentiyle gelen SLD
from qgis.core import Qgis  # Qt6/QGIS 4: Qgis.RenderUnit

STIL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eplan", "styles")

# ---- pafta olcusu ayari (mevzuat lejandi ile olculup ayarlandi; bkz. README) ----
# e-Plan SLD glif boylari mevzuattaki pafta olculerine tek oranla oturmuyor; glif turune gore:
UZUN_GLIF_ORANI = 3.0       # genislik/yukseklik >= bu ise "desen parcasi" (cizgi+nokta)
SEMBOL_GLIF = 0.25          # kesik desenli kucuk sembol (plan onama dairesi): boy = Size x bu
SEMBOL_PERIYOT = 0.35       #   ... periyot = desen toplami x bu
DESENSIZ_GLIF = 0.32        # desensiz glif dizisi (sit, onlemli alan): boy = Size x bu, uc uca
ALAN_GLIF_YUKSEKLIK = 0.45  # alan merkez sembolu (PARK, BHA, OSB): yukseklik = Size x bu
                            # (Netcad'de BHA kutusu yapilasma yazisinin ~1,85 kati)
SEMBOL_BIRIM_M = 8.0        # PL katmanindaki sembol nesnesi: yukseklik = nesne olcegi (SC) x bu (m)
KALEM_VARSAYILAN = 0.35     # desen glifi ince cizgiye cevrilirken SLD'de kalem yoksa (mm)
# Kademeye gore glif/periyot carpani. Yukaridaki oranlar UIP'de Netcad'e gore olculdu;
# NIP paftasinda (1/25000) Netcad'in desensiz glif dizileri (kentsel donusum daireleri,
# onlemli alan, sit) ~2.9 kat buyuk; desenli kucuk semboller (artilar, halkalar) UIP oraninda.
KADEME_CARPANI = {"UIP": 1.0, "NIP": 2.85, "CDP": 2.85}
# desenli kucuk sembol (gecekondu onleme artisi ...) NIP'te: 1/25000'de 50 m (olcekle orantili)
KUCUK_SEMBOL_CARPANI = {"UIP": 1.0, "NIP": 0.533, "CDP": 0.533}

_kurallar = {}      # (dosya, baslik) -> [cizgi tanimi]
_glif = {}          # (font, kod) -> (genislik_em, yukseklik_em, merkez_x_em, merkez_y_em)


def _yerel(tag):
    return tag.rsplit("}", 1)[-1]


def _css(node):
    d = {}
    for c in node:
        if _yerel(c.tag) in ("CssParameter", "SvgParameter"):
            v = "".join(c.itertext()).strip()
            if v:
                d[c.get("name")] = v
    return d


def _sayi(v, vars=None):
    try:
        return float(str(v).strip().replace(",", "."))
    except (TypeError, ValueError):
        return vars


def _cocuk(node, ad):
    for c in node:
        if _yerel(c.tag) == ad:
            return c
    return None


def _ara(node, ad):
    for c in node.iter():
        if _yerel(c.tag) == ad:
            return c
    return None


def kural_cizgileri(kaynak, baslik):
    """SLD dosyasi + kural basligi -> LineSymbolizer tanimlari listesi."""
    anahtar = (kaynak, baslik)
    if anahtar in _kurallar:
        return _kurallar[anahtar]
    sonuc = []
    yol = os.path.join(STIL_DIR, (kaynak or "") + ".sld")
    if os.path.exists(yol):
        try:
            kok = ET.parse(yol).getroot()  # nosec B314 - yalniz eklentiyle gelen e-Plan SLD dosyasi
        except ET.ParseError:
            kok = None
        kurallar = [r for r in (kok.iter() if kok is not None else []) if _yerel(r.tag) == "Rule"]
        sec = [r for r in kurallar if (_cocuk(r, "Title") is not None and
                                      (_cocuk(r, "Title").text or "").strip() == baslik)]
        if not sec and len(kurallar) == 1:
            sec = kurallar
        for r in sec[:1]:
            for ls in r.iter():
                if _yerel(ls.tag) != "LineSymbolizer":
                    continue
                st = _cocuk(ls, "Stroke")
                if st is None:
                    continue
                css = _css(st)
                tanim = {
                    "renk": css.get("stroke", "#000000"),
                    "saydam": _sayi(css.get("stroke-opacity"), 1.0),
                    "kalinlik": _sayi(css.get("stroke-width"), 0.26),
                    "desen": [x for x in (_sayi(t) for t in re.split(r"[\s,]+", css.get("stroke-dasharray", "")))
                              if x is not None],
                    "desen_kayma": _sayi(css.get("stroke-dashoffset"), 0.0),
                    "ofset": _sayi("".join(_cocuk(ls, "PerpendicularOffset").itertext())
                                   if _cocuk(ls, "PerpendicularOffset") is not None else None, 0.0),
                    "glif": None,
                }
                gs = _cocuk(st, "GraphicStroke")
                if gs is not None:
                    wk = _ara(gs, "WellKnownName")
                    sz = _ara(gs, "Size")
                    mark = _ara(gs, "Mark")
                    m = re.match(r"ttf://([^#]+)#0x([0-9A-Fa-f]+)", (wk.text or "").strip() if wk is not None else "")
                    dolgu = _cocuk(mark, "Fill") if mark is not None else None
                    renk = _css(dolgu).get("fill", tanim["renk"]) if dolgu is not None else tanim["renk"]
                    ms_ = _cocuk(mark, "Stroke") if mark is not None else None
                    kalem = _sayi(_css(ms_).get("stroke-width"), None) if ms_ is not None else None
                    if m:
                        tanim["glif"] = {"font": m.group(1), "kod": int(m.group(2), 16),
                                         "boy": _sayi(sz.text if sz is not None else None, 10.0),
                                         "renk": renk, "kalem": kalem}
                    elif wk is not None:
                        tanim["glif"] = {"sekil": (wk.text or "").strip(),
                                         "boy": _sayi(sz.text if sz is not None else None, 2.0),
                                         "renk": renk}
                sonuc.append(tanim)
    _kurallar[anahtar] = sonuc
    return sonuc


def _glif_olcu(font, kod):
    """Glif olculeri (em): genislik, yukseklik, kutu merkezi x/y (taban cizgisine gore,
    asagi +), ilerleme, ascent."""
    a = (font, kod)
    if a in _glif:
        return _glif[a]
    from qgis.PyQt.QtGui import QFont, QPainterPath, QFontMetricsF
    from qgis.PyQt.QtCore import QPointF
    f = QFont(font)
    f.setPixelSize(100)
    p = QPainterPath()
    p.addText(QPointF(0, 0), f, chr(kod))
    b = p.boundingRect()
    fm = QFontMetricsF(f)
    adv = fm.horizontalAdvance(chr(kod))
    if b.width() <= 0 or b.height() <= 0:
        r = (1.0, 1.0, 0.5, -0.5, 1.0, fm.ascent() / 100.0)
    else:
        r = (b.width() / 100.0, b.height() / 100.0, b.center().x() / 100.0, b.center().y() / 100.0,
             adv / 100.0, fm.ascent() / 100.0)
    _glif[a] = r
    return r


_kosu = {}


def glif_kosulari(font, kod):
    """Uzun desen glifini (cizgi+nokta) yatay murekkep kosularina ayirir.
    Donus: [(bas, son, yukseklik)] glif genisligine oranla (0..1), ya da None (sembol iceriyor)."""
    a = (font, kod)
    if a in _kosu:
        return _kosu[a]
    from qgis.PyQt.QtGui import QFont, QPainterPath, QImage, QPainter, QColor, QTransform
    from qgis.PyQt.QtCore import QPointF, Qt
    f = QFont(font)
    f.setPixelSize(200)
    p = QPainterPath()
    p.addText(QPointF(0, 0), f, chr(kod))
    b = p.boundingRect()
    sonuc = None
    if b.width() > 0 and b.height() > 0:
        W = 1600
        H = max(8, int(W * b.height() / b.width()))
        img = QImage(W, H, QImage.Format.Format_ARGB32)
        img.fill(0)
        g = QPainter(img)
        g.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        g.scale(W / b.width(), H / b.height())
        g.translate(-b.left(), -b.top())
        g.fillPath(p, QColor(0, 0, 0))
        g.end()
        sut = []
        for x in range(W):
            ys = [y for y in range(H) if (img.pixel(x, y) >> 24) & 255 > 128]
            sut.append((min(ys), max(ys)) if ys else None)
        kos, i = [], 0
        while i < W:
            if sut[i] is None:
                i += 1
                continue
            j, y0, y1 = i, sut[i][0], sut[i][1]
            while j < W and sut[j] is not None:
                y0, y1 = min(y0, sut[j][0]), max(y1, sut[j][1])
                j += 1
            kos.append((i / float(W), j / float(W), (y1 - y0 + 1) / float(H)))
            i = j
        if kos:
            hs = [k[2] for k in kos]
            # yalniz cizgi ve noktalardan olusuyorsa (sembol yok) cevrilebilir
            if max(hs) <= 2.2 * min(hs) and len(kos) <= 8:
                sonuc = kos
    _kosu[a] = sonuc
    return sonuc


def _desen_cizgisi(kos, uzunluk, periyot, renk, kalem_mm, ofset, fak=1.0):
    """Glif kosularindan ince kesik/noktali cizgi (Netcad kalemi gibi)."""
    from qgis.core import QgsSimpleLineSymbolLayer, QgsUnitTypes
    from qgis.PyQt.QtCore import Qt
    harita = Qgis.RenderUnit.MetersInMapUnits
    desen = []
    for n, (b0, b1, _h) in enumerate(kos):
        boy = (b1 - b0) * uzunluk
        nokta = boy <= max(kalem_mm * fak * 2.5, uzunluk * 0.06)
        desen.append(0.0001 if nokta else boy)
        sonraki = kos[n + 1][0] * uzunluk if n + 1 < len(kos) else periyot + kos[0][0] * uzunluk
        bosluk = sonraki - b1 * uzunluk
        if nokta:
            bosluk += boy           # nokta yerine yuvarlak uc: araligi koru
        desen.append(max(bosluk, 0.0001))
    sl = QgsSimpleLineSymbolLayer(_qc(renk))
    # Netcad gibi: kalem kalinligi SABIT (ekran/pafta mm), desen boylari harita olcekli
    sl.setWidth(max(kalem_mm, 0.1))
    sl.setWidthUnit(Qgis.RenderUnit.Millimeters)
    sl.setPenCapStyle(Qt.PenCapStyle.RoundCap)
    sl.setPenJoinStyle(Qt.PenJoinStyle.RoundJoin)
    sl.setUseCustomDashPattern(True)
    sl.setCustomDashVector(desen)
    sl.setCustomDashPatternUnit(harita)
    if ofset:
        sl.setOffset(ofset)
        sl.setOffsetUnit(harita)
    return sl


def font_isareti(font, kod, boy_m, renk, birim=None):
    """e-Plan glifi: en buyuk boyutu boy_m (harita metresi), sinir kutusu ortasi noktada.
    Donus: (QgsFontMarkerSymbolLayer, glifin yatay boyu m)."""
    from qgis.core import QgsFontMarkerSymbolLayer, QgsUnitTypes
    from qgis.PyQt.QtCore import QPointF
    birim = birim if birim is not None else Qgis.RenderUnit.MetersInMapUnits
    w, h, cx, cy, adv, asc = _glif_olcu(font, kod)
    em = boy_m / max(w, h, 1e-6)
    fm = QgsFontMarkerSymbolLayer(font, chr(kod), em)
    fm.setColor(_qc(renk))
    try:
        fm.setStrokeWidth(0)
        fm.setStrokeColor(_qc(renk, 0))
    except Exception:  # nosec B110 - istege bagli QGIS ayari
        pass
    fm.setSizeUnit(birim)
    try:
        fm.setStrokeWidthUnit(birim)
    except Exception:  # noqa  # nosec B110 - istege bagli QGIS ayari
        pass
    # QGIS harfi ilerlemenin ortasina, taban cizgisi noktanin ascent/2 altinda olacak sekilde
    # cizer. Kutu merkezini noktaya getirmek icin kaydir:
    dx = -(cx - adv / 2.0) * em
    dy = -(asc / 2.0 + cy) * em
    fm.setOffset(QPointF(dx, dy))
    fm.setOffsetUnit(birim)
    return fm, w * em


def _qc(hexrenk, saydam=1.0):
    from qgis.PyQt.QtGui import QColor
    c = QColor(hexrenk or "#000000")
    c.setAlphaF(max(0.0, min(1.0, saydam if saydam is not None else 1.0)))
    return c


# e-Plan'da karsiligi olmayan cizgi tipleri icin kendi tanimimiz (pafta mm; x olcek/1000 m)
# ad: (daire capi, ikili daire merkez araligi, periyot)
OZEL_CIZGILER = {
    "IKILI_DAIRE": (4.9, 6.8, 22.7),     # Endustriyel gelisme bolgesi siniri
}


def _ozel_cizgi(ad, fak):
    from qgis.core import (QgsMarkerLineSymbolLayer, QgsMarkerSymbol, QgsSimpleMarkerSymbolLayer,
                           QgsUnitTypes, Qgis)
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QColor
    tanim = OZEL_CIZGILER.get(ad)
    if not tanim:
        return []
    cap, ara, per = (v * fak for v in tanim)
    harita = Qgis.RenderUnit.MetersInMapUnits
    sekil = Qgis.MarkerShape.Circle
    ms = QgsMarkerSymbol()
    ms.deleteSymbolLayer(0)
    for dx in (-ara / 2.0, ara / 2.0):
        d = QgsSimpleMarkerSymbolLayer(sekil, cap)
        d.setSizeUnit(harita)
        d.setColor(QColor(0, 0, 0))
        d.setStrokeColor(QColor(0, 0, 0))
        d.setOffset(QPointF(dx, 0.0))
        d.setOffsetUnit(harita)
        ms.appendSymbolLayer(d)
    ml = QgsMarkerLineSymbolLayer()
    ml.setPlacements(Qgis.MarkerLinePlacement.Interval)
    ml.setInterval(per)
    ml.setIntervalUnit(harita)
    ml.setOffsetAlongLine(per / 2.0)
    ml.setOffsetAlongLineUnit(harita)
    ml.setRotateSymbols(True)
    ml.setSubSymbol(ms)
    return [ml]


def cizgi_katmanlari(kaynak, baslik, olcek):
    """QGIS cizgi sembol katmanlari listesi (bos olabilir)."""
    if kaynak == "*":
        return _ozel_cizgi(baslik, max(olcek or 1000, 1) / 1000.0)
    from qgis.core import (QgsSimpleLineSymbolLayer, QgsMarkerLineSymbolLayer, QgsMarkerSymbol,
                           QgsFontMarkerSymbolLayer, QgsUnitTypes, Qgis)
    from qgis.PyQt.QtCore import Qt, QPointF
    fak = max(olcek or 1000, 1) / 1000.0
    kc = KADEME_CARPANI.get((kaynak or "").split("_")[0], 1.0)
    ks = KUCUK_SEMBOL_CARPANI.get((kaynak or "").split("_")[0], 1.0)
    harita = Qgis.RenderUnit.MetersInMapUnits
    out = []
    for t in kural_cizgileri(kaynak, baslik):
        g = t["glif"]
        if g and "font" in g:
            w, h, _cx, _cy, _adv, _asc = _glif_olcu(g["font"], g["kod"])
            uzun = w >= h * UZUN_GLIF_ORANI
            desen = [abs(x) for x in t["desen"]]
            S = max(g["boy"] or 1.0, 0.1)
            if len(desen) >= 2 and uzun:
                # desen parcasi: glif cizgi parcasini doldurur, periyot = desen.
                # Cizgi+nokta glifi harf olarak basilirsa kalinligi boyuyla buyur; Netcad gibi
                # ince kalemle cizmek icin glif kesik/noktali cizgiye cevrilir.
                boy_m = max(desen[0], 0.1) * fak
                aralik = sum(desen) * fak
                kos = glif_kosulari(g["font"], g["kod"])
                if kos:
                    kalem = (g.get("kalem") or KALEM_VARSAYILAN)
                    out.append(_desen_cizgisi(kos, boy_m, aralik, g["renk"], kalem,
                                              -t["ofset"] * fak if t["ofset"] else 0, fak))
                    continue
            elif len(desen) >= 2:
                # desenli kucuk sembol (gecekondu onleme artisi, plan onama halkasi):
                # NIP'te 1/25000 icin 50 m (Size 15 x 0.25 x 25 x 0.533); periyot ayni oranda
                boy_m = S * SEMBOL_GLIF * fak * ks
                aralik = sum(desen) * SEMBOL_PERIYOT * fak * ks
            else:
                boy_m = S * DESENSIZ_GLIF * fak * kc
                aralik = None
            fm, uzunluk = font_isareti(g["font"], g["kod"], boy_m, g["renk"], harita)
            if aralik is None:
                aralik = uzunluk
            kayma = uzunluk / 2.0
            ms = QgsMarkerSymbol()
            ms.deleteSymbolLayer(0)
            ms.appendSymbolLayer(fm)
            try:
                ms.setSizeUnit(harita)          # alt sembol de olcekli metre (mm degil)
            except Exception:  # noqa  # nosec B110 - istege bagli QGIS ayari
                pass
            ml = QgsMarkerLineSymbolLayer()
            ml.setPlacements(Qgis.MarkerLinePlacement.Interval)
            ml.setInterval(max(aralik, 0.05))
            ml.setIntervalUnit(harita)
            ml.setOffsetAlongLine(kayma + (t["desen_kayma"] or 0) * fak)
            ml.setOffsetAlongLineUnit(harita)
            ml.setRotateSymbols(True)
            if t["ofset"]:
                ml.setOffset(-t["ofset"] * fak)
                ml.setOffsetUnit(harita)
            ml.setSubSymbol(ms)
            out.append(ml)
            continue
        if t["saydam"] is not None and t["saydam"] <= 0 and not g:
            continue
        sl = QgsSimpleLineSymbolLayer(_qc(t["renk"], t["saydam"]))
        sl.setWidth(min(max(t["kalinlik"] or 0.1, 0.1), 1.2))     # kalem: sabit mm (Netcad gibi)
        sl.setWidthUnit(Qgis.RenderUnit.Millimeters)
        sl.setPenJoinStyle(Qt.PenJoinStyle.RoundJoin)
        if len(t["desen"]) >= 2:
            sl.setUseCustomDashPattern(True)
            pat = [max(abs(x), 0.001) * fak for x in t["desen"]]
            if len(pat) % 2:
                pat.append(pat[-1])
            sl.setCustomDashVector(pat)
            sl.setCustomDashPatternUnit(harita)
            sl.setPenCapStyle(Qt.PenCapStyle.FlatCap)
        if t["ofset"]:
            sl.setOffset(-t["ofset"] * fak)
            sl.setOffsetUnit(harita)
        out.append(sl)
    return out


def cizgi_sembolu(kaynak, baslik, olcek):
    """Tam QgsLineSymbol ya da None (kuralda cizgi tanimi yoksa)."""
    from qgis.core import QgsLineSymbol
    kat = cizgi_katmanlari(kaynak, baslik, olcek)
    if not kat:
        return None
    sym = QgsLineSymbol()
    sym.deleteSymbolLayer(0)
    for k in kat:
        sym.appendSymbolLayer(k)
    return sym


def alan_sembolunu_duzelt(lyr, spec, olcek, merkez_glif=True, ek_kural=None):
    """e-Plan alan sembolunde (1) merkez glifini dunya olcekli ve ortali yapar,
    (2) kuralin LineSymbolizer sinirlarini (sit, onlemli alan...) ekler."""
    from qgis.core import QgsCentroidFillSymbolLayer, QgsFontMarkerSymbolLayer, QgsRenderContext
    fak = max(olcek or 1000, 1) / 1000.0
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
            if isinstance(sl, QgsCentroidFillSymbolLayer) and not merkez_glif:
                continue
            if isinstance(sl, QgsCentroidFillSymbolLayer) and sl.subSymbol() is not None:
                sub = sl.subSymbol()
                for j in range(sub.symbolLayerCount()):
                    f = sub.symbolLayer(j)
                    if isinstance(f, QgsFontMarkerSymbolLayer) and f.character():
                        kod = ord(f.character()[0])
                        w, h, _a, _b, _c, _d = _glif_olcu(f.fontFamily(), kod)
                        # yukseklik = Size x ALAN_GLIF_YUKSEKLIK (pafta mm) -> en buyuk boyuta cevir
                        boy = max(spec.size or 15.0, 0.1) * ALAN_GLIF_YUKSEKLIK * fak * max(w, h) / max(h, 1e-6)
                        yeni, _u = font_isareti(f.fontFamily(), kod, boy, f.color().name())
                        sub.changeSymbolLayer(j, yeni)
        if not merkez_glif:
            for i in reversed(range(sym.symbolLayerCount())):
                if isinstance(sym.symbolLayer(i), QgsCentroidFillSymbolLayer):
                    sym.deleteSymbolLayer(i)
        kat = cizgi_katmanlari(spec.source, spec.title, olcek)
        if not kat and ek_kural:
            # kuralda sinir yok: Netcad'in cizdigi katman cizgi tipi (END_GEL_14 ...)
            kat = cizgi_katmanlari(ek_kural[0], ek_kural[1], olcek)
        for k in kat:
            sym.appendSymbolLayer(k)
    lyr.triggerRepaint()


def sembol_nesnesi(spec, sc):
    """PL katmanindaki sembol nesnesi icin katmanin e-Plan glifi (yukseklik = SC x SEMBOL_BIRIM_M)."""
    if spec is None or not spec.font_family or not spec.font_char:
        return None
    from qgis.core import QgsMarkerSymbol
    kod = ord(spec.font_char[0])
    w, h, _a, _b, _c, _d = _glif_olcu(spec.font_family, kod)
    boy = max(sc or 1.0, 0.05) * SEMBOL_BIRIM_M * max(w, h) / max(h, 1e-6)
    fm, _u = font_isareti(spec.font_family, kod, boy, spec.marker_color or "#000000")
    m = QgsMarkerSymbol()
    m.deleteSymbolLayer(0)
    m.appendSymbolLayer(fm)
    return m
