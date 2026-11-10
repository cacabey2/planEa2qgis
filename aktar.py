# -*- coding: utf-8 -*-
"""NCZ -> GPKG -> QGIS katmanlari (QGIS arayuzunden bagimsiz cekirdek).

GEOMETRI KURALLARI (Netcad ile ayni):
  * Alan = yalniz Kapali + Dolu bayrakli PLine, katman stili dolgu tanimliyorsa.
    Acik PLine (cephe cizgisi) ve dolgusuz kapali PLine CIZGI olarak kalir; hicbir
    zaman zorla kapatilip poligona cevrilmez (eski eklentinin tarim hatasi buydu).
  * IC ALAN: bir alanin tamamen icinde kalan baska bir dolgulu alan, distaki alandan
    BOSLUK olarak cikarilir. Boylece dis alanin taramasi ic alanin uzerine binmez;
    dosyada ic alanin once/sonra cizilmis olmasi da onemsizlesir.
"""
import math
import os
import re

from qgis.core import Qgis  # Qt6/QGIS 4: Qgis.RenderUnit

from . import akilli, eslesme, stil
from .ncz_okuyucu import (NczDosyasi, PLINE, CIZGI, DAIRE, YAY, YAZI, SEMBOL, NOKTA,
                          ISARET, OZEL, ESYUK, DIKD, PAFTA, UCGEN, SPIRAL, palet_rgb, TUR_ADI)

LOG = "planEa2qgis"

# QGIS etiket ceyregi (QgsPalLayerSettings.QuadrantPosition) <- Netcad yazi hizasi
HIZA_CEYREK = {49: 5, 50: 8, 51: 7, 52: 6, 53: 3, 67: 1, 76: 2, 77: 4, 82: 0}

# yol genisligi dairesinin capi = nesne sembol olcegi (SCCU) x bu deger (metre).
# Olculdu: N39D4'te sembol cercevesi 14,0-14,2 x SCCU (220 nesne). Biraz buyuk tutulur ki
# beyaz zemin dosyadaki cerceve cizgilerini Netcad'deki gibi ortsun.
YOL_DAIRE_M = 14.3

# yapilasma etiketinin yazi boyu = nesne sembol olcegi (SCCU) x bu deger (metre).
# Olculdu: Netcad'in yazdigi yapilasma yazilari 4,5 m / SCCU 0,70 ve 1,76 m / SCCU 0,27 -> 6,4
YAPILASMA_YAZI_M = 6.4

# kucuk alanin bu orani distakinin icindeyse ic alan sayilir
IC_ALAN_ORANI = 0.5

AKILLI_ALANLAR = ("genislik", "yolTuru", "emsal", "yEncok", "taks", "kaks", "hmax",
                  "katAdedi", "yapiNizami")


def log(msg, seviye=0):
    try:
        from qgis.core import QgsMessageLog, Qgis
        QgsMessageLog.logMessage(str(msg), LOG, [Qgis.MessageLevel.Info, Qgis.MessageLevel.Warning, Qgis.MessageLevel.Critical][seviye])
    except Exception:
        pass


class Secenekler(object):
    def __init__(self):
        self.ic_alan_bosalt = True
        self.stil_onceligi = "eplan"     # "eplan" | "dosya"
        self.kademe = None               # None = otomatik, "UIP" | "NIP" | "CDP"
        self.olcek = 0                   # 0 = otomatik
        self.kapali_katmanlar_gizli = True


# --------------------------------------------------------------------------- yardimci
def cizim_olcegi(dosya, yol):
    """1/N payda: dosya adi, PINDEX_N katmani, '1/N' yazisi; yoksa 1000."""
    adaylar = []
    m = re.search(r"(?<!\d)(500|1000|2000|5000|10000|25000|50000|100000)(?!\d)", os.path.basename(yol))
    if m:
        adaylar.append(int(m.group(1)))
    for k in dosya.katmanlar:
        m = re.match(r"PINDEX_(\d{3,6})$", k.ad or "")
        if m:
            adaylar.append(int(m.group(1)))
    for n in dosya.nesneler:
        if n.tur == YAZI and n.metin:
            m = re.match(r"\s*1\s*/\s*(\d{3,6})\s*$", n.metin)
            if m:
                adaylar.append(int(m.group(1)))
    return adaylar[0] if adaylar else 1000


def crs_tanimi(dosya):
    from qgis.core import QgsCoordinateReferenceSystem
    e = dosya.epsg()
    if e:
        return QgsCoordinateReferenceSystem("EPSG:%d" % e)
    p = dosya.proj
    if p.get("dom"):
        elips = "+ellps=GRS80" if abs(p.get("a", 6378137.0) - 6378137.0) < 1 else "+ellps=intl"
        return QgsCoordinateReferenceSystem.fromProj(
            "+proj=tmerc +lat_0=0 +lon_0=%g +k=%g +x_0=%g +y_0=0 %s +units=m +no_defs" %
            (p["dom"], p.get("k0", 1.0), p.get("fe", 500000.0), elips))
    return QgsCoordinateReferenceSystem()


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb)


# --------------------------------------------------------------------------- toplama
class Toplanan(object):
    def __init__(self):
        self.alan = []      # (sira, katman_no, [halka], ad)
        self.cizgi = []     # (sira, katman_no, [nokta], kapali, ad, renk_hex, lt_ad)
        self.nokta = []     # (sira, katman_no, x, y, tur, ad, sembol_no, aci_derece, ozellikler)
        self.yazi = []      # (sira, katman_no, x, y, metin, boy, aci_derece, ceyrek, renk_hex)


