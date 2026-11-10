# -*- coding: utf-8 -*-
"""Netcad NCZ okuyucu — saf Python (planEa NczDosyasi.cs portu).

Koordinat kurali: x = DOGU, y = KUZEY. Netcad diskte once kuzeyi yazar.
Disaridan bagimlilik yok (yalniz struct/uuid/zlib).
"""
import struct
import uuid

_U32 = struct.Struct('<I').unpack_from
_I32 = struct.Struct('<i').unpack_from
_I16 = struct.Struct('<h').unpack_from
_U16 = struct.Struct('<H').unpack_from
_F64 = struct.Struct('<d').unpack_from
_F32 = struct.Struct('<f').unpack_from

# Nesne turleri (NMath.Cases)
NOKTA, CIZGI, DAIRE, YAY, YAZI, SEMBOL, PLINE, SPIRAL, ESYUK, DIKD, PAFTA, UCGEN, BLOK, ISARET, OZEL = range(1, 16)
TUR_ADI = {1: 'nokta', 2: 'cizgi', 3: 'daire', 4: 'yay', 5: 'yazi', 6: 'sembol', 7: 'pline',
           8: 'spiral', 9: 'esyukselti', 10: 'dikdortgen', 11: 'pafta', 12: 'ucgen', 13: 'blok',
           14: 'akilli', 15: 'akilli'}

# PLine bayraklari
P_KAPALI, P_DOLU, P_ADLI = 1, 2, 16

_YARDIMCI = {0x10, 0x0f, 0x18, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x22, 0x23}


def cp1254(b):
    try:
        return b.decode('cp1254', 'replace')
    except Exception:
        return b.decode('latin-1', 'replace')


class Katman(object):
    __slots__ = ('sira', 'ad', 'ozellik', 'renk', 'cizgi_tipi', 'cizim_rengi', 'tarama', 'stil')

    def __init__(self):
        self.stil = None

    @property
    def acik(self):
        return (self.ozellik & 1) != 0


class Stil(object):
    """LEX.ST2 katman stili (NcApi.TStyleRecord, 256 bayt)."""
    __slots__ = ('olcek_etkin', 'olcek_bas', 'olcek_son', 'kenar', 'renk', 'renk_rgb',
                 'cizgi_tipi', 'kalinlik', 'doku_id', 'doku_aci', 'doku_olcek', 'duz_dolgu',
                 'cizgi_rengi', 'saydamlik', 'renk_modu')

    @property
    def dolgu_var(self):
        return (self.duz_dolgu & 0x7F) != 0 or self.doku_id is not None


class Nesne(object):
    __slots__ = ('tur', 'katman', 'x', 'y', 'z', 'renk', 'kalinlik', 'lt', 'koseler', 'bayrak',
                 'ad', 'sinif', 'nesne_adi', 'metin', 'boy', 'aci', 'hiza', 'font',
                 'sembol_no', 'sembol_kut', 'sembol_olcek', 'yaricap', 'akilli_sinif',
                 'ozellikler', 'konum', 'sinir')

    def __init__(self):
        self.koseler = None
        self.bayrak = 0
        self.ad = self.sinif = self.nesne_adi = self.metin = None
        self.ozellikler = None
        self.akilli_sinif = None

    @property
    def kapali(self):
        return bool(self.bayrak & P_KAPALI)

    @property
    def dolu(self):
        return bool(self.bayrak & P_DOLU)


