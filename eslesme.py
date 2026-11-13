# -*- coding: utf-8 -*-
"""NCZ katman adi -> e-Plan (Mekansal Planlar) gosterim kurali.

Kaynak yalniz eklentiyle gelen e-Plan SLD kutuphanesi (eplan/) ve asagidaki
KENDI eslesme tablomuzdur. Disaridan hicbir sablon/lejant dosyasi okunmaz.

Zincir:
  PL_KONUT_GEL_DUSUK -> on ek soyulur -> KONUT_GEL_DUSUK
    -> TAKMA_AD (varsa)  -> ['DUSUK_51_120HA', 'GELISME_KONUT']
    -> e-Plan kural basligi / dosya adi eslesmesi (eplan_style)
"""
import os
import re

from . import eplan_style as E

EKLENTI_DIR = os.path.dirname(os.path.abspath(__file__))
KUTUPHANE = os.path.join(EKLENTI_DIR, "eplan")
KADEMELER = ("UIP", "NIP", "CDP")
KADEME_ADI = {"UIP": u"Uygulama İmar Planı", "NIP": u"Nazım İmar Planı",
              "CDP": u"Çevre Düzeni Planı"}

ON_EK = re.compile(r"^(PL|SNR|HAT|KA|KST|OA|SM|AL)_")