def _kutu_ortasi(n):
    """Akilli nesnenin cizim kutusu ortasi; kutu gecersiz/uzaksa (None, None)."""
    b = getattr(n, "sinir", None)
    if not b:
        return None, None
    w, h = b[2] - b[0], b[3] - b[1]
    if not (0 < w < 1000 and 0 < h < 1000):
        return None, None
    cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
    if abs(cx - n.x) > w + 50 or abs(cy - n.y) > h + 50:
        return None, None
    return cx, cy


def topla(dosya, stiller):
    t = Toplanan()
    for sira, n in enumerate(dosya.nesneler):
        k = n.katman
        st = stiller.get(k)
        renk = _hex(stil.gorunur(palet_rgb(n.renk))) if n.renk else ""
        lt_ad = ""
        if n.lt:
            ad, _d = stil.cizgi_tipi(dosya, n.lt)
            lt_ad = ad or ""
        T = n.tur
        if T == PLINE:
            pts = n.koseler or []
            if len(pts) < 2:
                continue
            if n.kapali and n.dolu and len(pts) >= 3 and st is not None and st.dolgu:
                t.alan.append((sira, k, pts, n.ad or ""))
            else:
                t.cizgi.append((sira, k, pts, int(n.kapali), n.ad or "", renk, lt_ad))
        elif T in (CIZGI, DAIRE, YAY, ESYUK, DIKD, PAFTA, UCGEN, SPIRAL):
            if n.koseler and len(n.koseler) >= 2:
                t.cizgi.append((sira, k, n.koseler, int(T in (DAIRE, DIKD, PAFTA, UCGEN)),
                                n.ad or "", renk, lt_ad))
        elif T == YAZI:
            if n.metin and n.metin.strip():
                t.yazi.append((sira, k, n.x, n.y, n.metin, n.boy or 0.0,
                               math.degrees(n.aci or 0.0), HIZA_CEYREK.get(n.hiza, 2), renk))
        elif T == SEMBOL:
            t.nokta.append((sira, k, n.x, n.y, "sembol", n.ad or "", n.sembol_no or 0,
                            math.degrees(n.aci or 0.0), None, n.sembol_olcek or 1.0))
        elif T == NOKTA:
            t.nokta.append((sira, k, n.x, n.y, "nokta", n.ad or "", 0, 0.0, None, 1.0))
        elif T in (ISARET, OZEL):
            x, y = n.x, n.y
            # yapilasma yazisi Netcad'de ekleme noktasindan SAGA dogru cizilir; dogru yer
            # Netcad'in dosyaya yazdigi cizim kutusunun (OLimits) ortasidir
            if n.ozellikler and akilli.yol_genisligi(n.ozellikler) is None:
                kx, ky = _kutu_ortasi(n)
                if kx is not None:
                    x, y = kx, ky
            t.nokta.append((sira, k, x, y, "akilli", n.ad or "", 0,
                            math.degrees(n.aci or 0.0), n.ozellikler, n.sembol_olcek or 1.0))
    return t


# --------------------------------------------------------------------------- ic alanlar
def alan_geometrileri(alanlar, bosalt=True, geri=None):
    """[(sira, katman, halka, ad)] -> [(sira, katman, QgsGeometry, ad, ic_sayisi)]"""
    from qgis.core import QgsGeometry, QgsPointXY, QgsSpatialIndex, QgsFeature
    geos = []
    for sira, k, pts, ad in alanlar:
        g = QgsGeometry.fromPolygonXY([[QgsPointXY(x, y) for x, y in pts]])
        if not g.isGeosValid():
            g = g.makeValid()
            if g.type() != 2:   # poligon degil
                g = g.buffer(0, 1)
        if g.isEmpty() or g.area() <= 0:
            continue
        geos.append([sira, k, g, ad, 0])
    if not bosalt or len(geos) < 2:
        return geos

    idx = QgsSpatialIndex()
    for i, r in enumerate(geos):
        f = QgsFeature(i)
        f.setGeometry(r[2])
        idx.addFeature(f)
    asil = [r[2] for r in geos]
    alanlar_m2 = [g.area() for g in asil]
    for i, gi in enumerate(asil):
        if geri and i % 50 == 0:
            geri(i, len(asil))
        bb = gi.boundingBox()
        ici = []
        for j in idx.intersects(bb):
            if j == i:
                continue
            # ic alan = DAHA KUCUK alan. Esit buyuklukte (kopya) iki alanda dosyada
            # SONRA cizilen ustte kalir: alttaki bu kisimdan bosaltilir.
            esit = abs(alanlar_m2[j] - alanlar_m2[i]) <= alanlar_m2[i] * 0.001
            if esit:
                if geos[j][0] < geos[i][0]:
                    continue
            elif alanlar_m2[j] > alanlar_m2[i]:
                continue
            gj = asil[j]
            if not gi.intersects(gj):
                continue
            ortak = gi.intersection(gj)
            # kucuk alanin en az yarisi distakinin icindeyse "ic alan" sayilir
            # (sinirdan biraz tasan ic alanlar da yakalanir; kenar komsulari elenir)
            if ortak and not ortak.isEmpty() and ortak.area() >= alanlar_m2[j] * IC_ALAN_ORANI:
                ici.append(gj)
        if ici:
            birlesik = QgsGeometry.unaryUnion(ici)
            yeni = gi.difference(birlesik)
            if yeni is None or yeni.isEmpty() or yeni.area() <= 0.5:
                geos[i][2] = None          # tamamen ortuldu (kopya alan): cizilmez
            else:
                geos[i][2] = yeni
            geos[i][4] = len(ici)
    geos = [r for r in geos if r[2] is not None]
    return geos


