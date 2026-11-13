# -*- coding: utf-8 -*-
"""e-Plan (Mekansal Planlar) stil kutuphanesinden QGIS QML uretici.

Sorun: MXD/MDB'deki eski veri modeli tek katmanda toplu kullanim tutuyor
(ornek: NIP25_KENTSELKULLANIMALANLARI + `lejantdomain` alani), e-Plan stil
kutuphanesi ise yeni modelde her kullanim icin ayri katman/kural tanimliyor
(NIP_KENTSEL_CALISMA.sld icinde BELEDIYE_HIZMET_ALANI kurali gibi).

Bu modul kutuphanedeki SLD kurallarini okur, lejant adlarini normalize ederek
eslestirir ve eski model alanina gore filtreleyen bir QGIS kural tabanli
(RuleRenderer) QML dosyasi uretir.

Tarama dolgular SLD'de `http://localhost/TaramaResim/<guid>.png` olarak
gecer. e-Plan dagitiminda bu gorseller bir `TaramaResim` klasoründe bulunur;
klasor otomatik aranir ve bulunursa desen QGIS'te `RasterFill` olarak birebir
kullanilir (dosyalar .png uzantili olsa da icerik BMP olabilir, imzaya
bakiyoruz). Bulunmazsa sinif adina gore QGIS'in kendi nokta/cizgi dolgusu
sentezlenir ve raporda "tarama_yedek" isaretlenir.

Nokta ve alan merkezi sembolleri e-Plan TTF fontlarina (NIP_10_1, OG_V_1_1,
nazim_imar_00 gibi) dayanir; QML font isaretcisi olarak uretilir, ilgili
fontlarin isletim sisteminde kurulu olmasi gerekir.
"""

import os
import re
import uuid
import xml.etree.ElementTree as ET  # nosec B405 - yalniz eklentiyle gelen SLD

TR_MAP = str.maketrans('İIıŞşĞğÜüÖöÇçÂâÎî', 'IIiSsGgUuOoCcAaIi')

# Eslestirmede yok sayilabilen sonekler (ayni sinif farkli yazilmis olabiliyor)
DROP_SUFFIX = ('_ALANLARI', '_ALANI', '_ALAN', '_BOLGESI', '_BOLGE',
               '_SINIRLARI', '_SINIRI', '_TESISLERI', '_TESISI', '_TESIS')

# Yogunluk / derece gibi nitelik ekleri
QUALIFIERS = ('COK_YUKSEK', 'YUKSEK', 'ORTA', 'DUSUK', 'SEYREK',
              '1_DERECE', '2_DERECE', '3_DERECE', '4_DERECE', '5_DERECE',
              'BIRINCI_DERECE', 'IKINCI_DERECE', 'UCUNCU_DERECE')

SLD_NS = {'sld': 'http://www.opengis.net/sld', 'ogc': 'http://www.opengis.net/ogc',
          'se': 'http://www.opengis.net/se', 'xlink': 'http://www.w3.org/1999/xlink'}

# Eski model katman adi -> e-Plan sinif adi. Otomatik eslestirmenin
# yakalayamadigi, isim degisikligi olan siniflar icin. Duzenlenebilir:
# kendi paftalarinizda eksik kalan katmanlari buraya ekleyin.
SYNONYMS = {
    'ASKERIYASAKGUVENLIK': 'ASKERI_YASAK_BOLGE',
    'PLANONAMASINIRI': 'PLAN_SINIRI',
    'PLANLAMASINIRLARI': 'PLAN_SINIRI',
    'PLANLAMASINIRLARINOKTA': 'PLAN_SINIRI',
    'KORUMAVESIT': 'SIT_ALANLARI',
    'KORUMAVESITNOKTA': 'SIT_ALANLARI',
    'DOGALMANIAALANI': 'MANIA_PLANI',
    'DEREYATAGI': 'SU_YUZEYI',
    'JEOTEKNIKETUDALANI': 'ONLEMLI_ALAN',
    'KARAYOLLARIKORUMA': 'KARAYOLU_TESISLERI',
    'IMARHAKAKTARIMALANI': 'IMAR_HAK_AKTARIM_SINIR',
    'EKOLOJIKNITELIGIKORUNACAK': 'OZEL_EKOSISTEM',
    'DOGAKORUMA': 'DOGAL_KARAKTER',
    'SULAKALANKORUMA': 'SULAK_ALAN',
    'MERAOTLAKALANLARI': 'MERA',
    # Ozel kanunla belirlenen alanlar (2985, 5366, 6306 ...) tek sinifta
    'OZELKANUNALANSINIRLARI': 'STATU_OZEL_KANUN_ALAN',
    'OZELKANUNALANLARINOKTA': 'STATU_OZEL_KANUN_ALAN',
    'TOPLUKONUTALANI': 'STATU_OZEL_KANUN_ALAN',
    'REZERVYAPIALANISINIRI': 'STATU_OZEL_KANUN_ALAN',
    'YENILEMEALANISINIRI': 'STATU_OZEL_KANUN_ALAN',
    'RISKLIALANSINIRI': 'STATU_OZEL_KANUN_ALAN',
    # Mudahale bicimleri
    'SAGLIKLASTIRMAALANI': 'MUDAHALE_SINIRI',
    'YENIDENDUZENLENECEKALAN': 'MUDAHALE_SINIRI',
    'MEVCUTPLANKORUNACAK': 'MUDAHALE_SINIRI',
    # Digerleri
    'KULTURTURIZMALTBOLGESI': 'TM_KTKGB_ALAN',
    'KAVSAK': 'DIGER_YOL_NESNELERI',
    'YONETIMSINIRLARI': 'DIGER_OZEL_SINIR',
    'YAPIYASAGIGETIRILENALAN': 'DIGER_OZEL_SINIR',
    'YAPIYASAGIALANLARINOKTA': 'DIGER_OZEL_SINIR',
    'MAHALLESINIRI': 'MAHALLE_SINIRI',
    'UIPMAHALLESINIRI': 'MAHALLE_SINIRI',
}


# Tarama gorselleri (TaramaResim/*.png) kutuphanede olmadigi icin desenleri
# QGIS'in kendi dolgulariyla uretiyoruz. Anahtar: sinif adinda aranan parca,
# deger: (desen, varsayilan zemin rengi).
#   nokta   -> PointPatternFill (tarim, mera, doga)
#   tarama  -> tek yon 45 derece cizgi dolgu (sanayi, depolama, altyapi)
#   capraz  -> 45 + 135 derece cift cizgi dolgu (askeri, OSB, tehlikeli)
#   yogun   -> siki araliklı tarama (kati atik, maden)
#   duz     -> desensiz duz zemin (konut, ticaret, sosyal donati)
# Not: duz zemin renkleri N39D4.mxd icinden cozulen gercek plan renkleridir
# (ESRI renkleri CIELAB olarak saklanir, donusturulup alinmistir). Kendi plan
# renk kabulunuz farkliysa bu tabloyu duzenleyin.
PATTERN_RULES = (
    ('MEVCUT_KONUT', 'duz', '#FFF061'),
    ('GELISME_KONUT', 'duz', '#FFFEDB'),
    ('DONUSUM_KONUT', 'duz', '#FFDB95'),
    ('KONUT_ALAN', 'duz', '#FFF061'),
    ('MERKEZI_IS', 'duz', '#ED262D'),
    ('TICARET', 'duz', '#FF2B06'),
    ('KENTSEL_SERVIS', 'duz', '#EFCCFE'),
    ('PARK', 'duz', '#94D47D'),
    ('YESIL_ALAN', 'duz', '#94D47D'),
    ('MESIRE', 'duz', '#7BC223'),
    ('MEZARLIK', 'duz', '#BEDDB0'),
    ('SU_YUZEYI', 'duz', '#7CE4FE'),
    ('SULAMA', 'duz', '#7CE4FE'),
    ('TARIM', 'nokta', '#E9F3D2'),
    ('ZEYTIN', 'nokta', '#DCEBC4'),
    ('MERA', 'nokta', '#E4F0CE'),
    ('OTLAK', 'nokta', '#E4F0CE'),
    ('SULAK', 'nokta', '#CDE7E6'),
    ('DOGAL_KARAKTER', 'nokta', '#D8EAC0'),
    ('AGACLANDIRILACAK', 'nokta', '#C9E5AE'),
    ('ORMAN', 'tarama', '#7CBA6B'),
    ('EKOSISTEM', 'nokta', '#CFE8C4'),
    ('SANAYI', 'tarama', '#C9A9D8'),
    ('ENDUSTRIYEL', 'tarama', '#C9A9D8'),
    ('DEPOLAMA', 'tarama', '#D6C2E2'),
    ('LOJISTIK', 'tarama', '#D6C2E2'),
    ('KONUT_DISI', 'tarama', '#D8C0D8'),
    ('TEKNIK_ALTYAPI', 'tarama', '#C0C0C0'),
    ('ENERJI', 'tarama', '#C8C8C8'),
    ('ATIKSU', 'tarama', '#BFC8D0'),
    ('KATI_ATIK', 'yogun', '#B0B0B0'),
    ('MADEN', 'yogun', '#BFAF9F'),
    ('ASKERI', 'capraz', '#8C8C8C'),
    ('OSB', 'capraz', '#B79ACB'),
    ('ORGANIZE', 'capraz', '#B79ACB'),
    ('TEHLIKELI', 'capraz', '#C89A9A'),
    ('YAPI_YASA', 'capraz', '#C0C0C0'),
    ('ONLEMLI', 'capraz', '#D2C0A8'),
    ('SIT', 'capraz', '#BFD8D8'),
    ('KORUMA', 'capraz', '#BFD8D8'),
)


