# -*- coding: utf-8 -*-
"""Plan sembolleri (PLANSEMBOL katmani): Netcad sembol kutuphanesinin NUMARASI -> kendi cizimimiz.

Netcad'in sembol dosyalari kullanilmaz (yayin kosulu). NCZ yalniz sembol numarasini tasir;
numaranin plandaki anlami Netcad paftasiyla karsilastirilarak bulundu ve burada
kendi sekillerimizle (kutu icinde kod, ucgen, kutu) cizilir. Taninmayan numara: bos kutu
(Netcad'in kucuk olcekte gosterdigi gibi).
"""
from qgis.core import Qgis  # Qt6/QGIS 4: Qgis.RenderUnit

# no -> ("kod", metin) | ("sekil", ad)
SEMBOLLER = {
    10: ("kod", u"T1"),
    12: ("kod", u"T3"),
    13: ("kod", u"TİCK"),
    16: ("kod", u"BHA"),
    34: ("kod", u"İA"),
    27: ("sekil", "ucgen"),
    29: ("sekil", "kare_ic"),
    31: ("sekil", "cift_kare"),
}

BIRIM_M = 8.0          # kutu kenari = nesne olcegi (SC) x BIRIM_M metre
KALEM_MM = 0.25


def _kare(boy, ofset=(0.0, 0.0), dolu=False):
    from qgis.core import QgsSimpleMarkerSymbolLayer, QgsUnitTypes
    from qgis.PyQt.QtCore import QPointF
    from qgis.PyQt.QtGui import QColor
    from qgis.core import Qgis
    sekil = Qgis.MarkerShape.Square
    sl = QgsSimpleMarkerSymbolLayer(sekil, boy)
    sl.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits)
    sl.setColor(QColor(255, 255, 255, 255 if dolu else 0))
    sl.setStrokeColor(QColor(0, 0, 0))
    sl.setStrokeWidth(KALEM_MM)
    sl.setStrokeWidthUnit(Qgis.RenderUnit.Millimeters)
    if ofset != (0.0, 0.0):
        sl.setOffset(QPointF(ofset[0], ofset[1]))
        sl.setOffsetUnit(Qgis.RenderUnit.MetersInMapUnits)
    return sl


def _ucgen(boy):
    from qgis.core import QgsSimpleMarkerSymbolLayer, QgsUnitTypes
    from qgis.PyQt.QtGui import QColor
    from qgis.core import Qgis
    sekil = Qgis.MarkerShape.Triangle
    sl = QgsSimpleMarkerSymbolLayer(sekil, boy)
    sl.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits)
    sl.setColor(QColor(0, 0, 0, 0))
    sl.setStrokeColor(QColor(0, 0, 0))
    sl.setStrokeWidth(KALEM_MM * 1.6)
    sl.setStrokeWidthUnit(Qgis.RenderUnit.Millimeters)
    return sl


def _yazi(metin, boy):
    from qgis.core import QgsFontMarkerSymbolLayer, QgsUnitTypes
    from qgis.PyQt.QtGui import QColor
    oran = 0.5 if len(metin) <= 2 else 0.34
    fm = QgsFontMarkerSymbolLayer("Arial", metin, boy * oran)
    fm.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits)
    fm.setColor(QColor(0, 0, 0))
    return fm


def sembol(no, sc):
    from qgis.core import QgsMarkerSymbol
    boy = max(sc or 1.0, 0.05) * BIRIM_M
    tur = SEMBOLLER.get(no)
    m = QgsMarkerSymbol()
    m.deleteSymbolLayer(0)
    if tur is None:
        m.appendSymbolLayer(_kare(boy * 0.8))
    elif tur[0] == "kod":
        m.appendSymbolLayer(_kare(boy))       # Netcad: kutu ici seffaf
        m.appendSymbolLayer(_yazi(tur[1], boy))
    elif tur[1] == "ucgen":
        m.appendSymbolLayer(_ucgen(boy * 0.75))
    elif tur[1] == "kare_ic":
        m.appendSymbolLayer(_kare(boy * 0.8))
        m.appendSymbolLayer(_kare(boy * 0.45))
    elif tur[1] == "cift_kare":
        m.appendSymbolLayer(_kare(boy * 0.8))
        m.appendSymbolLayer(_kare(boy * 0.32, (-boy * 0.18, 0.0)))
        m.appendSymbolLayer(_kare(boy * 0.32, (boy * 0.18, 0.0)))
    return m


def katman_mi(lyr):
    return "SEMBOL" in (lyr.name() or "").upper() and not (lyr.name() or "").upper().startswith("PL_")


def uygula(lyr):
    """sembol_no'ya gore kategorili gosterim. Uygulandiysa True."""
    from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory
    ni, si, ti = (lyr.fields().indexOf(a) for a in ("sembol_no", "olcek", "tur"))
    if ni < 0:
        return False
    nolar, scs = set(), []
    for f in lyr.getFeatures():
        if ti >= 0 and str(f.attribute(ti)) != "sembol":
            continue
        try:
            nolar.add(int(f.attribute(ni)))
        except (TypeError, ValueError):
            continue
        try:
            scs.append(float(f.attribute(si)))
        except (TypeError, ValueError):
            pass
    if not nolar:
        return False
    sc = sorted(scs)[len(scs) // 2] if scs else 1.0
    kat = []
    for no in sorted(nolar):
        tur = SEMBOLLER.get(no)
        ad = tur[1] if tur and tur[0] == "kod" else (u"sembol %d" % no)
        kat.append(QgsRendererCategory(no, sembol(no, sc), ad))
    r = QgsCategorizedSymbolRenderer("sembol_no", kat)
    try:
        r.setSourceSymbol(sembol(None, sc))
    except Exception:  # nosec B110 - istege bagli QGIS ayari
        pass
    lyr.setRenderer(r)
    return True