# --------------------------------------------------------------------------- GPKG
def gpkg_yaz(t, dosya, stiller, crs, hedef, bosalt=True, geri=None):
    from qgis.core import (QgsVectorLayer, QgsFeature, QgsField, QgsGeometry, QgsPointXY,
                           QgsVectorFileWriter, QgsProject, QgsWkbTypes)
    from qgis.PyQt.QtCore import QMetaType

    def katman_adi(i):
        k = dosya.katman(i)
        return k.ad if k else "katman %d" % i

    tablolar = []

    # ---- alan
    geos = alan_geometrileri(t.alan, bosalt, geri)
    alan = _bellek("MultiPolygon", crs, [("sira", QMetaType.Type.Int), ("katman_no", QMetaType.Type.Int),
                                          ("katman", QMetaType.Type.QString), ("lejant", QMetaType.Type.QString),
                                          ("ad", QMetaType.Type.QString), ("ic_alan", QMetaType.Type.Int),
                                          ("alan_m2", QMetaType.Type.Double)]
                   + [(c, QMetaType.Type.Double) for c in akilli.ALAN_SUTUNLARI]
                   + [("yapilasma", QMetaType.Type.QString)])
    # yapilasma akilli nesneleri: alanin icine dusen nesnenin degerleri alana aktarilir
    yap = []
    for r in t.nokta:
        deg, et = akilli.yapilasma(r[8])
        if deg is not None:
            yap.append((QgsPointXY(r[2], r[3]), deg, et))
    yap_esles = _yapilasma_esle(geos, yap)
    fs = []
    for i, (sira, k, g, ad, ic) in enumerate(geos):
        f = QgsFeature(alan.fields())
        g.convertToMultiType()
        f.setGeometry(g)
        st = stiller.get(k)
        deg, et = yap_esles.get(i, ({}, None))
        f.setAttributes([sira, k, katman_adi(k), (st.lejant if st else "") or "", ad, ic, round(g.area(), 2)]
                        + [deg.get(c) if isinstance(deg.get(c), float) else None
                           for c in akilli.ALAN_SUTUNLARI] + [et])
        fs.append(f)
    alan.dataProvider().addFeatures(fs)
    tablolar.append(("alan", alan))

    # ---- cizgi
    cz = _bellek("LineString", crs, [("sira", QMetaType.Type.Int), ("katman_no", QMetaType.Type.Int),
                                      ("katman", QMetaType.Type.QString), ("kapali", QMetaType.Type.Int),
                                      ("ad", QMetaType.Type.QString), ("renk", QMetaType.Type.QString),
                                      ("cizgi_tipi", QMetaType.Type.QString)])
    fs = []
    for sira, k, pts, kapali, ad, renk, lt in t.cizgi:
        f = QgsFeature(cz.fields())
        f.setGeometry(QgsGeometry.fromPolylineXY([QgsPointXY(x, y) for x, y in pts]))
        f.setAttributes([sira, k, katman_adi(k), kapali, ad, renk, lt])
        fs.append(f)
    cz.dataProvider().addFeatures(fs)
    tablolar.append(("cizgi", cz))

    # ---- nokta / akilli
    # ozellik adlari harf duyarsiz tekillestirilir (SQLite 'emsal' ile 'Emsal'i ayni sayar)
    ek, esle = [], {}
    sakli = {"fid", "geom", "sira", "katman_no", "katman", "tur", "ad", "sembol_no", "aci", "olcek",
             "etiket"}
    for r in t.nokta:
        for a in (r[8] or {}):
            if a == "VersionValue" or a in esle:
                continue
            kn = next((e for e in ek if e.lower() == a.lower()), None)
            if kn is None:
                kn = a if a.lower() not in sakli else a + "_oz"
                ek.append(kn)
            esle[a] = kn
    nk = _bellek("Point", crs, [("sira", QMetaType.Type.Int), ("katman_no", QMetaType.Type.Int),
                                 ("katman", QMetaType.Type.QString), ("tur", QMetaType.Type.QString),
                                 ("ad", QMetaType.Type.QString), ("sembol_no", QMetaType.Type.Int),
                                 ("aci", QMetaType.Type.Double), ("olcek", QMetaType.Type.Double),
                                 ("etiket", QMetaType.Type.QString)]
                + [(a, QMetaType.Type.QString) for a in ek])
    fs = []
    _bilinmeyen = {}
    for sira, k, x, y, tur, ad, no, aci, oz, olc in t.nokta:
        f = QgsFeature(nk.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        degerler = {}
        for a, v in (oz or {}).items():
            kn = esle.get(a)
            if kn and v not in (None, "") and kn not in degerler:
                degerler[kn] = v
        _d, etiket = akilli.yapilasma(oz)
        if etiket is None:
            etiket = akilli.yol_genisligi(oz)
        if etiket is None and oz and tur == "akilli" and "genislik" not in oz:
            etiket = akilli.genel_etiket(oz)
            if oz and katman_adi(k) not in _bilinmeyen:
                _bilinmeyen[katman_adi(k)] = sorted(oz)
        f.setAttributes([sira, k, katman_adi(k), tur, ad, no, aci, float(olc), etiket]
                        + [degerler.get(a) for a in ek])
        fs.append(f)
    nk.dataProvider().addFeatures(fs)
    for kat, adlar in _bilinmeyen.items():
        log(u"%s: yapilasma semasi taninmadi, genel etiket kullanildi. Ozellikler: %s"
            % (kat, ", ".join(adlar)), 1)
    tablolar.append(("nokta", nk))

    # ---- yazi
    yz = _bellek("Point", crs, [("sira", QMetaType.Type.Int), ("katman_no", QMetaType.Type.Int),
                                 ("katman", QMetaType.Type.QString), ("metin", QMetaType.Type.QString),
                                 ("boy", QMetaType.Type.Double), ("aci", QMetaType.Type.Double),
                                 ("ceyrek", QMetaType.Type.Int), ("renk", QMetaType.Type.QString)])
    fs = []
    for sira, k, x, y, metin, boy, aci, ceyrek, renk in t.yazi:
        f = QgsFeature(yz.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        f.setAttributes([sira, k, katman_adi(k), metin, float(boy), aci, ceyrek, renk])
        fs.append(f)
    yz.dataProvider().addFeatures(fs)
    tablolar.append(("yazi", yz))

    ctx = QgsProject.instance().transformContext()
    ilk = True
    for ad, ml in tablolar:
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = "GPKG"
        opts.layerName = ad
        opts.fileEncoding = "UTF-8"
        opts.actionOnExistingFile = (QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile if ilk
                                     else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer)
        try:
            res = QgsVectorFileWriter.writeAsVectorFormatV3(ml, hedef, ctx, opts)
        except AttributeError:
            res = QgsVectorFileWriter.writeAsVectorFormatV2(ml, hedef, ctx, opts)
        if res[0] != QgsVectorFileWriter.WriterError.NoError:
            raise RuntimeError(u"GPKG yazılamadı (%s): %s" % (ad, res[1] if len(res) > 1 else res[0]))
        ilk = False
    return {ad: ml.featureCount() for ad, ml in tablolar}, sum(1 for g in geos if g[4])


def _dolu(v):
    """QGIS NULL (QVariant), None ve bos metin -> False."""
    if v is None:
        return False
    try:
        if hasattr(v, "isNull") and v.isNull():
            return False
    except Exception:
        pass
    return str(v).strip() not in ("", "NULL")


def _yapilasma_esle(geos, yap):
    """Her yapilasma noktasini icine dustugu EN KUCUK alana baglar.
    Donus: {alan indeksi: (degerler, etiket)}; bir alanda birden cok nesne varsa ilki."""
    from qgis.core import QgsSpatialIndex, QgsFeature, QgsGeometry
    if not yap or not geos:
        return {}
    idx = QgsSpatialIndex()
    for i, r in enumerate(geos):
        f = QgsFeature(i)
        f.setGeometry(r[2])
        idx.addFeature(f)
    sonuc = {}
    for p, deg, et in yap:
        pg = QgsGeometry.fromPointXY(p)
        aday = [i for i in idx.intersects(pg.boundingBox()) if geos[i][2].contains(pg)]
        if not aday:
            continue
        i = min(aday, key=lambda j: geos[j][2].area())
        sonuc.setdefault(i, (deg, et))
    return sonuc


def _bellek(geom, crs, alanlar):
    from qgis.core import QgsVectorLayer, QgsField
    uri = geom + ("?crs=" + crs.authid() if crs.isValid() and crs.authid() else "")
    ml = QgsVectorLayer(uri, "tmp", "memory")
    if crs.isValid() and not crs.authid():
        ml.setCrs(crs)
    ml.dataProvider().addAttributes([_alan(a, t) for a, t in alanlar])
    ml.updateFields()
    return ml


def _alan(ad, tip):
    """QgsField: QGIS 3.38+/4 QMetaType.Type ister; eski QGIS 3 QVariant tipi."""
    from qgis.core import QgsField
    try:
        return QgsField(ad, tip)
    except TypeError:
        from qgis.PyQt.QtCore import QVariant, QMetaType
        eski = {QMetaType.Type.Int: QVariant.Int, QMetaType.Type.Double: QVariant.Double}
        return QgsField(ad, eski.get(tip, QVariant.String))


# --------------------------------------------------------------------------- ana is
def ice_aktar(yol, cikti_klasoru, secenek=None, grup_kok=None, geri=None):
    """Tek NCZ'yi aktarir. Donus: (eklenen katman sayisi, ozet metni)."""
    from qgis.core import QgsProject, QgsVectorLayer
    secenek = secenek or Secenekler()

    dosya = NczDosyasi.oku(yol)
    olcek = secenek.olcek or cizim_olcegi(dosya, yol)
    kademe = eslesme.kademe_sec(dosya, yol, secenek.kademe)
    stiller = {k.sira: stil.cozumle(dosya, k, kademe, secenek.stil_onceligi) for k in dosya.katmanlar}
    for n in dosya.nesneler:
        if n.tur == SEMBOL and n.katman in stiller:
            stiller[n.katman].sembol_var = True
    # plan kendi sembollerini (PLANSEMBOL) tasiyorsa Netcad alan ortasina glif basmaz:
    # e-Plan merkez glifleri (PARK, BHA ...) tum alanlarda kapatilir, cift sembol olmaz
    if plan_sembolu_var(dosya, stiller):
        for st in stiller.values():
            st.sembol_var = True
    crs = crs_tanimi(dosya)

    t = topla(dosya, stiller)
    base = os.path.splitext(os.path.basename(yol))[0]
    gpkg = os.path.join(cikti_klasoru, base + ".gpkg")
    sayilar, bosaltilan = gpkg_yaz(t, dosya, stiller, crs, gpkg, secenek.ic_alan_bosalt, geri)

    kok = grup_kok or QgsProject.instance().layerTreeRoot()
    grup = kok.insertGroup(0, base)
    eklenen = 0
    onama, tum = [], []           # aktarim sonrasi yakinlastirma kapsami
    # cizim sirasi (ustten alta): yazi > nokta > cizgi > alan
    for tablo in ("yazi", "nokta", "cizgi", "alan"):
        if not sayilar.get(tablo):
            continue
        alt = grup.addGroup({"yazi": u"Yazılar", "nokta": u"Noktalar / semboller",
                             "cizgi": u"Çizgiler", "alan": u"Alanlar"}[tablo])
        uri = u"%s|layername=%s" % (gpkg, tablo)
        prob = QgsVectorLayer(uri, tablo, "ogr")
        if not prob.isValid():
            continue
        li = prob.fields().indexOf("katman_no")
        nolar = sorted(int(v) for v in prob.uniqueValues(li) if v is not None)
        # alanlarda ustteki katman sonra cizilsin: yuksek no ustte
        for kno in sorted(nolar, reverse=True):
            k = dosya.katman(kno)
            st = stiller.get(kno) or stil.KatmanStili()
            ad = k.ad if k else u"katman %d" % kno
            lyr = QgsVectorLayer(uri, ad, "ogr")
            lyr.setSubsetString(u'"katman_no" = %d' % kno)
            if not lyr.isValid() or lyr.featureCount() == 0:
                continue
            if st.lejant:
                lyr.setTitle(st.lejant)
            try:
                _stille(lyr, tablo, st, olcek, secenek, dosya)
            except Exception as e:  # noqa
                import traceback
                log(u"%s stil hatası: %s\n%s" % (ad, e, traceback.format_exc()), 1)
            QgsProject.instance().addMapLayer(lyr, False)
            dugum = alt.addLayer(lyr)
            try:
                kp = lyr.extent()
                if not kp.isEmpty() and tablo != "yazi" and not eslesme.ATLA.match(ad or ""):
                    tum.append(kp)
                    if _onama_katmani(ad, st):
                        onama.append(kp)
            except Exception:  # noqa
                pass
            if st.lejant and tablo == "alan":
                lyr.setName(ad + u" — " + _baslik(st.lejant))
            if secenek.kapali_katmanlar_gizli and k is not None and not k.acik:
                dugum.setItemVisibilityChecked(False)
            eklenen += 1
        alt.setExpanded(tablo == "alan")

    ozet = (u"%s: %d alan (%d alana iç alan boşluğu açıldı), %d çizgi, %d yazı, %d nokta · "
            u"e-Plan %s · ölçek 1/%d" % (base, sayilar.get("alan", 0), bosaltilan,
                                         sayilar.get("cizgi", 0), sayilar.get("yazi", 0),
                                         sayilar.get("nokta", 0), kademe, olcek))
    kaynaklar = {}
    for kno, st in stiller.items():
        if st.dolgu:
            kaynaklar[st.kaynak] = kaynaklar.get(st.kaynak, 0) + 1
    from qgis.core import QgsRectangle

    def _birlesik(liste):
        if not liste:
            return None
        r = QgsRectangle(liste[0])
        for k in liste[1:]:
            r.combineExtentWith(k)
        return r
    r_tum, r_onama = _birlesik(tum), _birlesik(onama)
    # onama siniri lejanttaki ornek cizgi kadar kucukse (N39D4 gibi) tum plana yakinlastir
    if r_onama is not None and r_tum is not None and r_onama.area() < r_tum.area() * 0.01:
        r_onama = None
    secilen = r_onama or r_tum
    if secilen is not None:
        SON_KAPSAMLAR.append((secilen, crs))
    log(ozet + u" · dolgu kaynağı: " + ", ".join("%s=%d" % kv for kv in sorted(kaynaklar.items())))
    return eklenen, ozet


# ice_aktar her dosya icin (QgsRectangle, crs) ekler; arayuz yakinlastirmada kullanir
SON_KAPSAMLAR = []


def _onama_katmani(ad, st):
    """Plan onama siniri katmani mi (SNR_PLANONAMA, PLAN_SINIRI ...)."""
    a = (ad or "").upper()
    if "ONAMA" in a or "PLAN_SINIR" in a or "PLANSINIR" in a:
        return True
    return st is not None and st.spec is not None and \
        (st.spec.source or "").endswith("_PLAN_SINIRI") and a.startswith("SNR_")


def yakinlastir(canvas):
    """Son aktarilan dosyalarin plan onama sinirina (yoksa tum katmanlarina) yakinlastirir."""
    from qgis.core import QgsCoordinateTransform, QgsProject, QgsRectangle
    hedef = canvas.mapSettings().destinationCrs()
    toplam = None
    for r, crs in SON_KAPSAMLAR:
        try:
            if crs is not None and crs.isValid() and hedef.isValid() and crs != hedef:
                r = QgsCoordinateTransform(crs, hedef, QgsProject.instance()).transformBoundingBox(r)
        except Exception:  # noqa
            continue
        if toplam is None:
            toplam = QgsRectangle(r)
        else:
            toplam.combineExtentWith(r)
    del SON_KAPSAMLAR[:]
    if toplam is None or toplam.isEmpty():
        return False
    toplam.scale(1.05)
    canvas.setExtent(toplam)
    canvas.refresh()
    return True


def plan_sembolu_var(dosya, stiller=None):
    sem = set()
    for n in dosya.nesneler:
        if n.tur == SEMBOL:
            sem.add(n.katman)
    for kno in sem:
        k = dosya.katman(kno)
        ad = (k.ad if k else "") or ""
        if "SEMBOL" in ad.upper() and not ad.upper().startswith("PL_"):
            return True
    return False


def eplan_cizgi_var(spec):
    """Alan kurali da olsa SLD'de cizgi tanimi varsa (sit, onlemli alan sinirlari)."""
    from . import eplan_cizgi
    return spec.source != "yol" and bool(eplan_cizgi.kural_cizgileri(spec.source, spec.title))


def _baslik(s):
    """'TARIM VE HAYVANCILIK TESİS ALANI' -> 'Tarım ve Hayvancılık Tesis Alanı' (Turkce kurallariyla)."""
    kucuk_kal = (u"ve", u"ile", u"veya")
    out = []
    for w in s.split():
        lw = w.replace(u"I", u"ı").replace(u"İ", u"i").lower()
        if lw in kucuk_kal and out:
            out.append(lw)
        else:
            ilk = lw[:1].replace(u"i", u"İ").replace(u"ı", u"I").upper()
            out.append(ilk + lw[1:])
    return u" ".join(out)


# --------------------------------------------------------------------------- stil
def _stille(lyr, tablo, st, olcek, secenek, dosya):
    from qgis.core import (QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer,
                           QgsRendererCategory)
    if tablo == "alan":
        if not (st.kaynak == "eplan" and stil.eplan_uygula(lyr, st, "polygon", olcek)):
            lyr.setRenderer(QgsSingleSymbolRenderer(stil.dosya_dolgu_sembolu(st)))
    elif tablo == "cizgi":
        # e-Plan'da cizgi (sinir/hat) karsiligi varsa resmi gosterim
        if st.spec is not None and (st.spec.geom == "line" or eplan_cizgi_var(st.spec)) \
                and stil.eplan_uygula(lyr, st, "line", olcek):
            pass
        elif st.lt_kural and _lt_cizgisi(lyr, st, olcek):
            pass        # katmanin NCZ cizgi tipi (END_GEL_14, ONL_ALN-14 ...) -> e-Plan cizgisi
        else:
            desenler = {}
            for c in dosya.cizgi_tipleri:
                if c and c[0]:
                    desenler[c[0]] = c[1] if len(c) > 1 else None
            anahtarlar = set()
            for f in lyr.getFeatures():
                anahtarlar.add((f["renk"] or "", f["cizgi_tipi"] or ""))
            if anahtarlar <= {("", "")}:
                lyr.setRenderer(QgsSingleSymbolRenderer(
                    stil.dosya_cizgi_sembolu(st.cizgi_rgb, st.desen, st.kalinlik, olcek, st.cizgi_mm)))
            else:
                kat = []
                for renk, lt in sorted(anahtarlar):
                    rgb = tuple(int(renk[i:i + 2], 16) for i in (1, 3, 5)) if renk else st.cizgi_rgb
                    sym = stil.dosya_cizgi_sembolu(rgb, desenler.get(lt) if lt else st.desen,
                                                   st.kalinlik, olcek, st.cizgi_mm)
                    kat.append(QgsRendererCategory(renk + "|" + lt, sym, (renk + " " + lt).strip() or u"katman"))
                lyr.setRenderer(QgsCategorizedSymbolRenderer(
                    "coalesce(\"renk\",'') || '|' || coalesce(\"cizgi_tipi\",'')", kat))
    elif tablo == "nokta":
        try:
            _nokta_stili(lyr, st, olcek)
        except Exception as e:  # noqa
            import traceback
            log(u"%s nokta stili hatası: %s\n%s" % (lyr.name(), e, traceback.format_exc()), 1)
        # etiket, sembol adimindan BAGIMSIZ kurulur (yol genisligi katmani haric)
        if lyr.fields().indexOf("etiket") >= 0 and not lyr.labelsEnabled() \
                and not _yol_katmani(lyr):
            try:
                _etiket_kur(lyr)
            except Exception as e:  # noqa
                import traceback
                log(u"%s etiket hatası: %s\n%s" % (lyr.name(), e, traceback.format_exc()), 2)
    elif tablo == "yazi":
        try:
            _yazi_stili(lyr, st, olcek)
        except Exception as e:  # noqa
            import traceback
            log(u"%s yazı stili hatası: %s\n%s" % (lyr.name(), e, traceback.format_exc()), 2)
    lyr.triggerRepaint()


def _lt_cizgisi(lyr, st, olcek):
    from qgis.core import QgsSingleSymbolRenderer
    from . import eplan_cizgi
    eslesme.fontlari_yukle()
    sym = eplan_cizgi.cizgi_sembolu(st.lt_kural[0], st.lt_kural[1], olcek)
    if sym is None:
        return False
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))
    return True