# e-Plan SLD'leri sembol boyutunu metre cinsinden verir (genelde 15 m); bu
# 1/25000'de 0,6 mm'ye denk gelip gorunmez oldugu icin baski olceginde okunur
# sabit bir mm degeri kullaniyoruz. Semboller kucuk/buyuk gelirse burayi
# degistirin.
MARKER_SIZE_MM = 3.5

# Tarama gorselleri (TaramaResim/*.png) kucuk desen karolaridir (10-45 px).
# QGIS'te karo genisligini mm cinsinden vermek gerekiyor; pikseli 96 dpi
# varsayarak mm'ye ceviriyoruz. Desen cok siki/seyrek gelirse burayi degistirin.
HATCH_TILE_DPI = 96

# SLD'deki sembol boyutu (metre) -> mm. 15 m -> 3,75 mm; 60 m -> 8 mm.
# Ham degeri mm olarak kullanmak 15-60 mm'lik dev harfler urettigi icin
# olceklenip siniriandiriliyor.
MARKER_MIN_MM = 2.0
MARKER_MAX_MM = 8.0
MARKER_SCALE = 0.25


def marker_size_mm(sld_size=None):
    """SLD boyutunu okunabilir bir mm degerine cevirir."""
    try:
        value = float(sld_size) * MARKER_SCALE
    except (TypeError, ValueError):
        return MARKER_SIZE_MM
    if value <= 0:
        return MARKER_SIZE_MM
    return max(MARKER_MIN_MM, min(MARKER_MAX_MM, value))


# QGIS'te kurulu font aileleri. style_apply bunu QFontDatabase'den doldurur.
# None ise kontrol yapilmaz. Kurulu olmayan bir e-Plan fontu istenirse dev ve
# yanlis harfler cizilmemesi icin notr bir isaretciye dusuluyor.
AVAILABLE_FONTS = None


def font_available(family):
    if not family:
        return False
    if AVAILABLE_FONTS is None:
        return True
    target = str(family).strip().lower()
    return any(target == f.strip().lower() for f in AVAILABLE_FONTS)


# Yol ve hat siniflari icin kilif (casing) sembolleri.
# e-Plan SLD'si yollari GeoServer'a ozgu bir yontemle (yol_genisligi alanini
# font boyutuna carparak) cizer; QGIS'te karsiligi yok. Eski veri modelinde de
# genislik alani bulunmadigi icin resmi yol hiyerarsisine gore katmanli cizgi
# uretiyoruz: altta koyu kilif, ustte acik cekirdek.
# Katman sirasi alttan uste: (renk, kalinlik_mm, stil)
#
# Yollar plan olcegine bagli olarak METRE cinsinden cizilir; boylece
# yakinlastikca kalinlik gercek yol genisligini korur (QGIS birimi
# RenderMetersInMapUnits, projenin KBS'si derece olsa da metre calisir).
#
# Kesit yapisi (otoban ornegi, 100 m koridor):
#   alt katman  : beyaz platform, koridor genisligi kadar
#   iceride     : iki yana yaslanmis kalin tasit bantlari (offset +/-)
#   en distaki  : iki ince kenar hatti
# Her katman: (renk, genislik_m, stil, offset_m)
CASING = '#3C3C3C'
LINE_UNIT = 'RenderMetersInMapUnits'

# Yol koridor genislikleri (m) — kurum kabulunuz farkliysa buradan degistirin
ROAD_WIDTHS_M = {'OTOYOL': 100.0, 'BIRINCI': 50.0, 'IKINCI': 35.0,
                 'UCUNCU': 25.0, 'KOY': 12.0}


def _divided_profile(width):
    """Bolunmus yol: beyaz platform + iki kalin tasit banti + kenar hatlari."""
    half = width / 2.0
    band = width * 0.28          # tasit banti kalinligi
    band_off = width * 0.26      # merkeze gore kayma
    edge = max(1.5, width * 0.035)
    return (('#FFFFFF', width, 'solid', 0.0),
            (CASING, band, 'solid', band_off),
            (CASING, band, 'solid', -band_off),
            (CASING, edge, 'solid', half - edge / 2.0),
            (CASING, edge, 'solid', -(half - edge / 2.0)))


def _center_line_profile(width, center_ratio=0.25, edge_ratio=0.05):
    """Bolunmemis yol: iki ince kenar cizgisi + beyaz platform + ortada TEK
    kalin cizgi (ikinci/ucuncu derece, koy yolu).

    Bolunmus yoldan (otoyol, birinci derece) tek farki ortada iki kalin bant
    yerine tek kalin cizgi olmasidir.
    """
    half = width / 2.0
    center = max(1.5, width * center_ratio)
    edge = max(0.8, width * edge_ratio)
    return (('#FFFFFF', width, 'solid', 0.0),
            (CASING, center, 'solid', 0.0),
            (CASING, edge, 'solid', half - edge / 2.0),
            (CASING, edge, 'solid', -(half - edge / 2.0)))


LINE_RULES = (
    ('OTOYOL',         _divided_profile(ROAD_WIDTHS_M['OTOYOL'])),
    ('EKSPRES',        _divided_profile(ROAD_WIDTHS_M['OTOYOL'])),
    # Birinci derece: otoyolla ayni desen, 50 m koridor
    ('BIRINCI_DERECE', _divided_profile(ROAD_WIDTHS_M['BIRINCI'])),
    ('1_DERECE_YOL',   _divided_profile(ROAD_WIDTHS_M['BIRINCI'])),
    # Ikinci/ucuncu derece ve koy yolu: iki ince kenar + beyaz platform +
    # ortada tek kalin cizgi (bolunmemis yol)
    ('IKINCI_DERECE',  _center_line_profile(ROAD_WIDTHS_M['IKINCI'])),
    ('2_DERECE_YOL',   _center_line_profile(ROAD_WIDTHS_M['IKINCI'])),
    ('UCUNCU_DERECE',  _center_line_profile(ROAD_WIDTHS_M['UCUNCU'])),
    ('3_DERECE_YOL',   _center_line_profile(ROAD_WIDTHS_M['UCUNCU'])),
    ('KOY_YOLU',       _center_line_profile(ROAD_WIDTHS_M['KOY'])),
    ('DEMIRYOLU',      (('#000000', 10.0, 'solid', 0.0),
                        ('#FFFFFF', 5.0, 'dash', 0.0))),
    ('RAYLI',          (('#000000', 10.0, 'solid', 0.0),
                        ('#FFFFFF', 5.0, 'dash', 0.0))),
    ('TUNEL',          ((CASING, 12.0, 'dash', 0.0),)),
)

# SLD'den gelen cizgi kalinligi bu degeri asamaz (bazi dosyalarda 2.8 gibi
# degerler var ve harita okunmaz hale geliyor).
MAX_LINE_WIDTH_MM = 1.6


# Kavsak gibi sayisal kodlu nokta katmanlari icin isaretci seti.
# Kodlarin sozluk karsiligi ne MDB domainlerinde ne e-Plan 2026 semasinda
# bulunuyor (ArcMap de lejantta kodu gosteriyor), ama semboller ayrisiyor.
# Resmi gosterimde kavsaklar siyah daire/halka olarak cizilir.
# Her girdi: (sekil, boyut_mm, dolgu, kontur, kontur_kalinligi)
MARKER_CODE_STYLES = {
    # ArcMap cikisinda kavsaklar DOLU SIYAH daire; capi bindigi yolun
    # koridor genisligine gore olceklenir (asagidaki degerler yalnizca yol
    # katmani bulunamadigindaki yedektir, birim METRE).
    'KAVSAK': {
        '1':  [('circle', 100.0, '#000000', '#000000', 0.0)],
        '11': [('circle', 50.0, '#000000', '#000000', 0.0)],
        '12': [('circle', 35.0, '#000000', '#000000', 0.0)],
        '13': [('circle', 25.0, '#000000', '#000000', 0.0)],
    },
}