# Otomatik eslesmenin bulamadigi ya da yanlis buldugu siniflar.
# Anahtar: on eki soyulmus, normalize katman adi. Deger: denenecek e-Plan kural
# basliklari / dosya adlari (sirayla; ilk bulunan kullanilir, kademeden bagimsiz).
TAKMA_AD = {
    # kentsel calisma
    "BHA": ["BELEDIYE_HIZMET_ALANI"],
    "KHA": ["KAMU_HIZMET_ALANI", "RESMI_KURUM_ALANI"],
    "KDKCA": ["KONUT_DISI_KENTSEL_CALISMA_ALANI"],
    "DEPOLAMA": ["DEPOLAMA_ALANI"],
    "ENDUSTRIYEL_GEL": ["ENDUSTRIYEL_GELISME_BOLGESI"],
    "TOPLU_ISYERI": ["TOPLU_ISYERLERI", "TOPLU_ISYERI"],
    "TOPLU_ISYERLERI": ["TOPLU_ISYERLERI", "TOPLU_ISYERI"],
    "BAKIM_AKARYAKIT": ["AKARYAKIT_SERVIS_ISTASYONU_ALANI", "AKARYAKIT_SERVIS_ISTASYONU"],
    "AKARYAKIT": ["AKARYAKIT_SERVIS_ISTASYONU_ALANI", "AKARYAKIT_SERVIS_ISTASYONU"],
    "TOPTAN_TICARET": ["TOPTAN_TICARET_ALANI"],
    "ENERJI_URETIM": ["ENERJI_URETIM"],
    "TEKNIK_ALTYAPI": ["TEKNIK_ALTYAPI"],
    "OTOPARK": ["GENEL_OTOPARK"],
    # konut (NIP yogunluk kurallari; UIP'de tek GELISME/YERLESIK_KONUT)
    "KONUT_GEL_SEYREK": ["SEYREK_50HA_ALTINDA", "GELISME_KONUT"],
    "KONUT_GEL_DUSUK": ["DUSUK_51_120HA", "GELISME_KONUT"],
    "KONUT_GEL_ORTA": ["ORTA_121_250HA", "GELISME_KONUT"],
    "KONUT_GEL_YUKSEK": ["YUKSEK_251_400HA", "GELISME_KONUT"],
    "KONUT_GEL_COK_YUKSEK": ["COK_YUKSEK_401HA_USTUNDE", "GELISME_KONUT"],
    "KONUT_MEV_SEYREK": ["NIP_MEVCUT_KONUT", "YERLESIK_KONUT"],
    "KONUT_MEV_DUSUK": ["DUSUK_51_151HA", "YERLESIK_KONUT"],
    "KONUT_MEV_ORTA": ["ORTA_151_300HA", "YERLESIK_KONUT"],
    "KONUT_MEV_YUKSEK": ["YUKSEK_301_600HA", "YERLESIK_KONUT"],
    "EMSALKONUT": ["YERLESIK_KONUT", "GELISME_KONUT"],
    "KONUT": ["YERLESIK_KONUT", "GELISME_KONUT"],
    # tarim / yesil
    "DIKILI_TARIM": ["TARIM_ALANI"],
    "MUTLAK_TARIM": ["TARIM_ALANI"],
    "OZEL_URUN": ["TARIM_ALANI"],
    "SULU_TARIM": ["TARIM_ALANI"],
    "MARJINAL_TARIM": ["TARIM_ALANI"],
    "TARIMSAL_ALAN": ["TARIM_ALANI"],
    "ZEYTINLIK": ["ZEYTINLIK"],
    "MERA_ALANI": ["MERA"],
    "ORMAN_ALANI": ["ORMAN"],
    # sit
    "1DER_ARK_SIT": ["1_DERECE_ARKEOLOJIK_SIT"],
    "2DER_ARK_SIT": ["2_DERECE_ARKEOLOJIK_SIT"],
    "3DER_ARK_SIT": ["3_DERECE_ARKEOLOJIK_SIT"],
    "1DER_DOG_SIT": ["1_DERECE_DOGAL_SIT"],
    "2DER_DOG_SIT": ["2_DERECE_DOGAL_SIT"],
    "3DER_DOG_SIT": ["3_DERECE_DOGAL_SIT"],
    "KENTSEL_SIT": ["KENTSEL_SIT"],
    # sinirlar
    "PLANONAMA": ["PLAN"],
    "PLAN_ONAMA": ["PLAN"],
    "PLAN_DEGISIKLIGI": ["PLAN_DEGISIKLIK_SINIRI"],
    "GOB": ["GECEKONDU_ONLEME_BOLGESI"],
    "YAPIYAK": ["YAPI_YAKLASMA_SINIRI"],
    "ONLEMLI_ALAN": ["ONLEMLI_ALAN"],
    # yollar (eplan_style yol kesitleri)
    "1DER_YOL": ["@1_DERECE_YOL"],
    "2DER_YOL": ["@2_DERECE_YOL"],
    "3DER_YOL": ["@3_DERECE_YOL"],
    "KOY_YOLU": ["@KOY_YOLU"],
    "OTOYOL": ["@OTOYOL"],
    "DEMIRYOLU_PLAN": ["DEMIRYOLU"],
    "DOGALGAZ_BORU_HA": ["DOGALGAZ_BORU_HATTI"],
    "ENERJI_NAKIL": ["ENERJI_NAKIL_HATTI"],
}

# Altlik / yol geometrisi: e-Plan'a degil dosyanin kendi rengine gore cizilir (Netcad
# gorunumu). Deger: cizgi kalinligi (mm). Ada kenari kalin, kaldirim/refuj ince.
DOSYA_CIZGI = (
    (re.compile(r"^ADA_?KENARI"), 0.50),
    (re.compile(r"^(YOL_)?PLATFORM"), 0.25),
    (re.compile(r"^KALDIRIM"), 0.13),
    (re.compile(r"^REFUJ"), 0.13),
    (re.compile(r"^YAYA_?YOL"), 0.13),
    (re.compile(r"^YOL_EKSEN"), 0.13),
    (re.compile(r"^(PARSEL|KADASTRO|BINA)"), 0.13),
)


def dosya_cizgi_mm(katman_adi):
    """Altlik cizgisi ise kalinlik (mm), degilse None."""
    c = E.normalize(katman_adi or "")
    for rx, mm in DOSYA_CIZGI:
        if rx.match(c):
            return mm
    return None