def _nokta_stili(lyr, st, olcek):
    from qgis.core import (QgsMarkerSymbol, QgsSingleSymbolRenderer, QgsUnitTypes, QgsProperty,
                           QgsSymbolLayer, QgsFontMarkerSymbolLayer, QgsPalLayerSettings,
                           QgsTextFormat, QgsVectorLayerSimpleLabeling)
    from qgis.PyQt.QtGui import QColor
    fak = olcek / 1000.0
    # nokta tablosu ortak: alan adina degil, bu katmanda DOLU olan ozelliklere bak
    adlar = set()
    gi = lyr.fields().indexOf("genislik")
    ei = lyr.fields().indexOf("etiket")
    ti = lyr.fields().indexOf("tur")
    akilli_say = toplam = yol_say = 0
    for f in lyr.getFeatures():
        toplam += 1
        if ti >= 0 and str(f.attribute(ti)) == "akilli":
            akilli_say += 1
        if gi >= 0 and _dolu(f.attribute(gi)):
            yol_say += 1
    # yol genisligi: katmandaki noktalarin cogu genislik tasiyorsa
    if yol_say and yol_say * 2 >= toplam:
        adlar.add("genislik")
    elif ei >= 0:
        adlar.add("etiket")      # etiket her zaman baglanir; bos olanlar cizilmez
    # plan sembolleri (PLANSEMBOL): sembol numarasina gore kendi cizimimiz
    try:
        from . import plansembol
        if plansembol.katman_mi(lyr) and plansembol.uygula(lyr):
            return
    except Exception as e:  # noqa
        log(u"%s plan sembolü: %s" % (lyr.name(), e), 1)
    renk = stil._qc(st.cizgi_rgb)
    if "genislik" in adlar:
        # SM_YOL yol genisligi: Netcad'deki gibi daire + ortasinda genislik sayisi.
        # Boyut cizim olceginden DEGIL, nesnenin kendi sembol olceginden (SCCU):
        # cap = olcek x YOL_DAIRE_M metre.
        cap = 'max(coalesce("olcek", 1), 0.2) * %s' % YOL_DAIRE_M
        m = QgsMarkerSymbol.createSimple({"name": "circle", "color": "255,255,255,255",
                                          "outline_color": "0,0,0", "outline_width": "0.15"})
        sl = m.symbolLayer(0)
        sl.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits)
        sl.setStrokeWidthUnit(Qgis.RenderUnit.Millimeters)
        sl.setDataDefinedProperty(_sembol_ozellik("Size"), QgsProperty.fromExpression(cap))
        fm = QgsFontMarkerSymbolLayer("Arial", "0", 1.0)
        fm.setColor(QColor(0, 0, 0))
        fm.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits)
        fm.setDataDefinedProperty(_sembol_ozellik("Character"),
                                  QgsProperty.fromExpression("coalesce(\"genislik\", '')"))
        fm.setDataDefinedProperty(_sembol_ozellik("Size"),
                                  QgsProperty.fromExpression("(%s) * 0.31" % cap))
        m.appendSymbolLayer(fm)
        lyr.setRenderer(QgsSingleSymbolRenderer(m))
        return
    if "etiket" in adlar:
        # yapilasma: Netcad gibi yalniz "bos degil" isaretli degerler (E=, TAKS=, KAKS=, Hmax=,
        # Yencok=), dosyadaki ondalik hane sayisiyla; metin akilli.py'de hazirlanir
        if akilli_say and akilli_say * 2 >= toplam:
            m = QgsMarkerSymbol.createSimple({"name": "circle", "size": "0.1", "color": "0,0,0,0",
                                              "outline_style": "no"})   # akilli nesne: yalniz yazi
        else:
            m = QgsMarkerSymbol.createSimple({"name": "circle", "color": renk.name(),
                                              "outline_style": "no", "size": "1.2"})
        lyr.setRenderer(QgsSingleSymbolRenderer(m))
        _etiket_kur(lyr)
        return
    # PL katmanindaki sembol nesneleri (BHA kutusu vb.): katmanin e-Plan glifi, nesnenin olcegiyle
    try:
        from . import eplan_cizgi
        si = lyr.fields().indexOf("olcek")
        scs = [float(f.attribute(si)) for f in lyr.getFeatures()
               if str(f["tur"]) == "sembol" and _dolu(f.attribute(si))]
        if scs and st.spec is not None:
            eslesme.fontlari_yukle()
            sc = sorted(scs)[len(scs) // 2]
            ms = eplan_cizgi.sembol_nesnesi(st.spec, sc)
            if ms is not None:
                lyr.setRenderer(QgsSingleSymbolRenderer(ms))
                return
    except Exception as e:  # noqa
        log(u"%s sembol nesnesi: %s" % (lyr.name(), e), 1)
    m = QgsMarkerSymbol.createSimple({"name": "circle", "color": renk.name(),
                                      "outline_style": "no", "size": "1.2"})
    lyr.setRenderer(QgsSingleSymbolRenderer(m))


def _yol_katmani(lyr):
    gi = lyr.fields().indexOf("genislik")
    if gi < 0:
        return False
    n = y = 0
    for f in lyr.getFeatures():
        n += 1
        if _dolu(f.attribute(gi)):
            y += 1
    return bool(y) and y * 2 >= n


def _etiket_kur(lyr):
    """Yapilasma / akilli nesne etiketi: 'etiket' alani, boyu SCCU x YAPILASMA_YAZI_M metre."""
    from qgis.core import (QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling,
                           QgsUnitTypes, QgsProperty)
    from qgis.PyQt.QtGui import QColor
    ps = QgsPalLayerSettings()
    ps.fieldName = "etiket"
    ps.isExpression = False
    _guvenli(lambda: setattr(ps, "placement", _yer_ustu()))
    _guvenli(lambda: setattr(ps, "displayAll", True))
    fmt = QgsTextFormat()
    _guvenli(lambda: fmt.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits))
    fmt.setSize(4.5)
    fmt.setColor(QColor(0, 0, 0))
    ps.setFormat(fmt)

    def boy():
        dd = ps.dataDefinedProperties()
        dd.setProperty(_ozellik("Size"), QgsProperty.fromExpression(
            "max(coalesce(\"olcek\", 0.7), 0.1) * %s" % YAPILASMA_YAZI_M))
        ps.setDataDefinedProperties(dd)
    _guvenli(boy)
    _guvenli(lambda: setattr(ps, "multilineAlign", _cok_satir_orta()))
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(ps))
    lyr.setLabelsEnabled(True)