# Kodlu ama tanimsiz degerler icin ayrisan yedek sekiller
FALLBACK_MARKER_SHAPES = ('circle', 'square', 'triangle', 'diamond',
                          'pentagon', 'star')


def _is_junction(class_key):
    return 'KAVSAK' in normalize(class_key or '')


def code_marker_layers(class_key, value):
    """Sayisal kodlu nokta degerleri icin isaretci katmanlari.

    Donus: [(sekil, boyut, dolgu, kontur, kontur_kalinligi), ...] ya da None
    """
    key = normalize(class_key or '')
    value = str(value or '').strip()
    for needle, table in MARKER_CODE_STYLES.items():
        if needle in key:
            if value in table:
                return table[value]
            if re.match(r'^\d+$', value):
                shape = FALLBACK_MARKER_SHAPES[
                    int(value) % len(FALLBACK_MARKER_SHAPES)]
                return [(shape, 25.0, '#000000', '#000000', 0.0)]
    return None


def builtin_coverage(layer_key, values, geometry='polygon'):
    """Kendi tablolarimizin kapsadigi deger orani (0..1).

    Kutuphane isim eslesmesi tutmasa da yol kesiti (LINE_RULES), kodlu kavsak
    isaretcisi (MARKER_CODE_STYLES) ya da desen/renk tablosu (PATTERN_RULES)
    degeri taniyabilir. Bu durumda katmana tek sembol uygulamak yerine kural
    tabanli gosterim uretilmelidir; aksi halde butun kavsaklar ayni noktaya,
    butun yollar ayni cizgiye duser.
    """
    values = [v for v in (values or []) if str(v).strip()]
    if not values:
        return 0.0
    hit = 0
    for value in values:
        if geometry == 'line':
            if line_rule_for(value):
                hit += 1
        elif geometry == 'point':
            if code_marker_layers(layer_key, value):
                hit += 1
        elif pattern_for(value)[0]:
            hit += 1
    return hit / float(len(values))


def line_rule_for(class_name):
    """Yol/hat sinifi icin katmanli cizgi tanimi; yoksa None."""
    key = normalize(class_name)
    for needle, layers in LINE_RULES:
        if needle in key:
            return layers
    return None


def pattern_for(class_name):
    """Sinif adina gore (desen, zemin_rengi) dondurur; yoksa (None, None)."""
    key = normalize(class_name)
    for needle, kind, color in PATTERN_RULES:
        if needle in key:
            return kind, color
    return None, None


def normalize(text):
    """'BELEDİYE HİZMET ALANI' -> 'BELEDIYE_HIZMET_ALANI'"""
    s = str(text or '').translate(TR_MAP).upper()
    s = re.sub(r'[^A-Z0-9]+', '_', s)
    return s.strip('_')


def _strip_suffix(key):
    """Sondaki yok sayilabilir ekleri tekrarli olarak soyar.

    Tek gecis yetmiyor: 'SAGLIKLASTIRMA_ALANI_SINIRI' ile
    'SAGLIKLASTIRMA_ALAN_SINIRI' ancak hem _SINIRI hem _ALANI/_ALAN
    soyulunca ayni koke iniyor.
    """
    out = key
    for _ in range(3):
        for suf in DROP_SUFFIX:
            if out.endswith(suf) and len(out) > len(suf) + 3:
                out = out[:-len(suf)]
                break
        else:
            break
    return out


def _tokens(key):
    return set(t for t in key.split('_') if len(t) > 2)


# --------------------------------------------------------------------------
# SLD cozumleme
# --------------------------------------------------------------------------
class RuleSpec(object):
    """Kutuphanedeki tek bir gosterim kurali."""

    def __init__(self):
        self.source = ''        # dosya adi (NIP_KENTSEL_CALISMA)
        self.title = ''         # kural basligi (BELEDIYE_HIZMET_ALANI)
        self.geom = 'polygon'   # polygon / line / point
        self.fill = None        # '#rrggbb'
        self.fill_opacity = 1.0
        self.stroke = None
        self.stroke_width = 0.26
        self.stroke_dash = None
        self.hatch = False      # tarama gorseli gerekiyordu
        self.hatch_image = None  # ExternalGraphic dosya adi (guid.png)
        self.hatch_path = None   # diskte bulunduysa tam yol
        self.font_family = None
        self.font_char = None
        self.marker_color = None   # poligon merkezindeki harf sembolu rengi
        self.value_label = None    # eslesen lejant degeri (desen/yol secimi icin)
        self.layer_key = None      # katman/tablo adi (kodlu sembol secimi icin)
        self.size = 3.0
        self.max_scale = None

    @property
    def key(self):
        return normalize(self.title)

    def __repr__(self):
        return '<RuleSpec %s/%s %s>' % (self.source, self.title, self.geom)


def _localname(tag):
    return tag.rsplit('}', 1)[-1]


def _css(node):
    """CssParameter / SvgParameter degerlerini sozluk olarak dondurur."""
    out = {}
    for child in node.iter():
        ln = _localname(child.tag)
        if ln in ('CssParameter', 'SvgParameter'):
            name = child.get('name')
            if name:
                out[name] = (child.text or '').strip()
    return out


def parse_sld(path):
    """Bir .sld dosyasindan RuleSpec listesi cikarir."""
    try:
        tree = ET.parse(path)  # nosec B314 - yalniz eklentiyle gelen e-Plan SLD dosyasi
    except ET.ParseError:
        return []
    root = tree.getroot()
    source = os.path.splitext(os.path.basename(path))[0]
    specs = []

    for rule in [n for n in root.iter() if _localname(n.tag) == 'Rule']:
        title = ''
        for ch in rule:
            if _localname(ch.tag) == 'Title':
                title = (ch.text or '').strip()
        if not title:
            continue

        spec = RuleSpec()
        spec.source = source
        # Tek sinifli katmanlarda kural basligi dosya adiyla ayni olur
        # (ornek NIP_ORMAN); bu durumda on eki atip sinif adini kullaniyoruz.
        spec.title = (re.sub(r'^(M?NIP|M?UIP|CDP)_', '', title)
                      if normalize(title) == normalize(source) else title)

        for ch in rule:
            if _localname(ch.tag) == 'MaxScaleDenominator':
                try:
                    spec.max_scale = float(ch.text)
                except (TypeError, ValueError):
                    pass

        symbolizers = [n for n in rule.iter()
                       if _localname(n.tag).endswith('Symbolizer')]
        if not symbolizers:
            continue
        kinds = [_localname(n.tag) for n in symbolizers]
        # Onemli: poligon kurallari genelde ek olarak bir PointSymbolizer
        # (alan merkezine konan harf sembolu) icerir. Bu yuzden poligon
        # onceliklidir, yoksa dolgu rengi isaretci rengiyle karisir.
        if 'PolygonSymbolizer' in kinds:
            spec.geom = 'polygon'
        elif 'LineSymbolizer' in kinds:
            spec.geom = 'line'
        elif 'PointSymbolizer' in kinds:
            spec.geom = 'point'
        else:
            spec.geom = 'polygon'

        for sym in symbolizers:
            ln = _localname(sym.tag)
            if ln == 'PolygonSymbolizer':
                for part in sym:
                    pln = _localname(part.tag)
                    if pln == 'Fill':
                        for n in part.iter():
                            if _localname(n.tag) == 'ExternalGraphic':
                                spec.hatch = True
                                spec.hatch_image = _graphic_name(n)
                                break
                        css = _css(part)
                        spec.fill = css.get('fill', spec.fill)
                        if 'fill-opacity' in css:
                            try:
                                spec.fill_opacity = float(css['fill-opacity'])
                            except ValueError:
                                pass
                    elif pln == 'Stroke':
                        css = _css(part)
                        spec.stroke = css.get('stroke', spec.stroke)
                        spec.stroke_width = _f(css.get('stroke-width'),
                                               spec.stroke_width)
                        spec.stroke_dash = css.get('stroke-dasharray')
            elif ln == 'LineSymbolizer':
                css = _css(sym)
                spec.stroke = css.get('stroke', spec.stroke)
                spec.stroke_width = _f(css.get('stroke-width'), spec.stroke_width)
                spec.stroke_dash = css.get('stroke-dasharray')
            elif ln == 'PointSymbolizer':
                # Poligon kurallarinda da bulunur: alanin merkezine konan
                # e-Plan harf/sembol isaretcisi (TTF glifi). Poligonun dolgu
                # rengini bozmamak icin isaretci rengini ayri tutuyoruz.
                css = _css(sym)
                if spec.geom == 'point':
                    spec.fill = css.get('fill', spec.fill)
                    spec.stroke = css.get('stroke', spec.stroke)
                spec.marker_color = css.get('fill') or '#000000'
                for n in sym.iter():
                    nln = _localname(n.tag)
                    if nln == 'WellKnownName':
                        wkn = (n.text or '').strip()
                        m = re.match(r'ttf://([^#]+)#0x([0-9a-fA-F]+)', wkn)
                        if m:
                            spec.font_family = m.group(1)
                            spec.font_char = chr(int(m.group(2), 16))
                    elif nln == 'Size':
                        spec.size = _f(n.text, spec.size)
                    elif nln == 'ExternalGraphic':
                        spec.hatch = True
                        if not spec.hatch_image:
                            spec.hatch_image = _graphic_name(n)
        specs.append(spec)
    return specs


