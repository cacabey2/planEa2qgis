# -*- coding: utf-8 -*-
"""Akilli nesneler (Netcad modullerinin NCZ'ye yazdigi ozellik cantasi).

Bilinen siniflar (planEa olcumleri):
  963f3889...  SM_YOL      : genislik, yolTuru
  ec66d03e...  yapilasma   : emsal, taks, kaks, hmax, yEncok + chk<Ad>IsNull bayraklari,
                             numberOfDecimalPlace (ondalik hane)
  7c3f9a1e...  yapilasma   : Emsal, YencokKat (eski/sade sema)

Netcad yalniz "bos degil" isaretli degerleri yazar: chk<Ad>IsNull == "True" ise o deger
gosterilmez (dosyada "0" yazsa bile).
"""

# (etiket, olasi ozellik adlari, bos bayragi, birim)
YAPILASMA = (
    ("E", ("emsal", "Emsal", "E", "emsalDegeri", "EmsalDeger"), "chkEmsalIsNull", ""),
    ("TAKS", ("taks", "Taks", "TAKS"), "chkTaksIsNull", ""),
    ("KAKS", ("kaks", "Kaks", "KAKS"), "chkKaksIsNull", ""),
    ("Hmax", ("hmax", "Hmax", "HMAX"), "chkHmaxIsNull", " m"),
    ("Yençok", ("yEncok", "YencokKat", "yencok", "Yencok", "KatAdedi", "katSayisi"),
     "chkYEnCokIsNull", " Kat"),
)

ALAN_SUTUNLARI = ("emsal", "taks", "kaks", "hmax", "yencok")


def _kucuk(oz):
    """Ozellik adlari harf duyarsiz: {'emsal': ('Emsal', '0.5'), ...}"""
    return {str(k).lower(): (k, v) for k, v in (oz or {}).items()}


def _al(oz, adlar):
    kz = _kucuk(oz)
    for a in adlar:
        kv = kz.get(a.lower())
        if kv and kv[1] not in (None, ""):
            return kv[1]
    return None


def _bos_mu(oz, chk):
    """chk<Ad>IsNull bayragi (harf duyarsiz). Yoksa None."""
    kv = _kucuk(oz).get(chk.lower())
    if kv is None:
        return None
    return str(kv[1]).strip().lower() in ("true", "1", "evet")


def _sayi(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def yapilasma(oz):
    """Ozellik cantasindan {'emsal': 0.5, ...} ve Netcad bicimli etiket metni.
    Yapilasma nesnesi degilse (None, None)."""
    if not oz:
        return None, None
    if not any(_al(oz, adlar) is not None for _e, adlar, _c, _b in YAPILASMA):
        return None, None
    try:
        nd = int(_al(oz, ("numberOfDecimalPlace",)) or "2")
    except ValueError:
        nd = 2
    nd = max(0, min(4, nd))
    degerler, satirlar = {}, []
    for (etiket, adlar, chk, birim), sutun in zip(YAPILASMA, ALAN_SUTUNLARI):
        v = _al(oz, adlar)
        if v is None:
            continue
        bos = _bos_mu(oz, chk)
        if bos:
            continue                       # Netcad: bu deger bos isaretli
        s = _sayi(v)
        if bos is None and (s is None or s == 0):
            continue                       # bayraksiz semada 0 = yok
        degerler[sutun] = s if s is not None else v
        if s is None:
            metin = str(v)
        elif sutun == "yencok":
            metin = ("%g" % s) if s != int(s) else "%d" % s
        else:
            metin = "%.*f" % (nd, s)
        satirlar.append(u"%s=%s%s" % (etiket, metin, birim) if etiket != u"Yençok"
                        else u"Yençok= %s%s" % (metin, birim))
    if not satirlar:
        return None, None
    return degerler, u"\n".join(satirlar)


# etiket icin anlamsiz, teknik ozellikler
_TEKNIK = ("chk", "is", "version", "type", "choice", "numberof", "min")


def genel_etiket(oz):
    """Taninmayan akilli nesne: dolu ve sayisal olmayan-sifir ozellikleri 'ad=deger' yazar."""
    satir = []
    for k, v in (oz or {}).items():
        kl = str(k).lower()
        if v in (None, "") or any(kl.startswith(t) for t in _TEKNIK):
            continue
        sv = _sayi(v)
        if sv == 0:
            continue
        satir.append(u"%s=%s" % (k, v))
    return u"\n".join(satir[:4]) if satir else None


def yol_genisligi(oz):
    if not oz:
        return None
    v = oz.get("genislik")
    return v if v not in (None, "") else None