def _guvenli(fn):
    try:
        fn()
    except Exception as e:  # noqa
        log(u"etiket ayarı atlandı: %s" % e, 1)


def _yer_ustu():
    from qgis.core import QgsPalLayerSettings
    try:
        from qgis.core import Qgis
        return Qgis.LabelPlacement.OverPoint
    except Exception:
        return QgsPalLayerSettings.OverPoint


def _cok_satir_orta():
    try:
        from qgis.core import Qgis
        return Qgis.LabelMultiLineAlignment.Center
    except Exception:
        from qgis.core import QgsPalLayerSettings
        return QgsPalLayerSettings.MultiCenter


def _sembol_ozellik(ad):
    """QgsSymbolLayer veri-tanimli ozellik (eski: PropertySize, yeni: Property.Size)."""
    from qgis.core import QgsSymbolLayer
    if hasattr(QgsSymbolLayer, "Property") and hasattr(QgsSymbolLayer.Property, ad):
        return getattr(QgsSymbolLayer.Property, ad)
    return getattr(QgsSymbolLayer, "Property" + ad)


def _ozellik(ad):
    """QgsPalLayerSettings veri-tanimli ozellik (eski ve yeni QGIS)."""
    from qgis.core import QgsPalLayerSettings
    if hasattr(QgsPalLayerSettings, "Property") and hasattr(QgsPalLayerSettings.Property, ad):
        return getattr(QgsPalLayerSettings.Property, ad)
    return getattr(QgsPalLayerSettings, ad)