class NczDosyasi(object):
    def __init__(self, veri):
        self.d = veri
        self.N = len(veri)
        self.katmanlar = []
        self.cizgi_tipleri = []   # [(ad, desen)]
        self.meta = {}
        self.nesneler = []
        self.surum = None
        self.proj = {}
        self.uyarilar = []
        self.senkron = 0
        self._bolge = None
        self._coz()
        self.d = None

    @classmethod
    def oku(cls, yol):
        with open(yol, 'rb') as f:
            return cls(f.read())

    # ------------------------------------------------------------ yardimci
    def _kisa(self, o, kap, sinir):
        if o >= sinir:
            return ''
        n = self.d[o]
        n = min(n, kap, max(0, sinir - o - 1))
        return cp1254(self.d[o + 1:o + 1 + n]).rstrip('\x00')

    def _kutu(self, o):
        n0, e0, n1, e1 = struct.unpack_from('<4d', self.d, o)
        return (min(e0, e1), min(n0, n1), max(e0, e1), max(n0, n1))

    # ------------------------------------------------------------ cozum
    def _coz(self):
        d = self.d
        if self.N < 128 or d[0] != 1:
            raise ValueError(u'NCZ imzasi yok')
        self.baslik_kapsam = self._kutu(49)
        kp = _U32(d, 13)[0]
        if 0 < kp < self.N - 5 and d[kp] == 0x06:
            self._katmanlar(kp + 5, _U32(d, kp + 1)[0])

        nesne_bolumu = -1
        off = 125
        while off + 5 <= self.N:
            t = d[off]
            sz = _U32(d, off + 1)[0]
            if off + 5 + sz > self.N:
                break
            p = off + 5
            if t == 0x19 and sz >= 1 and d[p] > 0:
                self.surum = d[p + 1:p + 1 + d[p]].decode('ascii', 'replace')
            elif t == 0x06 and not self.katmanlar:
                self._katmanlar(p, sz)
            elif t == 0x08:
                self._cizgi_tipleri(p, sz)
            elif t == 0x1c:
                self._meta(p, sz)
            elif t == 0x0d:
                nesne_bolumu = p + sz
            off = p + sz
            if nesne_bolumu >= 0:
                break

        bas = _U32(d, 45)[0]
        if nesne_bolumu < 0 or (0 < bas < self.N and bas != nesne_bolumu and self._gecerli(bas, False)):
            nesne_bolumu = bas if 0 < bas < self.N else off

        self._stiller()
        self._projeksiyon()
        self._nesneler(nesne_bolumu)

    def _katmanlar(self, p, sz):
        d = self.d
        if sz < 13:
            return
        nl = _U16(d, p + 11)[0]
        q, son = p + 13, p + sz
        self.katmanlar = []
        i = 0
        while i < nl and q + 29 <= son:
            k = Katman()
            k.sira = i
            k.ozellik = _I32(d, q)[0]
            k.ad = self._kisa(q + 4, 20, q + 25)
            k.renk = d[q + 25]
            k.cizgi_tipi = struct.unpack_from('<b', d, q + 26)[0]
            k.cizim_rengi = struct.unpack_from('<b', d, q + 27)[0]
            k.tarama = struct.unpack_from('<b', d, q + 28)[0]
            self.katmanlar.append(k)
            i += 1
            q += 29

    def _stiller(self):
        b = self.meta.get('LEX.ST2')
        if not b or len(b) < 8:
            return
        sayi = _I32(b, 4)[0]
        for i in range(min(max(sayi, 0), len(self.katmanlar))):
            o = 8 + i * 256
            if o + 131 > len(b):
                break
            s = Stil()
            s.olcek_etkin = b[o] != 0
            s.olcek_bas = _U32(b, o + 1)[0]
            s.olcek_son = _U32(b, o + 5)[0]
            s.kenar = b[o + 48] != 0
            s.renk = _I32(b, o + 55)[0]
            s.renk_rgb = b[o + 59] != 0
            s.cizgi_tipi = _I16(b, o + 60)[0]
            s.kalinlik = _F64(b, o + 62)[0]
            g = bytes(b[o + 83:o + 99])
            s.doku_id = None if g == b'\x00' * 16 else str(uuid.UUID(bytes_le=g)).upper()
            s.doku_aci = _F64(b, o + 99)[0]
            s.doku_olcek = _F64(b, o + 107)[0]
            s.duz_dolgu = b[o + 115]
            s.cizgi_rengi = _I32(b, o + 116)[0]
            s.saydamlik = b[o + 120]
            s.renk_modu = b[o + 127]
            if not (1e-9 < s.doku_olcek < 1e6):
                s.doku_olcek = 1.0
            if not (0 <= s.kalinlik <= 100):
                s.kalinlik = 0.0
            self.katmanlar[i].stil = s

    def _cizgi_tipleri(self, p, sz):
        d = self.d
        B, R = 43, 219
        self.cizgi_tipleri = []
        if sz < B + R:
            return
        for i in range((sz - B) // R):
            r = p + B + i * R
            nl = d[r + 39]
            if nl == 0 or nl > 10:
                self.cizgi_tipleri.append(('', []))
                continue
            ad = cp1254(d[r + 40:r + 40 + nl]).rstrip('\x00')
            n = min(abs(struct.unpack_from('<b', d, r + 50)[0]), (R - 61) // 4)
            per = _F32(d, r + 51)[0]
            des = list(struct.unpack_from('<%df' % n, d, r + 61)) if n else []
            self.cizgi_tipleri.append((ad, des, per))

    def _meta(self, p, sz):
        d = self.d
        if sz < 1:
            return
        nl = d[p]
        if nl == 0 or nl > 32 or p + 1 + nl > p + sz:
            return
        ad = d[p + 1:p + 1 + nl].decode('ascii', 'replace')
        veri = p + 11 if nl + 1 <= 11 else p + 1 + nl
        self.meta[ad] = d[veri:p + sz]

    def _projeksiyon(self):
        b = self.meta.get('MPROJ')
        if not b or len(b) < 65:
            return
        cm = _U32(b, 5)[0]
        a, bb, k0 = _F64(b, 9)[0], _F64(b, 17)[0], _F64(b, 25)[0]
        fe = _F64(b, 57)[0]
        if 24 <= cm <= 48:
            self.proj['dom'] = cm
        if 'dom' in self.proj and 6.3e6 < a < 6.4e6 and 6.3e6 < bb < a and 0.9 < k0 <= 1.01:
            self.proj.update(a=a, b=bb, k0=k0, fe=fe if 0 < fe < 1e8 else 500000.0)

    # ------------------------------------------------------------ nesneler
    def _gecerli(self, k, siki):
        d = self.d
        if k < 0 or k + 5 > self.N:
            return False
        t = d[k]
        nesne = t in (0x15, 0x16, 0x21, 0x17)
        if not nesne and (siki or t not in _YARDIMCI):
            return False
        sz = _U32(d, k + 1)[0]
        if k + 5 + sz > self.N:
            return False
        if not nesne:
            return sz < (1 << 24)
        if t in (0x15, 0x16):
            if sz < 77:
                return False
            k0, k1 = d[k + 5], d[k + 6]
            yeni = k0 != 0 and k0 <= 0x20 and k1 == k0
            eski = k0 == 0 and k1 != 0 and k1 <= 0x20
            if not (yeni or eski):
                return False
            if siki:
                p = k + 5
                ky, kx = _F64(d, p + 3)[0], _F64(d, p + 11)[0]
                by, bx = _F64(d, p + 45)[0], _F64(d, p + 53)[0]
                if not self._makul(kx, ky) and not self._makul(bx, by):
                    return False
        return True

    def _makul(self, x, y):
        b = self.baslik_kapsam
        w, h = b[2] - b[0], b[3] - b[1]
        if not (w > 0 and h > 0):
            return x == x and y == y and abs(x) < 1e8 and abs(y) < 1e8 and (x != 0 or y != 0)
        pay = max(500.0, w, h)
        return b[0] - pay <= x <= b[2] + pay and b[1] - pay <= y <= b[3] + pay

    def _senkron(self, bas):
        d = self.d
        k = max(bas, 0)
        while k < self.N - 5:
            if self._gecerli(k, True):
                t = d[k]
                if t in (0x15, 0x16) and d[k + 6] in (0x0f, 0x0e):
                    return k
                sonraki = k + 5 + _U32(d, k + 1)[0]
                if sonraki == self.N or self._gecerli(sonraki, False):
                    return k
            k += 1
        return -1

    def _nesneler(self, off):
        d = self.d
        N = self.N
        while off + 5 <= N:
            t = d[off]
            sz = _U32(d, off + 1)[0]
            sigar = off + 5 + sz <= N
            if t in (0x15, 0x16) and sigar and sz >= 77:
                off = self._nesne(off, sz)
            elif t == 0x21 and sigar:
                p = off + 5
                if sz >= 8:
                    sl = d[p + 6]
                    if sl > 0 and p + 7 + sl <= p + sz:
                        self._bolge = cp1254(d[p + 7:p + 7 + sl])
                off = p + sz
            elif sigar and sz < (1 << 24) and (t in (0x17, 0x0d) or t in _YARDIMCI) and \
                    (off + 5 + sz == N or self._gecerli(off + 5 + sz, False)):
                off += 5 + sz
            elif sigar and 0 < sz < (1 << 24) and self._gecerli(off + 5 + sz, False) and t < 0x40:
                off += 5 + sz
            else:
                r = self._senkron(off + 1)
                if r < 0:
                    break
                self.senkron += 1
                off = r

    def _nesne(self, off, sz):
        d = self.d
        p = off + 5
        son = p + sz
        tag = d[p + 1] or d[p]
        n = Nesne()
        n.tur = tag if 1 <= tag <= 15 else 255
        n.konum = off
        n.y, n.x = struct.unpack_from('<2d', d, p + 3)
        try:
            n.sinir = self._kutu(p + 45)       # OLimits: Netcad'in cizim kutusu (minx, miny, maxx, maxy)
        except struct.error:
            n.sinir = None
        n.z = _F32(d, p + 19)[0]
        n.renk = d[p + 32]
        n.kalinlik = _F64(d, p + 33)[0]
        if not (abs(n.kalinlik) <= 1000):
            n.kalinlik = 0.0
        eski = d[p + 2]
        yeni = _U16(d, p + 30)[0]
        n.katman = yeni if (yeni != 0 and yeni < max(len(self.katmanlar), 1)) else eski
        lt = _I16(d, p + 28)[0]
        n.lt = lt if lt != 0 else struct.unpack_from('<b', d, p + 27)[0]
        if self._bolge is not None:
            n.ad = self._bolge
            self._bolge = None
        adli = d[off] == 0x16
        u = p + (109 if adli else 81)
        if adli and sz >= 109:
            n.sinif = self._kisa(p + 81, 10, p + 92)
            n.nesne_adi = self._kisa(p + 92, 16, p + 109)
        T = n.tur
        try:
            if T == NOKTA:
                a = self._kisa(u, 30, son)
                if a:
                    n.ad = a
                n.koseler = [(n.x, n.y)]
            elif T == CIZGI and u + 16 <= son:
                y2, x2 = struct.unpack_from('<2d', d, u)
                n.koseler = [(n.x, n.y), (x2, y2)]
            elif T == DAIRE and u + 8 <= son:
                n.yaricap = _F64(d, u)[0]
                n.koseler = _yay(n.x, n.y, n.yaricap, 0.0, 6.283185307179586, True)
            elif T == YAY and u + 34 <= son:
                n.yaricap = _F64(d, u)[0]
                a0, a1 = _F64(d, u + 18)[0], _F64(d, u + 26)[0]
                if a1 < a0:
                    a1 += 6.283185307179586
                n.koseler = _yay(n.x, n.y, n.yaricap, a0, a1, False)
            elif T == YAZI and u + 12 <= son:
                n.boy, n.aci = struct.unpack_from('<2f', d, u)
                n.hiza = d[u + 8]
                n.font = d[u + 10]
                sl = d[u + 11]
                sl = min(sl, max(0, son - u - 12))
                n.metin = cp1254(d[u + 12:u + 12 + sl])
                if not (0 <= n.boy <= 1e5):
                    n.boy = 0.0
                if not (abs(n.aci) <= 100):
                    n.aci = 0.0
            elif T == SEMBOL and u + 11 <= son:
                n.sembol_olcek, n.aci = struct.unpack_from('<2f', d, u)
                n.sembol_no = _I16(d, u + 8)[0]
                n.sembol_kut = d[u + 10]
                if not (0 <= n.sembol_olcek <= 1e5):
                    n.sembol_olcek = 1.0
                if not (abs(n.aci) <= 100):
                    n.aci = 0.0
            elif T == PLINE:
                a = self._kisa(u, 10, son)
                if n.ad is None and a:
                    n.ad = a
                if u + 23 <= son:
                    n.bayrak = _I32(d, u + 15)[0]
                v = u + 27
                adet = max(0, (son - v) // 24)
                k = []
                for i in range(adet):
                    yy, xx = struct.unpack_from('<2d', d, v + i * 24)
                    k.append((xx, yy))
                n.koseler = k
                if adet >= 3 and not n.kapali and k[0] == k[-1]:
                    n.bayrak |= P_KAPALI
            elif T == ESYUK:
                v = u + 36
                adet = max(0, (son - v) // 9)
                n.koseler = [(n.x + _F32(d, v + i * 9 + 4)[0], n.y + _F32(d, v + i * 9)[0]) for i in range(adet)]
            elif T == UCGEN and u + 40 <= son:
                y2, x2 = struct.unpack_from('<2d', d, u)
                y3, x3 = struct.unpack_from('<2d', d, u + 20)
                n.koseler = [(n.x, n.y), (x2, y2), (x3, y3), (n.x, n.y)]
            elif T == DIKD and u + 38 <= son:
                ay, ax = struct.unpack_from('<2d', d, u + 18)
                n.ad = self._kisa(u, 17, son)
                n.koseler = [(n.x, n.y), (ax, n.y), (ax, ay), (n.x, ay), (n.x, n.y)]
            elif T == PAFTA:
                n.ad = self._kisa(u, 17, son)
                b = self._kutu(p + 45)
                n.koseler = [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3]), (b[0], b[1])]
            elif T == SPIRAL and u + 16 <= son:
                y2, x2 = struct.unpack_from('<2d', d, u)
                n.koseler = [(n.x, n.y), (x2, y2)]
            elif T in (ISARET, OZEL):
                if son - u <= 0:
                    return son
                if u + 28 <= son:
                    n.sembol_olcek, n.aci = struct.unpack_from('<2f', d, u)
                    g = bytes(d[u + 8:u + 24])
                    veri = _I32(d, u + 24)[0]
                    if veri == -2:
                        if g == b'\x00' * 16 and u + 49 <= self.N:
                            g = bytes(d[u + 33:u + 49])
                        n.akilli_sinif = str(uuid.UUID(bytes_le=g))
                        oz, sonra = self._ozellikler(u + 53)
                        n.ozellikler = oz or {}
                        self.nesneler.append(n)
                        r = self._senkron(sonra if oz is not None else son)
                        return r if r >= 0 else (self.N if oz is not None else son)
                    n.akilli_sinif = str(uuid.UUID(bytes_le=g))
        except Exception as e:  # noqa
            self.uyarilar.append('nesne @%d: %s' % (off, e))
        if n.tur != 0:
            self.nesneler.append(n)
        return son

    def _ozellikler(self, o):
        d = self.d
        N = self.N
        if o + 4 > N:
            return None, o
        adet = _U32(d, o)[0]
        if adet == 0 or adet > 128:
            return None, o
        q = o + 4
        oz = {}
        for _ in range(adet):
            if q + 1 > N:
                return None, o
            nl = d[q]
            if nl == 0 or nl > 64 or q + 1 + nl > N:
                return None, o
            ad = d[q + 1:q + 1 + nl].decode('utf-8', 'replace')
            q += 1 + nl
            if q + 2 > N:
                return None, o
            q += 1
            vl = d[q]
            q += 1
            if q + vl > N:
                return None, o
            deger = d[q:q + vl].decode('utf-8', 'replace')
            q += vl
            if q + 1 > N:
                return None, o
            dl = d[q]
            q += 1 + dl + 7
            oz[ad] = deger
        if q + 4 <= N and _U32(d, q)[0] == 0:
            q += 4
        return oz, q

    # ------------------------------------------------------------ dis
    def katman(self, i):
        return self.katmanlar[i] if 0 <= i < len(self.katmanlar) else None

    def meta_metin(self, ad):
        b = self.meta.get(ad)
        return None if b is None else bytes(b).decode('utf-8', 'replace')

    def epsg(self):
        """MPROJ'dan EPSG. TUREF TM (GRS80, k0=1) -> 5253..5259; ED50 TM -> 2319..; UTM -> 326zz/230zz."""
        p = self.proj
        dom = p.get('dom')
        if not dom:
            return None
        a = p.get('a')
        k0 = p.get('k0', 1.0)
        if a is None:
            return None
        grs80 = abs(a - 6378137.0) < 1.0
        utm = abs(k0 - 0.9996) < 1e-6
        if utm:
            zone = int((dom + 183) // 6)
            return (32600 if grs80 else 23000) + zone
        if dom % 3 == 0 and 27 <= dom <= 45:
            if grs80:
                return 5253 + (dom - 27) // 3
            return 2319 + (dom - 27) // 3
        return None


def _yay(cx, cy, r, a0, a1, kapat):
    import math
    tar = a1 - a0
    parca = max(12, int(abs(tar) / (2 * math.pi) * 72))
    k = [(cx + r * math.cos(a0 + tar * i / parca), cy + r * math.sin(a0 + tar * i / parca)) for i in range(parca + 1)]
    if kapat:
        k[-1] = k[0]
    return k


def tcolor_rgb(v):
    """Delphi TColor (0x00BBGGRR) -> (r, g, b)."""
    v &= 0xFFFFFF
    return (v & 255, (v >> 8) & 255, (v >> 16) & 255)


# Netcad 256 renk paleti (NETCAD.PAL), 0xRRGGBB
PALET = (
    0xFFFFFF, 0x0000FF, 0x00FF00, 0x00FFFF, 0xFF0000, 0xFF8000, 0x808000, 0xFFCC00,
    0xC0C0C0, 0x0080FF, 0xFF00FF, 0x80FF80, 0x8080FF, 0xFF8080, 0xFFFF00, 0xFFFFFF,
    0x000000, 0x0000DB, 0x00DB00, 0x00DBDB, 0xDB0000, 0xDB6E00, 0x6E6E00, 0xDFB300,
    0xB43147, 0x006EDB, 0xDB00DB, 0x6FDF6F, 0x6E6EDB, 0xDF6F6F, 0xDFDF00, 0x7D5546,
    0x666666, 0x0000B7, 0x00B700, 0x00B7B7, 0xB70000, 0xB75C00, 0x5C5C00, 0xBF9A00,
    0x963443, 0x005CB7, 0xB700B7, 0x5FBF5F, 0x5C5CB7, 0xBF5F5F, 0xBFBF00, 0x725347,
    0x999999, 0x000093, 0x009300, 0x009393, 0x930000, 0x934A00, 0x4A4A00, 0x9F8100,
    0x7D343F, 0x004A93, 0x930093, 0x509F50, 0x4A4A93, 0x9F5050, 0x9F9F00, 0x604237,
    0xCCCCCC, 0x00006F, 0x006F00, 0x006F6F, 0x6F0000, 0x6F3800, 0x383800, 0x7F6800,
    0x6A343A, 0x00386F, 0x6F006F, 0x407F40, 0x38386F, 0x7F4040, 0x7F7F00, 0x553329,
    0xFFFFFF, 0x00005F, 0x004B00, 0x004B4B, 0x4B0000, 0x4B2600, 0x262600, 0x5F4F00,
    0x583235, 0x00264B, 0x4B004B, 0x305F30, 0x26264B, 0x5F3030, 0x5F5F00, 0x472B24,
    0x344449, 0x16305C, 0x005B3D, 0x52196E, 0xFF2424, 0xCE2410, 0x9ACF19, 0xE5811F,
    0x671C4F, 0x004D80, 0xA51D62, 0x577735, 0x007A90, 0xD52B31, 0xFFFF24, 0x81261E,
    0x546065, 0x37406A, 0x00714A, 0x5F3F83, 0xFF4848, 0xD6311F, 0xA8D549, 0xE88D3D,
    0x7D1D5F, 0x275D8F, 0xD71C78, 0x687E52, 0x088CA3, 0xDC4C44, 0xFFFF48, 0xA12B1F,
    0x738289, 0x515B80, 0x00815C, 0x7C609B, 0xFF6C6C, 0xDB4C34, 0xB3DA69, 0xEB9C59,
    0x8C3B71, 0x486EA1, 0xE04687, 0x68943E, 0x44A1B8, 0xE16658, 0xFFFF6C, 0xB35A35,
    0x859697, 0x707292, 0x4DA98A, 0x9F8CBB, 0xFF9090, 0xE0674C, 0xC1E281, 0xEEAD73,
    0x9E5685, 0x6585B8, 0xD35D8E, 0x78A355, 0x85BCD0, 0xE67F6F, 0xFFFF90, 0xC5714D,
    0x99AEB2, 0x9D9DB5, 0x77C1A7, 0xAC97C2, 0xFFB4B4, 0xE67F66, 0xD2E99B, 0xF2C08C,
    0xC089AE, 0x84A0D1, 0xD1769B, 0x8AB46C, 0xB3CCE4, 0xEB9988, 0xFFFFB4, 0xDA8967,
    0xD7E4E8, 0xB6C3D9, 0xA2D3C3, 0xB9A4CB, 0xFFD8D8, 0xEB9981, 0xE3F1C4, 0xF6D2AC,
    0xE0B1CE, 0xA7BBE0, 0xD08BA7, 0xBFE0A4, 0xDCEBF1, 0xF2B8A8, 0xFFFFD8, 0xF3C2A5,
    0xB36763, 0xB56675, 0xD52A4A, 0xE57774, 0xE05567, 0xB88082, 0x6B515C, 0x8C536C,
    0xF097BA, 0xB97F97, 0xBD9CAA, 0x945E84, 0xB44E8B, 0x8C1D72, 0x6E4285, 0x5D396F,
    0xF4C5B0, 0xEB9981, 0xE4775D, 0xB2663D, 0x8A5444, 0xF3C58D, 0xF3C500, 0xEB9A67,
    0xEB9A48, 0xE47744, 0xBB9E60, 0xB68159, 0xBFBF64, 0x4B4941, 0xB3DA7A, 0x7BC128,
    0x76858F, 0x5B646B, 0x404447, 0x485D5D, 0x3C7068, 0x5B7B7A, 0x408D81, 0x408D6A,
    0x3CAEBF, 0x428D99, 0x92AC9C, 0xB3DBC5, 0x77C19D, 0x76867B, 0x758669, 0x92AC68,
    0xEC999C, 0x6D6059, 0xB8AED3, 0x8C7FB3, 0x6675AF, 0x6C5C99, 0x776D92, 0x4A5373,
    0x4C4759, 0x5F6B81, 0x0075BE, 0x75C0EF, 0x92AABB, 0x76858F, 0x5B646B, 0xFF0000,
)


def palet_rgb(i):
    """Palet indeksi -> (r, g, b)."""
    v = PALET[i] if 0 <= i < 256 else 0
    return ((v >> 16) & 255, (v >> 8) & 255, v & 255)
