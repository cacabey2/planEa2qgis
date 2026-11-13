# -*- coding: utf-8 -*-
"""planEa2qgis — QGIS arayuzu (planEa ailesi, kipsiz pencere)."""
import os
import traceback

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                                 QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
                                 QHBoxLayout, QLabel, QLineEdit, QListWidget,
                                 QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                                 QSpinBox, QStyledItemDelegate, QToolButton, QVBoxLayout,
                                 QWidget)
from qgis.core import Qgis, QgsSettings
from qgis.PyQt import QtGui as _QtGui, QtWidgets as _QtWidgets
# QAction Qt6'da QtGui'de, Qt5'te QtWidgets'ta
QAction = getattr(_QtGui, "QAction", None) or getattr(_QtWidgets, "QAction")

from . import aktar, eslesme

EKLENTI_DIR = os.path.dirname(os.path.abspath(__file__))
BASLIK = u"planEa2qgis"
SURUM = u"1.0.0"
ANAHTAR = "planEa2qgis/"

# planEa renkleri
LACIVERT = "#0B2E4F"
MAVI = "#1F7AE0"
MAVI_KOYU = "#1665C1"
TURUNCU = "#FF7417"
ZEMIN = "#F4F6FA"
KENAR = "#DDE3EC"
METIN2 = "#5B6B7F"

QSS = u"""
QDialog#planEa {{ background: {zemin}; }}
QFrame#ust {{ background: white; border-bottom: 3px solid {turuncu}; }}
QLabel#altbaslik {{ color: {metin2}; font-size: 9pt; }}
QFrame.kart {{ background: white; border: 1px solid {kenar}; border-radius: 10px; }}
QLabel.kartbaslik {{ color: {lacivert}; font-weight: 600; font-size: 10pt; }}
QLabel.etiket {{ color: {metin2}; }}
QListWidget {{ border: 1px dashed #B8C4D4; border-radius: 8px; background: #FAFBFD;
              padding: 4px; color: {lacivert}; }}
QListWidget::item {{ padding: 4px 6px; border-radius: 4px; }}
QListWidget::item:selected {{ background: #E3EEFC; color: {lacivert}; }}
QLineEdit, QComboBox, QSpinBox {{ border: 1px solid {kenar}; border-radius: 6px;
              padding: 4px 8px; background: white; min-height: 22px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {mavi}; }}
QComboBox {{ padding-right: 26px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
              width: 24px; border: none; }}
QComboBox::down-arrow {{ image: url("{ok}"); width: 12px; height: 8px; }}
QComboBox QAbstractItemView {{ background: white; color: {lacivert}; border: 1px solid {kenar};
              outline: 0; padding: 4px; selection-background-color: #E3EEFC;
              selection-color: {lacivert}; }}
QComboBox QAbstractItemView::item {{ min-height: 28px; padding: 2px 10px; border-radius: 4px;
              color: {lacivert}; background: white; }}
QComboBox QAbstractItemView::item:hover, QComboBox QAbstractItemView::item:selected {{
              background: #E3EEFC; color: {lacivert}; }}
QCheckBox {{ color: {lacivert}; spacing: 8px; }}
QPushButton {{ border: 1px solid {kenar}; border-radius: 6px; padding: 6px 14px;
              background: white; color: {lacivert}; }}
QPushButton:hover {{ background: #EEF3FA; }}
QPushButton#birincil {{ background: {mavi}; border: none; color: white; font-weight: 600;
              padding: 8px 22px; }}
QPushButton#birincil:hover {{ background: {mavi_koyu}; }}
QPushButton#birincil:disabled {{ background: #9BBFEA; }}
QToolButton {{ border: none; color: {mavi}; padding: 2px 6px; }}
QToolButton:hover {{ color: {turuncu}; }}
QProgressBar {{ border: none; background: #E6EBF2; border-radius: 4px; height: 8px;
              text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {turuncu}; border-radius: 4px; }}
QLabel#durum {{ color: {metin2}; }}
""".format(ok=os.path.join(EKLENTI_DIR, "ok.svg").replace("\\", "/"), zemin=ZEMIN, turuncu=TURUNCU, metin2=METIN2, kenar=KENAR, lacivert=LACIVERT,
           mavi=MAVI, mavi_koyu=MAVI_KOYU)


