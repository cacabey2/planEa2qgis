# planEa2qgis — v0.3.0

NCZ imar planlarını QGIS'e aktarır; alanları **e-Plan (Mekânsal Planlar) resmi gösterimiyle**
— tarama dokusu, renk ve merkez sembolleriyle — çizer. planEa ailesinin QGIS eklentisi.

- Saf Python NCZ okuyucu: harici program ya da Netcad kurulumu gerekmez.
- Eklenti **Netcad yazılımı ya da dosyası içermez** (şablon, doku deposu, çizgi tipi, lejant yok).
  Gösterim kaynağı yalnız eklentiyle gelen e-Plan SLD kütüphanesi ve kendi eşleşme tablomuzdur.

## Kurulum

- `KUR.bat` → çift tıkla. Eklenti `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\planEa2qgis`
  klasörüne kopyalanır. Eski **EplanNczimport** eklentisi varsa sorulur; onaylanırsa
  `E:\claudetemp\EplanNczimport_eski_yedek` klasörüne taşınır (silinmez).
- QGIS'i yeniden başlat → Eklentiler → Eklentileri Yönet → **planEa2qgis**'i işaretle.
- Dağıtım zip'i: `ZIP_YAP.bat` → `cikti\planEa2qgis-0.3.0.zip` (QGIS → ZIP'ten kur).
- GitHub: `GITHUB_YUKLE.bat` (depo: `cacabey2/planEa2qgis`, önce GitHub'da oluşturulmalı).

## Kullanım

Pencere kipsizdir. NCZ seç → **Aktar**.

| Seçenek | Varsayılan | Not |
|---|---|---|
| Plan kademesi | Otomatik | Dosyanın meta adı / dosya adı (UIP, NIP, CDP); yoksa katman adlarıyla en çok eşleşen kademe |
| Alan stili | e-Plan | e-Plan karşılığı olmayan katmanlar dosyanın kendi rengiyle; istenirse hepsi dosya rengiyle |
| Çizim ölçeği | Otomatik | Dosya adı / `PINDEX_N` / "1/N" yazısı; yoksa 1/1000 |
| İç alanları boşalt | Açık | Aşağıda |
| Kapalı katmanlar | Kapalı gelir | Dosyada kapalı işaretli katmanlar QGIS'te işaretsiz |

Çıktı: NCZ ile aynı adlı tek `.gpkg` (`alan`, `cizgi`, `nokta`, `yazi`). Her NCZ katmanı ayrı
QGIS katmanı; adı `PL_TARIM_ALANI — Tarım Alanı` biçiminde. Tarama karoları stile `base64`
gömülür: `.qgz` kaydedip taşıyınca kaybolmaz.

## Yayınlama (plugins.qgis.org)

`YAYINLA.bat` çift tıkla:

1. İstersen önce `GITHUB_YUKLE.bat` ile depoyu günceller (site, `metadata.txt`'deki depo,
   ana sayfa ve hata takip bağlantılarının çalışmasını ister).
2. Paketi `cikti\planEa2qgis-<sürüm>.zip` olarak hazırlar (bat, gpkg, `__pycache__` hariç; LICENSE zorunlu).
3. Jetonla (token) `https://plugins.qgis.org/plugins/planEa2qgis/version/add/api/` adresine yükler.

**İlk yayın:** eklenti sitede yokken jeton da yoktur. Bat, jeton istemeden tarayıcıda
`plugins.qgis.org/plugins/add/` sayfasını açar ve zip'i gösterir: OSGeo hesabıyla giriş yapıp
zip'i bir kez elle yükle. Onaydan sonra eklenti sayfasında jeton oluştur; sonraki sürümler bat'la gider.
Jeton `%APPDATA%\planEa2qgis\qgis_token.txt` dosyasında saklanır (proje klasöründe ve GitHub'da değil).

Her yükleme önce güvenlik taramasından, sonra gönüllü onayından geçer. Yeni sürüm için
`metadata.txt`'de `version` artırılmalı ve `changelog`'a satır eklenmelidir.

## Lisans

GPL-2.0-or-later (`LICENSE`).

## Kontrol NCZ'sinde (N39D4_NIP_25000) bulunan hatalar ve çözümler

| Hata (eski sürüm) | Kök neden | Çözüm |
|---|---|---|
| Tarım alanlarında yanlış tarama, plan dışına taşan kamalar | Eski dönüştürücü `PL_` katmanındaki **≥3 köşeli her nesneyi** poligon yapıyordu. `PL_DIKILI_TARIM`'in 63 nesnesinin 27'si açık cephe çizgisi; zorla kapatılınca sanayi/konut üstüne binen sahte alanlar çıktı (planda toplam 100 açık çizgi) | Alan yalnız **kapalı + dolu** işaretli çoklu çizgiden kurulur; açık ve dolgusuz kapalı çizgi çizgi kalır |
| Tarım dokusu yanlış | `PL_DIKILI_TARIM` adı e-Plan'da yok | Kendi tablomuz: `DIKILI_TARIM → TARIM_ALANI` (e-Plan NİP Tarım Alanı dokusu) |
| İç/dış alan taraması üst üste | İç içe 89 alan çifti; dış alan iç alanın üstüne çiziliyordu | Küçük alanın **≥%50'si** büyük alanın içindeyse büyükten **boşluk** olarak çıkarılır |
| Aynı yerde iki sınıf (tarım + mera) | 17 alan birebir kopya | Eşit büyüklükte iki alanda dosyada **sonra çizilen** kalır |

Ölçüm (N39D4): 8.669 nesne, senkron kaybı 0 · 406 alan, 18 alana iç alan boşluğu (76 iç alan),
7.682 çizgi, 210 yazı, 353 nokta · 2,4 sn. Diğer test dosyaları (uip, MERKEZELMACIk2025,
Harita, kadastro_1) hatasız.

## Stil zinciri

1. **Dolgu kararı dosyadan:** katman stili varsa ve dolgu tanımlamıyorsa doldurulmaz
   (MERKEZELMACIk'ta önlemli alan planı koyu örtüyordu). Stil yoksa yalnız e-Plan'da alan
   sınıfı olan katmanlar dolar.
2. **e-Plan eşleşmesi** (`eslesme.py`): ön ek soyulur (`PL_`, `SNR_`, `HAT_`, `KA_`, `KST_`…) →
   `TAKMA_AD` tablosu → e-Plan kural başlığı / dosya adı (`eplan_style.py`).
   Eksik eşleşme eklemek için tek yer: `eslesme.TAKMA_AD`.
3. **Yedek:** dosyanın kendi rengi ve saydamlığı (düz renk); çizgide dosyanın kendi deseni.
4. Yollar (`HAT_OTOYOL`, `HAT_1/2/3DER_YOL`, `HAT_KOY_YOLU`): `eplan_style` metre ölçekli yol kesitleri.

## Çizgi ve sembol gösterimi (mevzuat lejandı)

Sınır ve hat çizgileri e-Plan SLD'sindeki tanımdan birebir üretilir (`eplan_cizgi.py`):
e-Plan fontlarındaki lejand glifleri (ilçe sınırı çizgi+iki nokta, plan onama daireleri,
sit dolu daire, önlemli alan üçgenleri, yapı yaklaşma çizgi+nokta…) çizgi boyunca döndürülerek
dizilir; düz/kesik çizgilerde renk, kalınlık, desen ve dik ofset uygulanır.

Desen boyları ve semboller pafta milimetresidir: dünya boyu = değer × plan ölçeği / 1000
(yaklaştıkça küçülmez). **Kalem kalınlığı ise Netcad'deki gibi sabittir** (ekran mm; SLD kalemi:
ilçe 0,8, yapı yaklaşma 0,4 mm). "Çizgi + nokta" glifleri harf olarak değil, glif şekli
çözümlenip ince kesik/noktalı çizgi olarak çizilir.

Sınır/hat/kısıt katmanları (`SNR_`, `KST_`, `HAT_`) ve e-Plan'da yalnız çizgi olan sınıflar
(önlemli alan, plan sınırları) dosya stili dolgu tanımlasa bile doldurulmaz (Netcad gibi).
e-Plan glif boyları mevzuattaki pafta ölçülerine tek oranla oturmadığı için glif türüne göre
ayarlıdır (`eplan_cizgi.py` başındaki sabitler):

| Glif türü | Kural | Kontrol (mevzuat) |
|---|---|---|
| desen parçası (ilçe, yapı yaklaşma, plan değişikliği) | glif = desenin çizgi parçası, periyot = desen | 18 / 17 mm, 12 / 12 mm |
| küçük sembol + desen (plan onama) | glif = Size × 0,25, periyot = desen × 0,35 | ø3,75 / 3,7 mm, 7,7 / 7,5 mm |
| desensiz dizi (sit, önlemli alan) | glif = Size × 0,32, uç uca | 9,6 mm (mevzuat 9–15) |
| alan merkez sembolü (PARK, BHA, OSB…) | yükseklik = Size × 0,45 | Netcad'de yapılaşma yazısının ≈1,85 katı |
| PL katmanındaki sembol nesnesi | katmanın e-Plan glifi, yükseklik = nesne ölçeği × 8 m; o katmanda alan ortası glifi basılmaz | — |

### Nazım imar planı (NİP) ve dosyanın kendi çizgi tipleri

- Yukarıdaki oranlar UİP'de ölçüldü. NİP paftasında Netcad'in çizgi sembolleri ve aralıkları
  ~2,9 kat büyük (desensiz glif dizileri: kentsel dönüşüm daireleri, önlemli alan, sit): `eplan_cizgi.KADEME_CARPANI` (NIP/CDP 2,85). Desenli küçük semboller (gecekondu önleme artısı, plan onama halkası) NİP'te 1/25000 için 50 m: `KUCUK_SEMBOL_CARPANI`.
- Katman adı e-Plan'da çizgi karşılığı vermiyorsa NCZ'nin katmana atadığı çizgi tipinin
  **adı** kullanılır (`eslesme.CIZGI_TIPI_KURAL`): `ÖNL_ALN-14` → önlemli alan,
  `GECEKN_14` → gecekondu önleme, `İLÇE_14` → ilçe sınırı… e-Plan'da karşılığı olmayan
  `END_GEL_14` (endüstriyel gelişme bölgesi) kendi tanımımızla ikili siyah daire.
- Çok parçalı yollar sembol seviyeleriyle çizilir (parça birleşimlerinde bant kesilmez).

### Plan sembolleri (`PLANSEMBOL`)

NCZ yalnız Netcad sembol kütüphanesinin numarasını taşır; kütüphane kullanılmaz.
Numaralar Netcad paftasıyla karşılaştırılıp kendi çizimimizle gösterilir
(`plansembol.py`): 10 T1, 12 T3, 13 TİCK, 16 BHA, 34 İA (kutu içinde kod), 27 üçgen,
29 iç içe kare, 31 çift kare; diğerleri boş kutu. Kutu kenarı = nesne ölçeği × 8 m.
Dosyada plan sembolü varsa e-Plan alan ortası glifleri (PARK, BHA…) basılmaz — Netcad gibi.

Aktarımdan sonra harita plan onama sınırına (yoksa aktarılan katmanlara) yakınlaşır.

## Akıllı nesneler

| Sınıf | Gösterim | Aktarım |
|---|---|---|
| Yol genişliği (`SM_YOL`) | beyaz daire + genişlik sayısı; çap = nesnenin sembol ölçeği × 14,3 m (dosyadaki sembol çerçevesiyle ölçüldü) | `nokta` tablosunda `genislik`, `yolTuru` |
| Yapılaşma (`SM_YAPILASMA`) | `E=… / TAKS=… / KAKS=… / Hmax=… m / Yençok= … Kat` — yalnız dosyada "boş değil" işaretli değerler, dosyadaki ondalık hane sayısıyla | değerler, nesnenin içine düştüğü **en küçük imar alanına** öznitelik olarak yazılır: `alan` tablosunda `emsal`, `taks`, `kaks`, `hmax`, `yencok`, `yapilasma` |

Etiket boyu: `aktar.YAPILASMA_YAZI_M`, yol dairesi: `aktar.YOL_DAIRE_M`.

## Altlık çizgileri

Ada kenarı, kaldırım, refüj, yaya yolu, yol ekseni, parsel e-Plan'dan değil dosyanın kendi
rengiyle çizilir (Netcad görünümü). Kalınlıklar `eslesme.DOSYA_CIZGI`'de: ada kenarı 0,50 mm,
kaldırım/refüj 0,13 mm.

## Dosyalar

| Dosya | İş |
|---|---|
| `ncz_okuyucu.py` | NCZ okuyucu (planEa çekirdeğinin Python karşılığı) |
| `eslesme.py` | katman adı → e-Plan kuralı, kademe seçimi, font yükleme |
| `eplan_style.py` | e-Plan SLD okuma ve QML üretimi |
| `akilli.py` | akıllı nesne özellikleri: yapılaşma etiketi, alan öznitelikleri |
| `eplan_cizgi.py` | e-Plan çizgi glifleri ve alan merkez sembolü (mevzuat ölçüleri) |
| `stil.py` | dolgu kararı, e-Plan uygulama, karo gömme, dosya rengi yedeği |
| `aktar.py` | geometri, iç alan boşaltma, GPKG, katman ağacı, yazı/nokta stilleri |
| `LICENSE` | GPL-2.0-or-later |
| `YAYINLA.bat` | paket + plugins.qgis.org'a jetonla yükleme |
| `plansembol.py` | plan sembolü numarası → kendi sembol çizimimiz |
| `eklenti.py` | arayüz (kipsiz pencere, Hakkında) |
| `eplan/styles` | UİP/NİP/ÇDP SLD'leri (233) |
| `eplan/TaramaResim` | bu SLD'lerin kullandığı 444 tarama karosu (PNG) |
| `eplan/fonts` | bu SLD'lerin kullandığı 27 e-Plan fontu (QGIS oturumuna yüklenir, sisteme kurulmaz) |

## Eski EplanNczimport'tan çıkarılanlar (33 MB → ~5 MB)

| Çıkarılan | Neden |
|---|---|
| `Ncz2Gpkg.exe` bağımlılığı | Saf Python okuyucu |
| `KNKE/`, `LEJAND/`, `ltypes/` | Netcad kaynaklı (plan şablonları, lejant, çizgi tipleri) — yayınlanamaz |
| `eplan/` içinde MUIP/MNIP SLD'leri ve kullanılmayan 510 karo, 82 font | Hiçbir SLD'de geçmiyor |
| `eplan_lejant.py`, `eplan_bridge.py`, `eplan_plan_dialog.py`, `styles.py`, `netcad_*.py`, `knke.py` | Yerlerine `eslesme.py`, `stil.py`, `aktar.py` |
| `bin/`, `.gitignore.txt`, `EPLAN.md` | Geçersiz |

## Bilinen eksikler

- Plan sembolü tablosunda (`plansembol.SEMBOLLER`) yalnız Netcad paftasıyla doğrulanan numaralar var;
  tanınmayan numara boş kutu olarak çizilir.
- `ncz_okuyucu.PALET`: NCZ'deki renk indekslerini çözmek için 256 renklik indeks tablosu.