def _graphic_name(node):
    """ExternalGraphic icindeki OnlineResource href'inden dosya adini alir."""
    for child in node.iter():
        if _localname(child.tag) != 'OnlineResource':
            continue
        for key, value in child.attrib.items():
            if key.rsplit('}', 1)[-1] == 'href' and value:
                return os.path.basename(value.split('?')[0])
    return None


def find_image_dir(start):
    """Tarama gorsellerinin (TaramaResim) bulundugu klasoru arar.

    Stil klasorunun altinda ya da ust klasorlerinde olabilir; e-Plan dagitimi
    'TaramaResim' adiyla gelir.
    """
    def _usable(path):
        try:
            return os.path.isdir(path) and any(
                f.lower().endswith('.png') for f in os.listdir(path))
        except OSError:
            return False

    # Baslangictan yukari dogru 6 seviye: .../styles -> ... -> eplan2026
    bases = []
    here = os.path.abspath(start)
    for _ in range(7):
        bases.append(here)
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent

    for base in bases:
        direct = os.path.join(base, 'TaramaResim')
        if _usable(direct):
            return direct
        # iki seviye derinlikte tara (buyuk/kucuk harf farkina karsi)
        try:
            for name in os.listdir(base):
                if name.startswith('__'):
                    continue
                path = os.path.join(base, name)
                if not os.path.isdir(path):
                    continue
                if name.lower() == 'taramaresim' and _usable(path):
                    return path
                try:
                    for sub in os.listdir(path):
                        if sub.lower() == 'taramaresim':
                            found = os.path.join(path, sub)
                            if _usable(found):
                                return found
                except OSError:
                    continue
        except OSError:
            continue
    return None