def _kart(baslik):
    k = QFrame()
    k.setProperty("class", "kart")
    v = QVBoxLayout(k)
    v.setContentsMargins(14, 12, 14, 14)
    v.setSpacing(8)
    if baslik:
        b = QLabel(baslik)
        b.setProperty("class", "kartbaslik")
        v.addWidget(b)
    return k, v


def _etiket(t):
    e = QLabel(t)
    e.setProperty("class", "etiket")
    return e


class DosyaListesi(QListWidget):
    """Surukle-birak ile NCZ eklenebilen liste."""

    def __init__(self, parent=None):
        super(DosyaListesi, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(96)

    def ekle(self, yollar):
        var = set(self.yollar())
        for y in yollar:
            if y.lower().endswith(".ncz") and y not in var:
                it = QListWidgetItem(os.path.basename(y))
                it.setToolTip(y)
                it.setData(Qt.ItemDataRole.UserRole, y)
                self.addItem(it)
                var.add(y)

    def yollar(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.ekle([u.toLocalFile() for u in e.mimeData().urls()])
        e.acceptProposedAction()

    def paintEvent(self, ev):
        super(DosyaListesi, self).paintEvent(ev)
        if self.count() == 0:
            from qgis.PyQt.QtGui import QPainter, QColor
            p = QPainter(self.viewport())
            p.setPen(QColor(METIN2))
            p.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter,
                       u"NCZ dosyalarını buraya sürükleyin\nya da “Dosya ekle”ye tıklayın")
            p.end()


class AktarPenceresi(QDialog):
    def __init__(self, iface):
        super(AktarPenceresi, self).__init__(iface.mainWindow())
        self.iface = iface
        self.setObjectName("planEa")
        self.setWindowTitle(u"planEa2qgis — NCZ içe aktar")
        self.setWindowIcon(QIcon(os.path.join(EKLENTI_DIR, "icon.png")))
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(600)
        self.setStyleSheet(QSS)
        ay = QgsSettings()

        kok = QVBoxLayout(self)
        kok.setContentsMargins(0, 0, 0, 0)
        kok.setSpacing(0)

        # ---- ust serit: logo + alt baslik + hakkinda
        ust = QFrame()
        ust.setObjectName("ust")
        uh = QHBoxLayout(ust)
        uh.setContentsMargins(18, 10, 14, 10)
        logo = QLabel()
        pm = QPixmap(os.path.join(EKLENTI_DIR, "logo.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaledToHeight(46, Qt.TransformationMode.SmoothTransformation))
        uh.addWidget(logo)
        yazi = QVBoxLayout()
        yazi.setSpacing(0)
        ad = QLabel(u"<span style='color:%s;font-size:13pt;font-weight:600'>2qgis</span>" % LACIVERT)
        alt = QLabel(u"NCZ imar planlarını e-Plan resmi gösterimiyle QGIS'e aktarır")
        alt.setObjectName("altbaslik")
        yazi.addWidget(ad)
        yazi.addWidget(alt)
        uh.addLayout(yazi)
        uh.addStretch(1)
        hk = QToolButton()
        hk.setText(u"Hakkında")
        hk.clicked.connect(self._hakkinda)
        uh.addWidget(hk, 0, Qt.AlignmentFlag.AlignTop)
        kok.addWidget(ust)

        govde = QWidget()
        gv = QVBoxLayout(govde)
        gv.setContentsMargins(16, 14, 16, 12)
        gv.setSpacing(12)
        kok.addWidget(govde)

        # ---- kart 1: dosyalar
        k1, v1 = _kart(u"1  NCZ dosyaları")
        self.liste = DosyaListesi()
        v1.addWidget(self.liste)
        sat = QHBoxLayout()
        b_ekle = QPushButton(u"Dosya ekle…")
        b_ekle.clicked.connect(self._dosya_sec)
        b_cik = QPushButton(u"Seçileni çıkar")
        b_cik.clicked.connect(self._cikar)
        sat.addWidget(b_ekle)
        sat.addWidget(b_cik)
        sat.addStretch(1)
        v1.addLayout(sat)
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.addWidget(_etiket(u"GPKG klasörü"), 0, 0)
        self.cikti = QLineEdit(ay.value(ANAHTAR + "cikti", "", str))
        self.cikti.setPlaceholderText(u"boş = NCZ ile aynı klasör")
        g.addWidget(self.cikti, 0, 1)
        b_kl = QPushButton(u"Seç…")
        b_kl.clicked.connect(self._klasor_sec)
        g.addWidget(b_kl, 0, 2)
        v1.addLayout(g)
        gv.addWidget(k1)

        # ---- kart 2: gosterim
        k2, v2 = _kart(u"2  Gösterim")
        g2 = QGridLayout()
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(8)
        self.kademe = QComboBox()
        self.kademe.addItem(u"Otomatik (dosyadan)", None)
        for kd in eslesme.KADEMELER:
            self.kademe.addItem(eslesme.KADEME_ADI[kd], kd)
        i = self.kademe.findData(ay.value(ANAHTAR + "kademe", None))
        self.kademe.setCurrentIndex(max(i, 0))
        self.oncelik = QComboBox()
        self.oncelik.addItem(u"e-Plan resmi gösterimi", "eplan")
        self.oncelik.addItem(u"Dosyanın kendi renkleri", "dosya")
        i = self.oncelik.findData(ay.value(ANAHTAR + "oncelik", "eplan", str))
        self.oncelik.setCurrentIndex(max(i, 0))
        # cizim olcegi: listeden secilir ya da elle yazilir (1/7500, 7500 ...)
        self.olcek = QComboBox()
        self.olcek.setEditable(True)
        self.olcek.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.olcek.addItem(u"Otomatik (dosyadan)", 0)
        for pay in (500, 1000, 2000, 5000, 10000, 25000, 50000, 100000):
            self.olcek.addItem(u"1/%d" % pay, pay)
        self.olcek.setToolTip(u"Otomatik: dosya adından, pafta indeksinden ya da '1/N' yazısından.\n"
                              u"Listeden seçin ya da yazın (ör. 1/7500).")
        for cb in (self.kademe, self.oncelik, self.olcek):
            cb.setItemDelegate(QStyledItemDelegate(cb))
        g2.addWidget(_etiket(u"Plan kademesi"), 0, 0)
        g2.addWidget(self.kademe, 0, 1)
        g2.addWidget(_etiket(u"Alan stili"), 1, 0)
        g2.addWidget(self.oncelik, 1, 1)
        g2.addWidget(_etiket(u"Çizim ölçeği"), 2, 0)
        g2.addWidget(self.olcek, 2, 1)
        g2.setColumnStretch(1, 1)
        v2.addLayout(g2)
        self.ic_alan = QCheckBox(u"İç alanları dış alandan boşalt (taramalar üst üste binmesin)")
        self.ic_alan.setChecked(ay.value(ANAHTAR + "icAlan", True, bool))
        self.gizli = QCheckBox(u"Dosyada kapalı olan katmanları kapalı getir")
        self.gizli.setChecked(ay.value(ANAHTAR + "gizli", True, bool))
        v2.addWidget(self.ic_alan)
        v2.addWidget(self.gizli)
        gv.addWidget(k2)

        # ---- alt: ilerleme + dugmeler
        self.ilerleme = QProgressBar()
        self.ilerleme.setMaximumHeight(8)
        self.ilerleme.setVisible(False)
        gv.addWidget(self.ilerleme)
        self.durum = QLabel(u"")
        self.durum.setObjectName("durum")
        self.durum.setWordWrap(True)
        gv.addWidget(self.durum)

        alt_s = QHBoxLayout()
        alt_s.addStretch(1)
        kapat = QPushButton(u"Kapat")
        kapat.clicked.connect(self.hide)
        self.btn = QPushButton(u"Aktar")
        self.btn.setObjectName("birincil")
        self.btn.setDefault(True)
        self.btn.clicked.connect(self._aktar)
        alt_s.addWidget(kapat)
        alt_s.addWidget(self.btn)
        gv.addLayout(alt_s)

    # ------------------------------------------------------------ olaylar
    def _dosya_sec(self):
        son = QgsSettings().value(ANAHTAR + "sonKlasor", "", str)
        dd, _ = QFileDialog.getOpenFileNames(self, u"NCZ dosyası seç", son,
                                             u"NCZ (*.ncz *.NCZ);;Tüm dosyalar (*.*)")
        if dd:
            QgsSettings().setValue(ANAHTAR + "sonKlasor", os.path.dirname(dd[0]))
            self.liste.ekle(dd)

    def _cikar(self):
        for it in self.liste.selectedItems():
            self.liste.takeItem(self.liste.row(it))

    def _klasor_sec(self):
        d = QFileDialog.getExistingDirectory(self, u"GPKG çıktı klasörü", self.cikti.text())
        if d:
            self.cikti.setText(d)

    def _hakkinda(self):
        d = QDialog(self)
        d.setObjectName("planEa")
        d.setStyleSheet(QSS)
        d.setWindowTitle(u"planEa2qgis hakkında")
        v = QVBoxLayout(d)
        v.setContentsMargins(28, 22, 28, 18)
        logo = QLabel()
        pm = QPixmap(os.path.join(EKLENTI_DIR, "logo.png"))
        if not pm.isNull():
            logo.setPixmap(pm.scaledToWidth(220, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(logo)
        t = QLabel(u"<p style='font-size:12pt;color:%s'><b>planEa2qgis</b></p>"
                   u"<p>Sürüm %s<br>NCZ imar planlarını e-Plan resmi gösterimiyle QGIS'e aktarır.</p>"
                   u"<p>Geliştiren: <b>Erdoğan Arslan</b><br>© 2026 Erdoğan Arslan</p>"
                   u"<p style='color:%s;font-size:8pt'>Gösterim: e-Plan (Mekânsal Planlar) SLD "
                   u"kütüphanesi, tarama dokuları ve fontları.<br>Netcad® ilgili firmanın tescilli "
                   u"markasıdır; bu eklenti Netcad yazılımı veya dosyası içermez.</p>"
                   % (LACIVERT, SURUM, METIN2))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setWordWrap(True)
        v.addWidget(t)
        b = QPushButton(u"Tamam")
        b.setObjectName("birincil")
        b.clicked.connect(d.accept)
        v.addWidget(b, 0, Qt.AlignmentFlag.AlignCenter)
        d.exec()


    def _olcek_degeri(self):
        """Ölçek kutusundaki metinden payda: '1/5000', '5000', '1:5.000' -> 5000; boş/Otomatik -> 0."""
        import re
        metin = (self.olcek.currentText() or "").strip()
        if self.olcek.currentIndex() >= 0 and metin == self.olcek.itemText(self.olcek.currentIndex()):
            v = self.olcek.itemData(self.olcek.currentIndex())
            if v is not None:
                return int(v)
        metin = metin.replace(".", "").replace(" ", "")
        m = re.search(r"(?:1[/:])?(\d{2,7})$", metin)
        return int(m.group(1)) if m else 0
    def _aktar(self):
        dd = self.liste.yollar()
        if not dd:
            self._dosya_sec()
            dd = self.liste.yollar()
            if not dd:
                return
        ay = QgsSettings()
        ay.setValue(ANAHTAR + "cikti", self.cikti.text())
        ay.setValue(ANAHTAR + "kademe", self.kademe.currentData())
        ay.setValue(ANAHTAR + "oncelik", self.oncelik.currentData())
        ay.setValue(ANAHTAR + "icAlan", self.ic_alan.isChecked())
        ay.setValue(ANAHTAR + "gizli", self.gizli.isChecked())

        s = aktar.Secenekler()
        s.kademe = self.kademe.currentData()
        s.stil_onceligi = self.oncelik.currentData()
        s.olcek = self._olcek_degeri()      # dosyaya ozgu: kaydedilmez, her acilista Otomatik
        s.ic_alan_bosalt = self.ic_alan.isChecked()
        s.kapali_katmanlar_gizli = self.gizli.isChecked()

        self.btn.setEnabled(False)
        self.ilerleme.setVisible(True)
        self.ilerleme.setRange(0, 0)
        tamam = []
        del aktar.SON_KAPSAMLAR[:]
        try:
            for no, yol in enumerate(dd, 1):
                if not os.path.exists(yol):
                    continue
                ad = os.path.basename(yol)
                klasor = self.cikti.text().strip() or os.path.dirname(yol)
                self.durum.setText(u"%d / %d · %s okunuyor…" % (no, len(dd), ad))
                QApplication.processEvents()

                def geri(i, n, ad=ad, no=no):
                    self.ilerleme.setRange(0, max(n, 1))
                    self.ilerleme.setValue(i)
                    self.durum.setText(u"%d / %d · %s — iç alanlar %d / %d" % (no, len(dd), ad, i, n))
                    QApplication.processEvents()
                try:
                    _n, ozet = aktar.ice_aktar(yol, klasor, s, geri=geri)
                    tamam.append(ozet)
                except Exception as e:  # noqa
                    aktar.log(traceback.format_exc(), 2)
                    QMessageBox.critical(self, BASLIK, u"%s\n\n%s" % (ad, e))
                self.ilerleme.setRange(0, 0)
        finally:
            self.btn.setEnabled(True)
            self.ilerleme.setVisible(False)
        if tamam:
            # dunya geneline degil: plan onama sinirina (yoksa aktarilan katmanlara)
            try:
                if not aktar.yakinlastir(self.iface.mapCanvas()):
                    self.iface.mapCanvas().zoomToFullExtent()
            except Exception:  # noqa
                aktar.log(traceback.format_exc(), 1)
            kisa = []
            for oz in tamam:
                ad, _, kalan = oz.partition(": ")
                parca = kalan.split(" · ")
                kisa.append(u"✓ %s — %s · %s" % (ad, parca[0].split(" (")[0],
                                                  u" · ".join(parca[1:])))
            self.durum.setText(u"\n".join(kisa))
            self.durum.setToolTip(u"\n".join(tamam))
            self.iface.messageBar().pushMessage(BASLIK, u"%d dosya aktarıldı. Ayrıntı: Günlük → planEa2qgis"
                                                % len(tamam), level=Qgis.MessageLevel.Success, duration=6)


class PlanEa2QgisPlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.pencere = None
        self.menu = u"&planEa"

    def initGui(self):
        icon = QIcon(os.path.join(EKLENTI_DIR, "icon.png"))
        self.action = QAction(icon, u"planEa2qgis — NCZ içe aktar…", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginMenu(self.menu, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.pencere is not None:
            self.pencere.close()
            self.pencere = None

    def run(self):
        if self.pencere is None:
            self.pencere = AktarPenceresi(self.iface)
        self.pencere.show()
        self.pencere.raise_()
        self.pencere.activateWindow()