# Bu katmanlar e-Plan'la eslestirilmez (lejant kutusu, pafta, yardimci)
ATLA = re.compile(r"^(LJ_|@LJ|PINDEX|PAFTA|BPAFTA|KPAFTA|PFT_|GRID|CIZPEN|HESAP|KST_YAZI)")

_libs = {}
_fontlar = [False]


def cekirdek(ad):
    return ON_EK.sub("", E.normalize(ad or ""))


def kutuphane(kademe):
    if kademe not in _libs:
        _libs[kademe] = E.discover_libraries(os.path.join(KUTUPHANE, "styles"), kademe, strict=True)
        for lib in _libs[kademe]:
            lib.image_dir = os.path.join(KUTUPHANE, "TaramaResim")
            for spec in lib.rules:
                if spec.hatch_image:
                    p = os.path.join(lib.image_dir, spec.hatch_image)
                    spec.hatch_path = p if os.path.exists(p) else None
    return _libs[kademe]


def fontlari_yukle():
    """e-Plan TTF fontlarini QGIS oturumuna yukler (sisteme kurulmaz)."""
    if _fontlar[0]:
        return
    _fontlar[0] = True
    try:
        from qgis.PyQt.QtCore import QByteArray
        from qgis.PyQt.QtGui import QFontDatabase
    except ImportError:
        return
    d = os.path.join(KUTUPHANE, "fonts")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.lower().endswith((".ttf", ".otf")):
            # dosya yolundan degil bellekten: Windows yuklu font dosyasini kilitler ve
            # eklenti guncellenirken uzerine yazilamaz ("paketi cikartma basarisiz")
            try:
                with open(os.path.join(d, f), "rb") as fh:
                    veri = fh.read()
                QFontDatabase.addApplicationFontFromData(QByteArray(veri))
            except Exception:  # nosec B112 - okunamayan font atlanir
                continue
    try:
        E.AVAILABLE_FONTS = set(QFontDatabase().families())
    except Exception:
        E.AVAILABLE_FONTS = None


def bul(katman_adi, kademe):
    """(RuleSpec, yontem) ya da (None, neden)."""
    if not katman_adi or ATLA.match(E.normalize(katman_adi)):
        return None, "atlandi"
    if dosya_cizgi_mm(katman_adi) is not None:
        return None, "dosya cizgisi"
    libs = kutuphane(kademe)
    if not libs:
        return None, "kutuphane yok"
    c = cekirdek(katman_adi)
    for hedef in TAKMA_AD.get(c, []):
        if hedef.startswith("@"):            # yalniz cizgi kesiti (eplan_style.LINE_RULES)
            sp = E.RuleSpec()
            sp.source, sp.title, sp.geom = "yol", hedef[1:], "line"
            return sp, "yol kesiti"
        for lib in libs:
            if hedef in lib.by_key:
                return lib._pick(lib.by_key[hedef]), "takma ad"
        sp, sk, how = E.match_layer_style(libs, hedef)
        if sp is not None and sk >= 0.85:
            return sp, "takma ad/dosya"
    sp, sk, how = E.match_in(libs, c)
    if sp is not None and sk >= 0.5:
        return sp, how
    sp, sk, how = E.match_layer_style(libs, c)
    if sp is not None and sk >= 0.6:
        return sp, how
    return None, "eslesme yok"


def kademe_sec(dosya, yol, tercih=None):
    """UIP/NIP/CDP. Tercih > dosya meta adi > dosya adi > en cok eslesen."""
    if tercih in KADEMELER:
        return tercih
    metin = (dosya.meta_metin("GISWIZ") or "") + " " + os.path.basename(yol)
    m = re.search(r"(UIP|NIP|CDP)", E.normalize(metin))
    if m:
        return m.group(1)
    adlar = [k.ad for k in dosya.katmanlar if k.ad.upper().startswith("PL_")]
    en, puan = "UIP", -1
    for kd in KADEMELER:
        p = sum(1 for a in adlar if bul(a, kd)[0] is not None)
        if p > puan:
            en, puan = kd, p
    return en