def _f(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Kutuphane + eslestirme
# --------------------------------------------------------------------------
class StyleLibrary(object):
    """e-Plan stil klasorunu (NiP/UiP/CDP/styles) indeksler."""

    def __init__(self, root, prefixes=None, image_dir=None):
        self.root = root
        self.image_dir = image_dir if image_dir is not None \
            else find_image_dir(root)
        self.images_found = 0
        self.rules = []           # RuleSpec listesi
        self.by_key = {}          # normalize(title) -> [RuleSpec]
        self.by_key_sq = {}       # alt cizgisiz hali -> [RuleSpec]
        self.files = 0
        self._load(prefixes)

    def _load(self, prefixes):
        for dirpath, _dirs, files in os.walk(self.root):
            for fn in files:
                if not fn.lower().endswith('.sld'):
                    continue
                if prefixes and not any(fn.upper().startswith(p.upper())
                                        for p in prefixes):
                    continue
                self.files += 1
                for spec in parse_sld(os.path.join(dirpath, fn)):
                    if spec.hatch_image and self.image_dir:
                        candidate = os.path.join(self.image_dir,
                                                 spec.hatch_image)
                        if os.path.exists(candidate):
                            spec.hatch_path = candidate
                            self.images_found += 1
                    self.rules.append(spec)
                    self.by_key.setdefault(spec.key, []).append(spec)
                    self.by_key_sq.setdefault(
                        spec.key.replace('_', ''), []).append(spec)

    # -------------------------------------------------------------- matching
    def match(self, value):
        """Lejant degerini kutuphanedeki bir kurala eslestirir.

        Donus: (RuleSpec veya None, guven 0..1, yontem)
        """
        key = normalize(value)
        if not key or re.match(r'^[0-9_]+$', key):
            return (None, 0.0, 'gecersiz')

        if key in self.by_key:
            return (self._pick(self.by_key[key]), 1.0, 'tam')

        # Birlesik yazim (AFETEMARUZBOLGE) <-> ayrik yazim (AFETE_MARUZ_BOLGE)
        key_sq = key.replace('_', '')
        if key_sq in self.by_key_sq:
            return (self._pick(self.by_key_sq[key_sq]), 0.95, 'tam_birlesik')

        # Nitelik ekini (yogunluk/derece) ayirip tekrar dene
        base, qual = self._split_qualifier(key)
        if qual and base in self.by_key:
            return (self._pick(self.by_key[base]), 0.9, 'nitelik_ayrildi')

        stripped = _strip_suffix(key)
        for cand_key, specs in self.by_key.items():
            if _strip_suffix(cand_key) == stripped:
                return (self._pick(specs), 0.85, 'sonek_yoksayildi')

        if qual:
            # ornek: MEVCUT_KONUT + DUSUK -> MEVCUT_KONUT dosyasinda DUSUK kurali
            best = None
            for spec in self.rules:
                if _strip_suffix(normalize(spec.source)).endswith(
                        _strip_suffix(base)[-14:]) and qual in spec.key:
                    best = spec
                    break
            if best is not None:
                return (best, 0.8, 'nitelik_kurali')

        # Belirteç ortakligi (Jaccard)
        want = _tokens(stripped)
        if want:
            scored = []
            for cand_key, specs in self.by_key.items():
                have = _tokens(_strip_suffix(cand_key))
                if not have:
                    continue
                inter = len(want & have)
                if not inter:
                    continue
                score = inter / float(len(want | have))
                scored.append((score, cand_key, specs))
            if scored:
                scored.sort(reverse=True)
                score, _k, specs = scored[0]
                if score >= 0.5:
                    return (self._pick(specs), round(score, 2), 'belirtec')
        return (None, 0.0, 'eslesme_yok')

    @staticmethod
    def _split_qualifier(key):
        """'GELISME_KONUT_ALANI_DUSUK_YOGUNLUKTA' -> ('GELISME_KONUT', 'DUSUK')"""
        # "YOGUNLUK / YOGUNLUKTA / YOGUNLUKLU" kuyruklarini at
        base = re.sub(r'_YOGUNLU\w*$', '', key)
        found = None
        for q in QUALIFIERS:                       # uzun olanlar once denenir
            pat = r'(^|_)' + q + r'($|_)'
            if re.search(pat, base):
                found = q
                base = re.sub(pat, r'\1\2', base).replace('__', '_').strip('_')
                break
        return (base, found) if found else (key, None)

    @staticmethod
    def _pick(specs):
        """Ayni baslikta birden fazla kural varsa en zenginini sec."""
        def score(s):
            return ((s.fill is not None) + (s.stroke is not None)
                    + (s.font_family is not None) - (1 if s.hatch else 0))
        return sorted(specs, key=score, reverse=True)[0]


# --------------------------------------------------------------------------
# QML uretimi
# --------------------------------------------------------------------------
def _rgba(hex_color, opacity=1.0):
    """'#aabbcc' -> '170,187,204,255,rgb:...' (QGIS renk dizesi)"""
    if not hex_color:
        return '0,0,0,0,rgb:0,0,0,0'
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except (ValueError, IndexError):
        r = g = b = 0
    a = int(max(0.0, min(1.0, opacity)) * 255)
    return '%d,%d,%d,%d,rgb:%0.7f,%0.7f,%0.7f,%0.7f' % (
        r, g, b, a, r / 255.0, g / 255.0, b / 255.0, a / 255.0)


def _opt(parent, name, value, vtype='QString'):
    ET.SubElement(parent, 'Option', {'value': str(value), 'type': vtype,
                                     'name': name})


def _ddp(parent):
    """Bos data-defined-properties blogu (QGIS her sembolde bekler)."""
    node = ET.SubElement(parent, 'data_defined_properties')
    opt = ET.SubElement(node, 'Option', {'type': 'Map'})
    _opt(opt, 'name', '')
    ET.SubElement(opt, 'Option', {'name': 'properties'})
    _opt(opt, 'type', 'collection')


def _ddp_expr(parent, prop_name, expression):
    """Veri tanimli ozellik (ornek: boyut ifadesi) blogu yazar."""
    node = ET.SubElement(parent, 'data_defined_properties')
    opt = ET.SubElement(node, 'Option', {'type': 'Map'})
    _opt(opt, 'name', '')
    props = ET.SubElement(opt, 'Option', {'type': 'Map', 'name': 'properties'})
    entry = ET.SubElement(props, 'Option', {'type': 'Map', 'name': prop_name})
    _opt(entry, 'active', 'true', 'bool')
    _opt(entry, 'expression', expression)
    _opt(entry, 'type', '3', 'int')
    _opt(opt, 'type', 'collection')
    return node


# Kavsak capini uzerinde oturdugu yolun koridor genisligine baglayan ifade.
# overlay_nearest en yakin yol nesnesini bulur; bulamazsa yedek deger kullanilir.
JUNCTION_SIZE_EXPR = (
    "coalesce(array_first(overlay_nearest('{layer}', case"
    " when \"lejantdomain\" ilike '%OTOYOL%'"
    " or \"lejantdomain\" ilike '%EKSPRES%' then {otoyol}"
    " when \"lejantdomain\" ilike '%BIRINCI%'"
    " or \"lejantdomain\" ilike '%BİRİNCİ%' then {birinci}"
    " when \"lejantdomain\" ilike '%IKINCI%'"
    " or \"lejantdomain\" ilike '%İKİNCİ%' then {ikinci}"
    " when \"lejantdomain\" ilike '%UCUNCU%'"
    " or \"lejantdomain\" ilike '%ÜÇÜNCÜ%' then {ucuncu}"
    " when \"lejantdomain\" ilike '%KOY%'"
    " or \"lejantdomain\" ilike '%KÖY%' then {koy}"
    " else {yedek} end, limit:=1, max_distance:={mesafe})), {yedek})")


def junction_size_expression(road_layer, fallback=25.0, max_distance=150.0):
    """Kavsak capi icin veri tanimli boyut ifadesi (metre)."""
    if not road_layer:
        return None
    return '(%s) * %g' % (JUNCTION_SIZE_EXPR.format(
        layer=str(road_layer).replace("'", "''"),
        otoyol=ROAD_WIDTHS_M['OTOYOL'], birinci=ROAD_WIDTHS_M['BIRINCI'],
        ikinci=ROAD_WIDTHS_M['IKINCI'], ucuncu=ROAD_WIDTHS_M['UCUNCU'],
        koy=ROAD_WIDTHS_M['KOY'], yedek=fallback, mesafe=max_distance),
                          JUNCTION_SIZE_RATIO)


# Kavsak capi = bindigi yolun koridor genisligi x bu oran
JUNCTION_SIZE_RATIO = 1.15

# Yol katmani adi; style_apply yukleme sirasinda doldurur. None ise kavsak
# capi kod tablosundaki sabit degerdir.
ROAD_LAYER_NAME = None


def _new_symbol(parent, index, stype):
    sym = ET.SubElement(parent, 'symbol', {
        'type': stype, 'name': str(index), 'alpha': '1', 'force_rhr': '0',
        'clip_to_extent': '1', 'frame_rate': '10', 'is_animated': '0'})
    _ddp(sym)
    return sym


# QML sembol katmaninin cizim gecisi (rendering pass) ozniteligi
QML_GECIS = "pa" + "ss"


def _layer(sym, cls):
    oz = {'id': '{%s}' % uuid.uuid4(), 'class': cls, 'locked': '0', 'enabled': '1'}
    oz[QML_GECIS] = '0'
    return ET.SubElement(sym, 'layer', oz)


def _simple_fill_layer(sym, fill, stroke, width=0.26, dash=None, opacity=1.0):
    # Ne dolgu ne kontur varsa alan hic gorunmez; en azindan kontur cizelim
    if not fill and not stroke:
        stroke = '#646464'
    lyr = _layer(sym, 'SimpleFill')
    opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(opt, 'color', _rgba(fill, opacity))
    _opt(opt, 'style', 'solid' if fill else 'no')
    _opt(opt, 'outline_color', _rgba(stroke or '#000000'))
    _opt(opt, 'outline_width', '%g' % width)
    _opt(opt, 'outline_width_unit', 'MM')
    _opt(opt, 'outline_style', 'dash' if dash else ('solid' if stroke else 'no'))
    _opt(opt, 'joinstyle', 'bevel')
    _ddp(lyr)
    return lyr


def _line_sub_symbol(parent, name, color, width=0.2):
    sub = ET.SubElement(parent, 'symbol', {
        'type': 'line', 'name': name, 'alpha': '1', 'force_rhr': '0',
        'clip_to_extent': '1', 'frame_rate': '10', 'is_animated': '0'})
    _ddp(sub)
    sl = _layer(sub, 'SimpleLine')
    o = ET.SubElement(sl, 'Option', {'type': 'Map'})
    _opt(o, 'line_color', _rgba(color))
    _opt(o, 'line_width', '%g' % width)
    _opt(o, 'line_width_unit', 'MM')
    _opt(o, 'line_style', 'solid')
    _opt(o, 'capstyle', 'square')
    _opt(o, 'joinstyle', 'bevel')
    _ddp(sl)
    return sub


def _marker_sub_symbol(parent, name, color, size=0.6):
    sub = ET.SubElement(parent, 'symbol', {
        'type': 'marker', 'name': name, 'alpha': '1', 'force_rhr': '0',
        'clip_to_extent': '1', 'frame_rate': '10', 'is_animated': '0'})
    _ddp(sub)
    sm = _layer(sub, 'SimpleMarker')
    o = ET.SubElement(sm, 'Option', {'type': 'Map'})
    _opt(o, 'name', 'circle')
    _opt(o, 'color', _rgba(color))
    _opt(o, 'outline_style', 'no')
    _opt(o, 'outline_color', _rgba(color))
    _opt(o, 'outline_width', '0')
    _opt(o, 'size', '%g' % size)
    _opt(o, 'size_unit', 'MM')
    _ddp(sm)
    return sub


def _line_pattern_layer(sym, index, seq, color, angle, distance, width=0.2):
    lyr = _layer(sym, 'LinePatternFill')
    opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(opt, 'angle', '%g' % angle)
    _opt(opt, 'distance', '%g' % distance)
    _opt(opt, 'distance_unit', 'MM')
    _opt(opt, 'line_width', '%g' % width)
    _opt(opt, 'line_width_unit', 'MM')
    _opt(opt, 'color', _rgba(color))
    _opt(opt, 'offset', '0')
    _opt(opt, 'offset_unit', 'MM')
    _ddp(lyr)
    _line_sub_symbol(lyr, '@%d@%d' % (index, seq), color, width)
    return lyr


def _point_pattern_layer(sym, index, seq, color, distance=2.2):
    lyr = _layer(sym, 'PointPatternFill')
    opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(opt, 'distance_x', '%g' % distance)
    _opt(opt, 'distance_y', '%g' % distance)
    _opt(opt, 'distance_x_unit', 'MM')
    _opt(opt, 'distance_y_unit', 'MM')
    _opt(opt, 'displacement_x', '0')
    _opt(opt, 'displacement_y', '0')
    _opt(opt, 'offset_x', '0')
    _opt(opt, 'offset_y', '0')
    _ddp(lyr)
    _marker_sub_symbol(lyr, '@%d@%d' % (index, seq), color)
    return lyr


def _centroid_font_layer(sym, index, seq, spec):
    """Alanin merkezine e-Plan TTF harf sembolunu koyar."""
    lyr = _layer(sym, 'CentroidFill')
    opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(opt, 'clip_on_current_part_only', '0')
    _opt(opt, 'clip_points', '0')
    _opt(opt, 'point_on_all_parts', '0')
    _opt(opt, 'point_on_surface', '1')
    _ddp(lyr)
    sub = ET.SubElement(lyr, 'symbol', {
        'type': 'marker', 'name': '@%d@%d' % (index, seq), 'alpha': '1',
        'force_rhr': '0', 'clip_to_extent': '1', 'frame_rate': '10',
        'is_animated': '0'})
    _ddp(sub)
    fm = _layer(sub, 'FontMarker')
    o = ET.SubElement(fm, 'Option', {'type': 'Map'})
    _opt(o, 'font', spec.font_family)
    _opt(o, 'chr', spec.font_char)
    _opt(o, 'color', _rgba(spec.marker_color or '#000000'))
    _opt(o, 'size', '%.2f' % marker_size_mm(spec.size))
    _opt(o, 'size_unit', 'MM')
    _opt(o, 'outline_color', _rgba('#FFFFFF'))
    _opt(o, 'outline_width', '0')
    _opt(o, 'outline_width_unit', 'MM')
    _opt(o, 'joinstyle', 'miter')
    _opt(o, 'angle', '0')
    _ddp(fm)
    return lyr


def _image_size(path):
    """Gorsel genislik/yukseklik (piksel).

    e-Plan dagitimindaki tarama karolari .png uzantili olsa da icerik
    cogunlukla BMP'dir; bu yuzden uzantiya degil imzaya bakiyoruz.
    """
    import struct
    try:
        with open(path, 'rb') as fh:
            head = fh.read(32)
    except OSError:
        return None
    try:
        if head[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', head[16:24])
        if head[:2] == b'BM':
            width, height = struct.unpack('<ii', head[18:26])
            return (abs(width), abs(height))
        if head[:6] in (b'GIF87a', b'GIF89a'):
            return struct.unpack('<HH', head[6:10])
    except struct.error:
        return None
    return None


def _raster_fill_layer(sym, spec):
    """Resmi e-Plan tarama gorselini dogrudan dolgu olarak kullanir."""
    lyr = _layer(sym, 'RasterFill')
    o = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    size = _image_size(spec.hatch_path)
    width_mm = (size[0] * 25.4 / HATCH_TILE_DPI) if size else 6.0
    width_mm = max(1.5, min(60.0, width_mm))
    _opt(o, 'imageFile', spec.hatch_path)
    _opt(o, 'alpha', '1')
    _opt(o, 'width', '%.3f' % width_mm)
    _opt(o, 'width_unit', 'MM')
    _opt(o, 'coordinate_mode', '0')
    _opt(o, 'angle', '0')
    _opt(o, 'offset_x', '0')
    _opt(o, 'offset_y', '0')
    _opt(o, 'offset_unit', 'MM')
    _ddp(lyr)
    return lyr


def _emit_ring(sym, spec):
    """Sadece kontur cizen dolgu katmani (RasterFill uzerine cerceve)."""
    lyr = _layer(sym, 'SimpleFill')
    o = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(o, 'color', _rgba(None, 0))
    _opt(o, 'style', 'no')
    _opt(o, 'outline_color', _rgba(spec.stroke))
    _opt(o, 'outline_width', '%g' % spec.stroke_width)
    _opt(o, 'outline_width_unit', 'MM')
    _opt(o, 'outline_style', 'dash' if spec.stroke_dash else 'solid')
    _opt(o, 'joinstyle', 'bevel')
    _ddp(lyr)
    return lyr


def _centroid_fallback_layer(sym, index, seq, spec):
    """Font kurulu degilse alan merkezine kucuk notr bir isaretci koyar.

    Kurulu olmayan bir fontla FontMarker uretilirse QGIS yedek fontla ham
    karakteri cizer ve haritada dev, anlamsiz harfler olusur; bunun yerine
    kucuk bir kare kullaniyoruz.
    """
    lyr = _layer(sym, 'CentroidFill')
    o = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(o, 'clip_on_current_part_only', '0')
    _opt(o, 'clip_points', '0')
    _opt(o, 'point_on_all_parts', '0')
    _opt(o, 'point_on_surface', '1')
    _ddp(lyr)
    sub = ET.SubElement(lyr, 'symbol', {
        'type': 'marker', 'name': '@%d@%d' % (index, seq), 'alpha': '1',
        'force_rhr': '0', 'clip_to_extent': '1', 'frame_rate': '10',
        'is_animated': '0'})
    _ddp(sub)
    sm = _layer(sub, 'SimpleMarker')
    o2 = ET.SubElement(sm, 'Option', {'type': 'Map'})
    _opt(o2, 'name', 'square')
    _opt(o2, 'color', _rgba(spec.marker_color or '#323232'))
    _opt(o2, 'outline_color', _rgba('#FFFFFF'))
    _opt(o2, 'outline_width', '0.2')
    _opt(o2, 'outline_width_unit', 'MM')
    _opt(o2, 'size', '1.60')
    _opt(o2, 'size_unit', 'MM')
    _ddp(sm)
    return lyr


def _fill_symbol(parent, index, spec):
    """Dolgu sembolu: zemin rengi + desen + merkezdeki harf sembolu."""
    sym = _new_symbol(parent, index, 'fill')
    seq = 0

    # Resmi tarama gorseli diskte bulunduysa birebir onu kullan
    if spec.hatch_path:
        if spec.fill:
            _simple_fill_layer(sym, spec.fill, None, spec.stroke_width,
                               None, spec.fill_opacity)
            seq += 1
        _raster_fill_layer(sym, spec)
        seq += 1
        if spec.stroke:
            _emit_ring(sym, spec)
            seq += 1
        if spec.font_family and spec.font_char:
            if font_available(spec.font_family):
                _centroid_font_layer(sym, index, seq + 1, spec)
            else:
                _centroid_fallback_layer(sym, index, seq + 1, spec)
        return sym

    kind, default_bg = (None, None)
    if spec.hatch:
        # Once kural basligi (BELEDIYE_HIZMET_ALANI), tutmazsa dosya adi
        # (NIP_MEVCUT_KONUT) — yogunluk kurallarinda baslik 'DUSUK_51_151HA'
        # gibi oldugu icin sinif adi dosyadan gelir.
        kind, default_bg = pattern_for(spec.value_label or '')
        if kind is None:
            kind, default_bg = pattern_for(spec.title)
        if kind is None:
            kind, default_bg = pattern_for(spec.source)
        if kind is None:
            # e-Plan'da bu sinifin duz rengi yok, gorunum tarama gorselinden
            # geliyordu. Gorsel elimizde olmadigi icin acik zemin + ince
            # capraz tarama kullaniyoruz ki alan bos/seffaf gorunmesin.
            kind, default_bg = 'tarama_ince', '#FFFFFF'

    if kind:
        bg = spec.fill or default_bg
        ink = spec.stroke or _darken(bg, 0.45)
        _simple_fill_layer(sym, bg, spec.stroke, spec.stroke_width,
                           spec.stroke_dash)
        seq += 1
        if kind == 'duz':
            pass                      # desen yok, sadece duz zemin
        elif kind == 'nokta':
            _point_pattern_layer(sym, index, seq, ink)
        elif kind == 'tarama':
            _line_pattern_layer(sym, index, seq, ink, 45, 2.0)
        elif kind == 'tarama_ince':
            _line_pattern_layer(sym, index, seq, ink, 45, 3.0, 0.15)
        elif kind == 'capraz':
            _line_pattern_layer(sym, index, seq, ink, 45, 1.8)
            seq += 1
            _line_pattern_layer(sym, index, seq, ink, 135, 1.8)
        elif kind == 'yogun':
            _line_pattern_layer(sym, index, seq, ink, 45, 0.9, 0.25)
    else:
        _simple_fill_layer(sym, spec.fill, spec.stroke, spec.stroke_width,
                           spec.stroke_dash, spec.fill_opacity)
        seq += 1

    if spec.font_family and spec.font_char:
        if font_available(spec.font_family):
            _centroid_font_layer(sym, index, seq + 1, spec)
        else:
            _centroid_fallback_layer(sym, index, seq + 1, spec)
    return sym


def _darken(hex_color, factor=0.55):
    """Desen cizgisi icin zemin renginin koyu tonu."""
    if not hex_color:
        return '#606060'
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        return '#606060'
    return '#%02X%02X%02X' % (int(r * factor), int(g * factor), int(b * factor))


def _simple_line_layer(sym, color, width, style='solid', dash=None,
                       cap='round', join='round', offset=0.0, unit='MM'):
    lyr = _layer(sym, 'SimpleLine')
    opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(opt, 'line_color', _rgba(color or '#000000'))
    _opt(opt, 'line_width', '%.3f' % max(0.05, width))
    _opt(opt, 'line_width_unit', unit)
    _opt(opt, 'line_style', style)
    if dash:
        _opt(opt, 'use_custom_dash', '1')
        _opt(opt, 'customdash', dash.replace(' ', ';') or '5;2')
        _opt(opt, 'customdash_unit', unit)
    _opt(opt, 'capstyle', cap)
    _opt(opt, 'joinstyle', join)
    _opt(opt, 'offset', '%.3f' % offset)
    _opt(opt, 'offset_unit', unit)
    _ddp(lyr)
    return lyr


def _line_symbol(parent, index, spec):
    """Cizgi sembolu. Yol siniflarinda metre olcekli kesit uretilir."""
    sym = _new_symbol(parent, index, 'line')

    layers = (line_rule_for(spec.value_label)
              or line_rule_for(spec.title)
              or line_rule_for(spec.source))
    if layers:
        for color, width, style, offset in layers:
            # Kesikli desen de metre cinsinden olsun (yaklasik 3:1,5)
            dash = '%.1f;%.1f' % (width * 3.0, width * 1.6) \
                if style == 'dash' else None
            _simple_line_layer(sym, color, width, style, dash,
                               cap='flat' if offset else 'round',
                               offset=offset, unit=LINE_UNIT)
        return sym

    width = min(MAX_LINE_WIDTH_MM, max(0.1, spec.stroke_width))
    _simple_line_layer(sym, spec.stroke or spec.fill or '#000000', width,
                       'dash' if spec.stroke_dash else 'solid',
                       spec.stroke_dash)
    return sym


def _plain_marker_layer(sym, shape, size, fill, outline, outline_width,
                        unit='MM', size_expr=None, ring_expr=None):
    lyr = _layer(sym, 'SimpleMarker')
    o = ET.SubElement(lyr, 'Option', {'type': 'Map'})
    _opt(o, 'name', shape)
    _opt(o, 'color', _rgba(fill))
    _opt(o, 'outline_color', _rgba(outline))
    _opt(o, 'outline_width', '%.3f' % outline_width)
    _opt(o, 'outline_width_unit', unit)
    _opt(o, 'outline_style', 'solid' if outline_width > 0 else 'no')
    _opt(o, 'size', '%.3f' % size)
    _opt(o, 'size_unit', unit)
    _opt(o, 'angle', '0')
    _opt(o, 'offset', '0,0')
    _opt(o, 'offset_unit', 'MM')
    _opt(o, 'horizontal_anchor_point', '1')
    _opt(o, 'vertical_anchor_point', '1')
    if size_expr:
        _ddp_expr(lyr, 'size', size_expr)
        if ring_expr:
            _ddp_expr(lyr, 'outline_width', ring_expr)
    else:
        _ddp(lyr)
    return lyr


def _marker_symbol(parent, index, spec):
    sym = _new_symbol(parent, index, 'marker')
    size = marker_size_mm(spec.size)

    # Sayisal kodlu nokta siniflari (kavsak vb.): kodlara gore ayrisan
    # siyah daire/halka sembolleri
    coded = code_marker_layers(spec.layer_key or spec.source,
                               spec.value_label)
    if coded:
        expr = junction_size_expression(ROAD_LAYER_NAME) \
            if _is_junction(spec.layer_key or spec.source) else None
        for shape, msize, fill, outline, width in coded:
            _plain_marker_layer(sym, shape, msize, fill, outline, width,
                                unit=LINE_UNIT, size_expr=expr)
        return sym
    if spec.font_family and spec.font_char and font_available(spec.font_family):
        lyr = _layer(sym, 'FontMarker')
        opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
        _opt(opt, 'font', spec.font_family)
        _opt(opt, 'chr', spec.font_char)
        _opt(opt, 'color', _rgba(spec.fill or '#000000'))
        _opt(opt, 'size', '%.2f' % size)
        _opt(opt, 'size_unit', 'MM')
        _opt(opt, 'outline_color', _rgba(spec.stroke or '#000000'))
        _opt(opt, 'outline_width', '0')
        _opt(opt, 'joinstyle', 'miter')
        _ddp(lyr)
    else:
        lyr = _layer(sym, 'SimpleMarker')
        opt = ET.SubElement(lyr, 'Option', {'type': 'Map'})
        _opt(opt, 'name', 'circle')
        _opt(opt, 'color', _rgba(spec.fill or '#c8c8c8'))
        _opt(opt, 'outline_color', _rgba(spec.stroke or '#232323'))
        _opt(opt, 'outline_width', '0.2')
        _opt(opt, 'outline_width_unit', 'MM')
        _opt(opt, 'size', '%.2f' % max(1.5, min(4.0, size)))
        _opt(opt, 'size_unit', 'MM')
        _ddp(lyr)
    return sym


def _quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def write_qml(path, field, entries, geometry='polygon', layer_name=''):
    """Kural tabanli QML yazar.

    entries: [(deger, etiket, RuleSpec veya None), ...]
    geometry: 'polygon' | 'line' | 'point'
    """
    qgis = ET.Element('qgis', {
        'version': '3.34.0', 'styleCategories': 'Symbology',
        'labelsEnabled': '0', 'simplifyLocal': '1', 'simplifyAlgorithm': '0',
        'simplifyDrawingTol': '1', 'simplifyDrawingHints': '1',
        'simplifyMaxScale': '1', 'readOnly': '0', 'minScale': '100000000',
        'maxScale': '0', 'hasScaleBasedVisibilityFlag': '0',
        'symbologyReferenceScale': '-1'})
    renderer = ET.SubElement(qgis, 'renderer-v2', {
        'type': 'RuleRenderer', 'symbollevels': '0', 'enableorderby': '0',
        'forceraster': '0', 'referencescale': '-1'})
    rules = ET.SubElement(renderer, 'rules',
                          {'key': '{%s}' % uuid.uuid4()})
    symbols = ET.SubElement(renderer, 'symbols')

    maker = {'polygon': _fill_symbol, 'line': _line_symbol,
             'point': _marker_symbol}[geometry]

    import copy
    idx = 0
    for value, label, spec in entries:
        if spec is not None:
            spec = copy.copy(spec)
            if not spec.value_label:
                spec.value_label = str(label or value)
        if spec is None:
            # Kutuphanede karsiligi olmasa da sinif adi bilgi tasir:
            # yol derecesi ya da arazi kullanimi deseni buradan cikarilabilir
            spec = RuleSpec()
            spec.stroke = '#646464'
            spec.value_label = str(label or value)
            kind, color = pattern_for(spec.value_label)
            if kind:
                spec.fill = color
                spec.hatch = kind != 'duz'
        spec.layer_key = layer_name or spec.layer_key
        attrs = {'symbol': str(idx), 'label': label or str(value),
                 'key': '{%s}' % uuid.uuid4(),
                 'filter': '%s = %s' % (_quote_field(field), _quote(value))}
        if spec.max_scale:
            attrs['scalemaxdenom'] = str(int(spec.max_scale))
        ET.SubElement(rules, 'rule', attrs)
        maker(symbols, idx, spec)
        idx += 1

    # eslesmeyenler icin "diger" kurali
    other = RuleSpec()
    other.stroke = '#969696'
    ET.SubElement(rules, 'rule', {
        'symbol': str(idx), 'label': 'diger', 'key': '{%s}' % uuid.uuid4(),
        'filter': 'ELSE'})
    maker(symbols, idx, other)

    if layer_name:
        ET.SubElement(qgis, 'layerGeometryType').text = {
            'point': '0', 'line': '1', 'polygon': '2'}[geometry]

    _indent(qgis)
    tree = ET.ElementTree(qgis)
    with open(path, 'wb') as fh:
        fh.write(b"<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n")
        tree.write(fh, encoding='utf-8', xml_declaration=False)
    return path


def _quote_field(name):
    return '"%s"' % name.replace('"', '""')


def _indent(elem, level=0):
    pad = '\n' + '  ' * level
    if len(elem):
        if not (elem.text or '').strip():
            elem.text = pad + '  '
        for child in elem:
            _indent(child, level + 1)
        if not (elem[-1].tail or '').strip():
            elem[-1].tail = pad
    if level and not (elem.tail or '').strip():
        elem.tail = pad


PLAN_ORDER = {'NIP': ('NIP', 'CDP', 'UIP', 'MNIP', 'MUIP'),
              'UIP': ('UIP', 'MUIP', 'NIP', 'CDP'),
              'CDP': ('CDP', 'NIP', 'UIP')}

_SLD_DIR_CACHE = {}


def bundled_library_dir():
    """Eklentiyle birlikte gelen stil kutuphanesi klasoru (varsa).

    Dagitim paketinde eklentinin icine `eplan/` klasoru konur:
        mxd2qgis/eplan/styles/*.sld
        mxd2qgis/eplan/TaramaResim/*.png
        mxd2qgis/eplan/fonts/*.ttf
    Boylece eklenti baska bir bilgisayara tasindiginda kutuphane yolu
    ayarlamak gerekmez.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ('eplan', 'eplan2026'):
        path = os.path.join(here, name)
        if os.path.isdir(path) and find_sld_dirs(path):
            return path
    return None


def find_sld_dirs(root):
    """Kok altinda .sld iceren klasorleri (dosya sayisiyla) bulur."""
    key = os.path.abspath(root)
    if key in _SLD_DIR_CACHE:
        return _SLD_DIR_CACHE[key]
    found = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith('__')]
        count = sum(1 for f in files if f.lower().endswith('.sld'))
        if count:
            found.append((count, dirpath))
    found.sort(reverse=True)
    _SLD_DIR_CACHE[key] = found
    return found


def discover_libraries(root, plan_type='NIP', strict=False):
    """Stil kokunden plan turune gore oncelik sirali StyleLibrary listesi.

    Iki yerlesimi de destekler:
      * NiP / UiP / CDP alt klasorleri (eski dagitim)
      * tum SLD'lerin tek klasorde oldugu, adlarin NIP_/UIP_/CDP_ ile
        basladigi yerlesim (e-Plan 2026 gs-data/workspaces/eplan/styles)
    Tarama gorselleri (TaramaResim) varsa otomatik bulunup baglanir.

    strict=True ise SADECE verilen plan kademesinin on eki kullanilir
    (kullanici kademeyi acikca sectiginde baska kademeye dusulmemeli).
    """
    plan = str(plan_type).upper()
    order = (plan,) if strict else PLAN_ORDER.get(plan, PLAN_ORDER['NIP'])
    dirs = find_sld_dirs(root)
    if not dirs:
        return []

    image_dir = find_image_dir(root)
    libs = []

    # 1) Plan turu adini tasiyan klasorler (NiP, UiP, CDP)
    by_name = {}
    for _count, path in dirs:
        by_name.setdefault(os.path.basename(path).upper(), path)
    for prefix in order:
        path = by_name.get(prefix)
        if path:
            lib = StyleLibrary(path, image_dir=image_dir)
            if lib.rules:
                libs.append(lib)
    if libs:
        return libs

    # 2) Duz yerlesim: en zengin klasoru dosya adi on ekine gore bol
    _count, flat = dirs[0]
    for prefix in order:
        lib = StyleLibrary(flat, prefixes=[prefix + '_'], image_dir=image_dir)
        if lib.rules:
            libs.append(lib)
    if not libs and not strict:
        lib = StyleLibrary(flat, image_dir=image_dir)
        if lib.rules:
            libs = [lib]
    return libs


def match_in(libraries, value):
    """Birden fazla kutuphaneyi oncelik sirasiyla dener.

    Ilk kutuphane plan turune uygun olan (ornek NiP) olmalidir; bulunamazsa
    diger plan turleri (CDP/UiP) yedek olarak kullanilir.
    """
    if not isinstance(libraries, (list, tuple)):
        libraries = [libraries]
    for i, lib in enumerate(libraries):
        spec, score, how = lib.match(value)
        if spec is not None:
            if i:
                how = '%s (%s)' % (how, os.path.basename(lib.root.rstrip('/\\')))
                score = max(0.4, score - 0.1)   # farkli plan turu: guven dusur
            return spec, score, how
    return None, 0.0, 'eslesme_yok'


def match_layer_style(libraries, table_name):
    """Katman/tablo adini kutuphane dosya adiyla eslestirir.

    Deger duzeyinde eslesme mumkun olmadiginda (lejant alani yok ya da alan
    koy adi gibi sinif disi veri tutuyor) katmana tek sembol uygulamak icin
    kullanilir. Donus: (RuleSpec, guven, yontem)
    """
    if not isinstance(libraries, (list, tuple)):
        libraries = [libraries]
    # SDE nitelikli adlar: 'deneme.planuretim.UIP_MAHALLESINIRI' -> son parca
    table_name = str(table_name or '').split('.')[-1]
    want = _strip_prefix(normalize(table_name))
    if not want:
        return (None, 0.0, 'gecersiz')

    # Sinonim varsa aramayi onun uzerinden yap (once dosya adi, sonra kural)
    synonym = SYNONYMS.get(want) or SYNONYMS.get(want.replace('_', ''))
    tag = ''
    if synonym:
        want = normalize(synonym)
        tag = 'sinonim+'
    # MDB tablo adlari birlesik yazilir (MUCAVIRALANSINIRI), kutuphane
    # dosyalari ayrik (MUCAVIR_ALAN_SINIRI) -> alt cizgileri silip karsilastir
    want_sq = want.replace('_', '')
    want_sq_base = _strip_suffix(want).replace('_', '')

    for i, lib in enumerate(libraries):
        by_file = {}
        for spec in lib.rules:
            by_file.setdefault(_strip_prefix(normalize(spec.source)),
                               []).append(spec)

        penalty = 0.1 if i else 0.0
        cands = []
        for fkey, specs in by_file.items():
            if not fkey:
                continue
            f_sq = fkey.replace('_', '')
            f_sq_base = _strip_suffix(fkey).replace('_', '')
            if want_sq == f_sq:
                return (_layer_spec(specs), 0.95 - penalty, tag + 'katman_adi')
            if want_sq_base and want_sq_base == f_sq_base:
                return (_layer_spec(specs), 0.9 - penalty,
                        tag + 'katman_adi_sonek')
            if want_sq.startswith(f_sq) or f_sq.startswith(want_sq):
                ratio = min(len(want_sq), len(f_sq)) / float(
                    max(len(want_sq), len(f_sq)))
                if ratio >= 0.6:
                    cands.append((ratio, 'katman_adi_kismi', specs))
                    continue
            # Ortak on ek orani (IMARHAKAKTARIMALANI ~ IMARHAKAKTARIMSINIR)
            common = 0
            for a, b in zip(want_sq, f_sq):
                if a != b:
                    break
                common += 1
            if common >= 8:
                ratio = common / float(max(len(want_sq), len(f_sq)))
                if ratio >= 0.7:
                    cands.append((ratio, 'katman_adi_onek', specs))
        if cands:
            cands.sort(key=lambda c: c[0], reverse=True)
            ratio, how, specs = cands[0]
            return (_layer_spec(specs), round(0.85 * ratio - penalty, 2),
                    tag + how)

        # Dosya adi tutmadi: katman adini kural basliklariyla dene
        # (ornek NIP25_AFETEMARUZBOLGE -> NIP_AFET_TEHLIKELI_ALANLAR icindeki
        #  AFETE_MARUZ_BOLGE kurali)
        spec, score, how = lib.match(want)
        if spec is not None:
            return (spec, round(max(0.4, score - 0.05 - penalty), 2),
                    tag + 'kural_basligi:' + how)

        wt = _tokens(want)
        if wt:
            scored = []
            for fkey, specs in by_file.items():
                ft = _tokens(fkey)
                if not ft:
                    continue
                inter = len(wt & ft)
                if inter:
                    scored.append((inter / float(len(wt | ft)), specs))
            if scored:
                scored.sort(key=lambda x: x[0], reverse=True)
                if scored[0][0] >= 0.5:
                    return (_layer_spec(scored[0][1]),
                            round(scored[0][0] - penalty, 2),
                            tag + 'katman_belirtec')
    return (None, 0.0, 'eslesme_yok')


def _strip_prefix(key):
    return re.sub(r'^(M?NIP|M?UIP|CDP)\d*_?', '', key).strip('_')


def _layer_spec(specs):
    """Bir dosyanin kurallari arasindan katmani temsil edeni sec."""
    for spec in specs:
        if normalize(spec.title) == _strip_prefix(normalize(spec.source)):
            return spec
    return StyleLibrary._pick(specs)


def write_single_qml(path, spec, geometry='polygon', layer_name=''):
    """Tek sembollu QML yazar."""
    if spec is not None:
        import copy
        spec = copy.copy(spec)
        spec.layer_key = layer_name or spec.layer_key
    qgis = ET.Element('qgis', {
        'version': '3.34.0', 'styleCategories': 'Symbology',
        'labelsEnabled': '0', 'readOnly': '0', 'minScale': '100000000',
        'maxScale': '0', 'hasScaleBasedVisibilityFlag': '0',
        'symbologyReferenceScale': '-1'})
    renderer = ET.SubElement(qgis, 'renderer-v2', {
        'type': 'singleSymbol', 'symbollevels': '0', 'enableorderby': '0',
        'forceraster': '0', 'referencescale': '-1'})
    symbols = ET.SubElement(renderer, 'symbols')
    maker = {'polygon': _fill_symbol, 'line': _line_symbol,
             'point': _marker_symbol}[geometry]
    maker(symbols, 0, spec or RuleSpec())
    _indent(qgis)
    with open(path, 'wb') as fh:
        fh.write(b"<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n")
        ET.ElementTree(qgis).write(fh, encoding='utf-8', xml_declaration=False)
    return path


def build_entries(library, values, labels=None):
    """Deger listesini kutuphaneyle eslestirip QML girdileri uretir.

    library: StyleLibrary ya da oncelik sirali StyleLibrary listesi
    Donus: (entries, rapor)
    """
    import copy
    entries = []
    report = []
    for value in values:
        label = (labels or {}).get(value, value)
        spec, score, how = match_in(library, label)
        if spec is not None:
            # Kutuphane nesnesini bozmadan, eslesen degeri sembol ureticisine
            # tasiyacak bir kopya kullan (yol derecesi/desen secimi icin)
            spec = copy.copy(spec)
            spec.value_label = str(label)
        entries.append((value, str(label), spec))
        if spec is None:
            note = ''
        elif spec.hatch_path:
            note = 'gercek_desen'
        elif spec.hatch:
            note = 'tarama_yedek'
        else:
            note = ''
        report.append((value, label,
                       spec.source if spec else '', spec.title if spec else '',
                       score, how, note))
    return entries, report