def _yazi_stili(lyr, st, olcek):
    """Netcad yazilari: metin, boy (m), aci, hiza (ceyrek), renk. Her ayar ayri korunur;
    QGIS surumunde olmayan bir ayar etiketin tamamini dusurmez."""
    from qgis.core import (QgsMarkerSymbol, QgsSingleSymbolRenderer, QgsUnitTypes, QgsProperty,
                           QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling)
    fak = olcek / 1000.0
    _guvenli(lambda: lyr.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple(
        {"name": "circle", "size": "0.1", "color": "0,0,0,0", "outline_style": "no"}))))
    ps = QgsPalLayerSettings()
    ps.fieldName = "metin"
    ps.isExpression = False
    _guvenli(lambda: setattr(ps, "placement", _yer_ustu()))
    _guvenli(lambda: setattr(ps, "displayAll", True))
    fmt = QgsTextFormat()
    _guvenli(lambda: fmt.setSizeUnit(Qgis.RenderUnit.MetersInMapUnits))
    fmt.setSize(2.5 * fak)
    fmt.setColor(stil._qc(st.cizgi_rgb))
    ps.setFormat(fmt)
    dd = ps.dataDefinedProperties()
    # Netcad yazi boyu (Sct) = harfin dunya yuksekligi (m); 0 ise olcege gore varsayilan
    _guvenli(lambda: dd.setProperty(_ozellik("Size"), QgsProperty.fromExpression(
        "CASE WHEN \"boy\" > 0 THEN \"boy\" ELSE %r END" % round(2.5 * fak, 3))))
    _guvenli(lambda: dd.setProperty(_ozellik("LabelRotation"), QgsProperty.fromExpression("-\"aci\"")))
    _guvenli(lambda: dd.setProperty(_ozellik("OffsetQuad"), QgsProperty.fromField("ceyrek")))
    _guvenli(lambda: dd.setProperty(_ozellik("Color"), QgsProperty.fromExpression(
        "CASE WHEN \"renk\" <> '' THEN \"renk\" END")))
    ps.setDataDefinedProperties(dd)
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(ps))
    lyr.setLabelsEnabled(True)