# NCZ'nin kendi cizgi tipi ADI -> e-Plan cizgi kurali (kademe oneki eklenir).
# Netcad katmana atanmis cizgi tipini (END_GEL_14, ONL_ALN-14 ...) ciziyor; katman adi
# e-Plan'da cizgi karsiligi vermiyorsa (PL_ENDUSTRIYEL_GEL sinirlari gibi) bu ad kullanilir.
# "{K}" kademe adiyla doldurulur; "{1}" ilk yakalanan gruptur.
CIZGI_TIPI_KURAL = (
    # e-Plan'da karsiligi yok (sanayi siniflarinin glifi disli cark); Netcad gibi ikili daire
    (r"END_?GEL", "*", "IKILI_DAIRE"),
    (r"^OSB", "ILAN_EDILEN_CLSMA_ALAN", "OSB"),
    (r"TGB|TEKNO", "ILAN_EDILEN_CLSMA_ALAN", "TEKNOLOJI_GELISTIRME_BOLGESI"),
    (r"ONL", "ONLEMLI_ALAN", "ONLEMLI_ALAN"),
    (r"GECEK|GOB", "DONUSUM_KONUT_ALANLARI", "GECEKONDU_ONLEME_BOLGESI"),
    (r"KNT_?DON|KENTSEL_?DON", "DONUSUM_KONUT_ALANLARI", "KENTSEL_DONUSUM_PROJE_ALANI"),
    (r"ILCE", "ILCE_SINIRI", "{K}_ILCE_SINIRI"),
    (r"(\d)_?ARK", "SIT_ALANLARI", "{1}_DERECE_ARKEOLOJIK_SIT"),
    (r"(\d)_?DOG", "SIT_ALANLARI", "{1}_DERECE_DOGAL_SIT"),
    (r"DEMI?R", "DEMIRYOLU", "DEMIRYOLU"),
    (r"BOR_?HAT|BORU", "BORU_HATTI", "DOGALGAZ_BORU_HATTI"),
    (r"^ENH|ENERJI", "ENERJI_NAKIL_HATTI", "{K}_ENERJI_NAKIL_HATTI"),
    (r"PLN_?DE|PLAN_?DE", "PLAN_DEGISIKLIK_SINIRI", "{K}_PLAN_DEGISIKLIK_SINIRI"),
    (r"ONAMA", "PLAN_SINIRI", "PLAN"),
)


def _ascii(s):
    tr = {u"Ç": "C", u"Ğ": "G", u"İ": "I", u"I": "I", u"Ö": "O", u"Ş": "S", u"Ü": "U",
          u"ç": "C", u"ğ": "G", u"ı": "I", u"i": "I", u"ö": "O", u"ş": "S", u"ü": "U"}
    return "".join(tr.get(c, c) for c in (s or "")).upper()


def cizgi_tipi_kurali(lt_ad, kademe):
    """NCZ cizgi tipi adi -> (e-Plan kaynak, kural basligi) ya da None."""
    from . import eplan_cizgi
    ad = _ascii(lt_ad)
    if not ad or ad == "DUZ":
        return None
    for desen, kaynak, baslik in CIZGI_TIPI_KURAL:
        m = re.search(desen, ad)
        if not m:
            continue
        if kaynak == "*":
            return kaynak, baslik          # eplan_cizgi.OZEL_CIZGILER (kendi tanimimiz)
        for kd in (kademe, "UIP", "NIP"):
            src = "%s_%s" % (kd, kaynak)
            b = baslik.replace("{K}", kd)
            if m.groups():
                b = b.replace("{1}", m.group(1))
            if eplan_cizgi.kural_cizgileri(src, b):
                return src, b
        return None
    return None
