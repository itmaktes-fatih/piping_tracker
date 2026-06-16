import os
from datetime import datetime
import json
import threading 
import requests 
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import get_color_from_hex, platform
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock 
from openpyxl import Workbook

# 🚨 ANDROID GÜVENLİ İNTERNET VE SSL BAĞLANTI YAMASI:
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

# 🔗 YENİ VERİ TABANI LINKINIZ ENTEGRE EDİLDİ:
FIREBASE_URL = "https://piping-tracker-default-rtdb.europe-west1.firebasedatabase.app/"

# Endüstriyel Borulama / Piping Renk Paleti
ARKA_PLAN = get_color_from_hex("#1E2022")       
BORU_MAVİSİ = get_color_from_hex("#2980B9")     
FORM_RENGI = get_color_from_hex("#2C3E50")      
YAZI_RENGI = get_color_from_hex("#ECF0F1")      
BUTON_YESIL = get_color_from_hex("#27AE60")     
BUTON_KIRMIZI = get_color_from_hex("#C0392B")    
BUTON_PASIF = get_color_from_hex("#7F8C8D")     

# Global Durum Değişkenleri
AKTIF_KULLANICI = "Bilinmeyen"
KULLANICI_ROLÜ = "personel" 

class RenkliKutu(BoxLayout):
    def __init__(self, bg_color, radius=[10], **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=radius)
        self.bind(pos=self.guncelle, size=self.guncelle)
    def guncelle(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# --- 1. EKRAN: SİSTEM GİRİŞ EKRANI ---
class GirisEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        duzen = BoxLayout(orientation='vertical', padding=40, spacing=15)
        
        duzen.add_widget(Label(
            text="⚙️\nPIPING TRACKER\nPROJE TAKİP SİSTEMİ GİRİŞİ", 
            font_size='22sp', bold=True, color=BORU_MAVİSİ, halign="center", size_hint_y=0.3
        ))
        
        form_alani = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=15, spacing=10, size_hint_y=0.4)
        self.input_kullanici = TextInput(hint_text="Kullanıcı Adı", multiline=False, font_size='16sp', write_tab=False)
        self.input_sifre = TextInput(hint_text="Şifre", password=True, multiline=False, font_size='16sp', write_tab=False)
        self.lbl_hata = Label(text="Proje personeli giriş bilgilerini giriniz.\n(Tüm personeller ortak proje havuzuna kayıt girebilir)", color=YAZI_RENGI, font_size='13sp', size_hint_y=0.2, halign="center")
        
        form_alani.add_widget(self.input_kullanici)
        form_alani.add_widget(self.input_sifre)
        form_alani.add_widget(self.lbl_hata)
        duzen.add_widget(form_alani)
        
        btn_giris = Button(text="SİSTEME GİRİŞ YAP", background_normal='', background_color=BORU_MAVİSİ, color=(1,1,1,1), bold=True, font_size='16sp', size_hint_y=0.1)
        btn_giris.bind(on_press=self.bulut_giris_kontrol_thread)
        duzen.add_widget(btn_giris)
        duzen.add_widget(BoxLayout(size_hint_y=0.2))
        self.add_widget(duzen)

    def bulut_giris_kontrol_thread(self, instance):
        threading.Thread(target=self.bulut_giris_kontrol).start()

    def bulut_giris_kontrol(self):
        global AKTIF_KULLANICI, KULLANICI_ROLÜ
        kullanici = self.input_kullanici.text.strip().lower()
        sifre = self.input_sifre.text.strip()
        
        if not kullanici or not sifre:
            Clock.schedule_once(lambda dt: self.HataSetEt("HATA: Alanlar boş bırakılamaz!", BUTON_KIRMIZI))
            return
            
        Clock.schedule_once(lambda dt: self.HataSetEt("Proje sunucusuna bağlanılıyor...", BORU_MAVİSİ))
        
        # 🔑 ADMİN DOĞRUDAN GEÇİŞ YAMASI:
        if kullanici == "admin" and sifre == "1234":
            AKTIF_KULLANICI = "admin"
            KULLANICI_ROLÜ = "yonetici"
            try:
                admin_data = {"sifre": "1234", "rol": "yonetici"}
                requests.put(f"{FIREBASE_URL}kullanicilar/admin.json", json=admin_data, timeout=5)
            except:
                pass
            Clock.schedule_once(self.GirisBasariliGecis)
            return

        # Firebase Personel Giriş Kontrolü
        req_url = f"{FIREBASE_URL}kullanicilar/{kullanici}.json"
        try:
            response = requests.get(req_url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result and isinstance(result, dict) and result.get("sifre") == sifre:
                    AKTIF_KULLANICI = kullanici
                    KULLANICI_ROLÜ = result.get("rol", "personel")
                    Clock.schedule_once(self.GirisBasariliGecis)
                else:
                    Clock.schedule_once(lambda dt: self.HataSetEt("HATA: Kullanıcı adı veya şifre yanlış!", BUTON_KIRMIZI))
            else:
                Clock.schedule_once(lambda dt: self.HataSetEt("Sunucu hatası! Yanıt alınamadı.", BUTON_KIRMIZI))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.HataSetEt(f"Bağlantı Hatası: {str(e)[:30]}", BUTON_KIRMIZI))

    def HataSetEt(self, metin, renk):
        self.lbl_hata.text = metin
        self.lbl_hata.color = renk

    def GirisBasariliGecis(self, dt):
        self.lbl_hata.text = "Giriş Başarılı!"
        self.lbl_hata.color = BUTON_YESIL
        
        ana_sayfa = self.manager.get_screen('ana_ekran')
        ana_sayfa.görünüm_ayarla() 
        
        self.manager.current = 'ana_ekran'
        if hasattr(ana_sayfa, 'tum_listele_click_thread'):
            ana_sayfa.tum_listele_click_thread(None)

# --- 2. EKRAN: BORULAMA VE PROJE TAKİP ANA EKRANI ---
class AnaTakipEkrani(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secili_kayit_id = None
        self.tum_bulut_verisi = {} 
        
        self.ana_duzen = BoxLayout(orientation='vertical', padding=10, spacing=8)
        
        self.lbl_durum = Label(text="PIPING TRACKER | CANLI BAĞLANTI", size_hint_y=0.04, color=BORU_MAVİSİ, bold=True, font_size='13sp')
        self.ana_duzen.add_widget(self.lbl_durum)
        
        # Sadeleştirilmiş Borulama Alanları
        form_kartı = RenkliKutu(bg_color=FORM_RENGI, orientation='vertical', padding=8, spacing=5, size_hint_y=0.25)
        self.input_hat_no = TextInput(hint_text="İzometrik Hat Numarası / Line No (* Zorunlu)", multiline=False, font_size='14sp')
        self.input_cap = TextInput(hint_text="Boru Çapı (İnç / DN)", multiline=False, font_size='14sp')
        self.input_lokasyon = TextInput(hint_text="Ünite / Lokasyon / Alan (* Zorunlu)", multiline=False, font_size='14sp')
        self.input_ilerleme = TextInput(hint_text="Montaj İlerleme Yüzdesi (Örn: %75) (* Zorunlu)", multiline=False, font_size='14sp')
        
        form_kartı.add_widget(self.input_hat_no)
        form_kartı.add_widget(self.input_cap)
        form_kartı.add_widget(self.input_lokasyon)
        form_kartı.add_widget(self.input_ilerleme)
        self.ana_duzen.add_widget(form_kartı)
        
        # İşlem Butonları
        islem_butonlari = BoxLayout(orientation='horizontal', size_hint_y=0.05, spacing=6)
        self.btn_ekle = Button(text="PROJEYE KAYDET", background_normal='', background_color=BUTON_YESIL, font_size='12sp', bold=True)
        self.btn_ekle.bind(on_press=lambda inst: threading.Thread(target=self.hat_ekle_click).start())
        self.btn_guncelle = Button(text="REVİZYON / GÜNCELLE", background_normal='', background_color=BORU_MAVİSİ, font_size='12sp', bold=True)
        self.btn_guncelle.bind(on_press=lambda inst: threading.Thread(target=self.hat_guncelle_click).start())
        self.btn_sil = Button(text="HATTI SİL", background_normal='', background_color=BUTON_KIRMIZI, font_size='12sp', bold=True)
        self.btn_sil.bind(on_press=lambda inst: threading.Thread(target=self.hat_sil_click).start())
        
        islem_butonlari.add_widget(self.btn_ekle)
        islem_butonlari.add_widget(self.btn_guncelle)
        islem_butonlari.add_widget(self.btn_sil)
        self.ana_duzen.add_widget(islem_butonlari)
        
        # Arama Alanı
        arama_duzeni = BoxLayout(orientation='horizontal', spacing=6, size_hint_y=0.05)
        self.input_arama = TextInput(hint_text="Line No veya Lokasyon yazarak ARA...", multiline=False, font_size='14sp', size_hint_x=0.75)
        btn_ara = Button(text="ARA", background_normal='', background_color=BORU_MAVİSİ, font_size='12sp', bold=True, size_hint_x=0.25, color=(1,1,1,1))
        btn_ara.bind(on_press=self.arama_yap_click)
        arama_duzeni.add_widget(self.input_arama)
        arama_duzeni.add_widget(btn_ara)
        self.ana_duzen.add_widget(arama_duzeni)
        
        # Filtre ve Excel Çıktı Alanları
        liste_buton_duzeni = BoxLayout(orientation='horizontal', size_hint_y=0.05, spacing=6)
        btn_tum_liste = Button(text="Yenile / Listele", background_normal='', background_color=get_color_from_hex("#7F8C8D"), font_size='11sp', bold=True)
        btn_tum_liste.bind(on_press=self.tum_listele_click_thread)
        btn_kritik_liste = Button(text="✅ Tamamlananlar (%100)", background_normal='', background_color=get_color_from_hex("#27AE60"), font_size='11sp', bold=True)
        btn_kritik_liste.bind(on_press=self.tamamlananlari_listele_click)
        btn_excel = Button(text="📊 Excel Proje Çıktısı", background_normal='', background_color=get_color_from_hex("#16A085"), font_size='11sp', bold=True)
        btn_excel.bind(on_press=self.excel_cikti_al_click)
        
        liste_buton_duzeni.add_widget(btn_tum_liste)
        liste_buton_duzeni.add_widget(btn_kritik_liste)
        liste_buton_duzeni.add_widget(btn_excel)
        self.ana_duzen.add_widget(liste_buton_duzeni)
        
        # Raporlama Ekranı
        liste_kartı = RenkliKutu(bg_color=get_color_from_hex("#2C3E50"), orientation='vertical', padding=8, size_hint_y=0.38)
        scroll = ScrollView(bar_width=8)
        self.lbl_liste = Label(text="Proje hatları yükleniyor...", size_hint_y=None, halign="left", valign="top", font_size='13sp', color=YAZI_RENGI)
        self.lbl_liste.bind(texture_size=self.lbl_liste.setter('size'))
        scroll.add_widget(self.lbl_liste)
        liste_kartı.add_widget(scroll)
        self.ana_duzen.add_widget(liste_kartı)

        # ⚙️ SAHA PERSONELİ ATAMA PANELİ (Yalnızca Admin Girişinde Görünür)
        self.admin_paneli = RenkliKutu(bg_color=get_color_from_hex("#111D2A"), orientation='vertical', padding=6, spacing=4, size_hint_y=0.22)
        self.admin_paneli.add_widget(Label(text="⚙️ PROJE YÖNETİCİSİ SAHA PERSONELİ ATAMA PANELİ", font_size='11sp', bold=True, color=BORU_MAVİSİ))
        
        admin_input_duzen = BoxLayout(orientation='horizontal', spacing=5)
        self.input_yeni_kullanici = TextInput(hint_text="Yeni Personel Kul. Adı", multiline=False, font_size='12sp')
        self.input_yeni_sifre = TextInput(hint_text="Giriş Şifresi", multiline=False, font_size='12sp')
        admin_input_duzen.add_widget(self.input_yeni_kullanici)
        admin_input_duzen.add_widget(self.input_yeni_sifre)
        self.admin_paneli.add_widget(admin_input_duzen)
        
        admin_btn_duzen = BoxLayout(orientation='horizontal', spacing=5)
        btn_kul_ekle = Button(text="PERSONEL HESABI AÇ", background_normal='', background_color=BUTON_YESIL, font_size='11sp', bold=True)
        btn_kul_ekle.bind(on_press=lambda inst: threading.Thread(target=self.kullanici_ekle_click).start())
        btn_kul_sil = Button(text="PERSONEL YETKİSİ İPTAL", background_normal='', background_color=BUTON_KIRMIZI, font_size='11sp', bold=True)
        btn_kul_sil.bind(on_press=lambda inst: threading.Thread(target=self.kullanici_sil_click).start())
        
        admin_btn_duzen.add_widget(btn_kul_ekle)
        admin_btn_duzen.add_widget(btn_kul_sil)
        self.admin_paneli.add_widget(admin_btn_duzen)
        
        self.add_widget(self.ana_duzen)

    def görünüm_ayarla(self):
        global KULLANICI_ROLÜ, AKTIF_KULLANICI
        if self.admin_paneli in self.ana_duzen.children:
            self.ana_duzen.remove_widget(self.admin_paneli)
            
        if KULLANICI_ROLÜ == "yonetici":
            self.lbl_durum.text = f"PROJE YÖNETİCİSİ PANELİ | AKTİF: {AKTIF_KULLANICI.upper()}"
            self.lbl_durum.color = BORU_MAVİSİ
            self.ana_duzen.children[0].size_hint_y = 0.20 
            self.ana_duzen.add_widget(self.admin_paneli)
            
            self.btn_guncelle.disabled = False
            self.btn_guncelle.background_color = BORU_MAVİSİ
            self.btn_sil.disabled = False
            self.btn_sil.background_color = BUTON_KIRMIZI
        else:
            self.lbl_durum.text = f"SAHA VERİ GİRİŞ PANELİ | AKTİF: {AKTIF_KULLANICI.upper()}"
            self.lbl_durum.color = YAZI_RENGI
            self.ana_duzen.children[0].size_hint_y = 0.43 
            
            self.btn_guncelle.disabled = True
            self.btn_guncelle.background_color = BUTON_PASIF
            self.btn_sil.disabled = True
            self.btn_sil.background_color = BUTON_PASIF

    def kullanici_ekle_click(self):
        yeni_k = self.input_yeni_kullanici.text.strip().lower()
        yeni_s = self.input_yeni_sifre.text.strip()
        
        if not yeni_k or not yeni_s:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Kullanıcı adı ve şifre boş bırakılamaz!", BUTON_KIRMIZI))
            return
            
        kullanici_verisi = {"sifre": yeni_s, "rol": "personel"}
        try:
            res = requests.put(f"{FIREBASE_URL}kullanicilar/{yeni_k}.json", json=kullanici_verisi, timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(lambda dt: self.DurumGuncelle(f"BAŞARILI: '{yeni_k}' personeli sisteme tanımlandı.", BUTON_YESIL))
                Clock.schedule_once(lambda dt: self.admin_form_temizle())
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("Bulut hatası oluştu!", BUTON_KIRMIZI))

    def kullanici_sil_click(self):
        sil_k = self.input_yeni_kullanici.text.strip().lower()
        if not sil_k:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Yetkisi alınacak personel adını yazın!", BUTON_KIRMIZI))
            return
        if sil_k == "admin":
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Ana admin hesabı silinemez!", BUTON_KIRMIZI))
            return
            
        try:
            res = requests.delete(f"{FIREBASE_URL}kullanicilar/{sil_k}.json", timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(lambda dt: self.DurumGuncelle(f"SİLİNDİ: '{sil_k}' personelinin girişi kapatıldı.", BUTON_YESIL))
                Clock.schedule_once(lambda dt: self.admin_form_temizle())
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("Buluttan silme başarısız!", BUTON_KIRMIZI))

    def admin_form_temizle(self):
        self.input_yeni_kullanici.text = ""
        self.input_yeni_sifre.text = ""

    def DurumGuncelle(self, metin, renk):
        self.lbl_durum.text = metin
        self.lbl_durum.color = renk

    def formu_temizle(self):
        self.input_hat_no.text = ""
        self.input_cap.text = ""
        self.input_lokasyon.text = ""
        self.input_ilerleme.text = ""
        self.secili_kayit_id = None

    def zorunlu_alan_kontrolu(self):
        if (not self.input_hat_no.text.strip() or not self.input_lokasyon.text.strip() or 
            not self.input_ilerleme.text.strip()):
            return False
        return True

    def hat_ekle_click(self):
        global AKTIF_KULLANICI
        if not self.zorunlu_alan_kontrolu():
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Zorunlu alanları (Line No, Lokasyon, İlerleme) doldurun!", BUTON_KIRMIZI))
            return
            
        yeni_kayit = {
            "hat_no": self.input_hat_no.text.strip(),
            "cap": self.input_cap.text.strip(),
            "lokasyon": self.input_lokasyon.text.strip(),
            "ilerleme": self.input_ilerleme.text.strip(),
            "guncelleyen_kullanici": AKTIF_KULLANICI,
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        
        try:
            res = requests.post(f"{FIREBASE_URL}kayitlar.json", json=yeni_kayit, timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(self.islem_basarili)
            else:
                Clock.schedule_once(lambda dt: self.DurumGuncelle("SUNUCU HATASI: Kayıt başarısız.", BUTON_KIRMIZI))
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("BAĞLANTI HATASI: İnternet yok.", BUTON_KIRMIZI))

    def hat_guncelle_click(self):
        global KULLANICI_ROLÜ, AKTIF_KULLANICI
        if KULLANICI_ROLÜ != "yonetici":
            return
            
        if not self.secili_kayit_id:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Önce ARA panelinden bir hat seçin!", BUTON_KIRMIZI))
            return
        if not self.zorunlu_alan_kontrolu():
            return
            
        guncel_kayit = {
            "hat_no": self.input_hat_no.text.strip(),
            "cap": self.input_cap.text.strip(),
            "lokasyon": self.input_lokasyon.text.strip(),
            "ilerleme": self.input_ilerleme.text.strip(),
            "guncelleyen_kullanici": AKTIF_KULLANICI,
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        try:
            res = requests.patch(f"{FIREBASE_URL}kayitlar/{self.secili_kayit_id}.json", json=guncel_kayit, timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(self.islem_basarili)
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("BAĞLANTI HATASI!", BUTON_KIRMIZI))

    def hat_sil_click(self):
        global KULLANICI_ROLÜ
        if KULLANICI_ROLÜ != "yonetici":
            return
            
        if not self.secili_kayit_id:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("HATA: Silinecek hattı seçmediniz!", BUTON_KIRMIZI))
            return
        try:
            res = requests.delete(f"{FIREBASE_URL}kayitlar/{self.secili_kayit_id}.json", timeout=10)
            if res.status_code == 200:
                Clock.schedule_once(self.islem_basarili)
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("BAĞLANTI HATASI!", BUTON_KIRMIZI))

    def islem_basarili(self, dt):
        self.lbl_durum.text = "İŞLEM BAŞARILI: Proje veri havuzu güncellendi."
        self.lbl_durum.color = BUTON_YESIL
        self.formu_temizle()
        self.tum_listele_click_thread(None)

    def tum_listele_click_thread(self, instance):
        Clock.schedule_once(lambda dt: self.ListeDurumSetEt("Canlı veri havuzu güncelleniyor..."))
        threading.Thread(target=self.tum_listele_click).start()

    def ListeDurumSetEt(self, metin):
        self.lbl_liste.text = metin

    def tum_listele_click(self):
        try:
            res = requests.get(f"{FIREBASE_URL}kayitlar.json", timeout=10)
            result = res.json()
            Clock.schedule_once(lambda dt: self.listeleme_yap(result))
        except:
            Clock.schedule_once(lambda dt: self.DurumGuncelle("Veri çekme hatası!", BUTON_KIRMIZI))

    def listeleme_yap(self, result):
        if not result:
            self.lbl_liste.text = "Proje havuzunda henüz girilmiş bir borulama hattı yok."
            self.tum_bulut_verisi = {}
            return
            
        self.tum_bulut_verisi = result
        rapor = f"--- TÜM PROJE BORULAMA LİSTESİ ({len(result)} Hat) ---\n\n"
        for k_id, v in result.items():
            rapor += f"📍 Line No: {v.get('hat_no')} | 📐 Çap: {v.get('cap','-')}\n  🌍 Alan/Ünite: {v.get('lokasyon')} | 📊 İlerleme: {v.get('ilerleme')}\n  👷 Kaydeden: {v.get('guncelleyen_kullanici','-')} [{v.get('tarih','')}]\n\n"
        self.lbl_liste.text = rapor

    def arama_yap_click(self, instance):
        kriter = self.input_arama.text.strip().lower()
        if not kriter or not self.tum_bulut_verisi:
            self.lbl_liste.text = "Arama kriteri (Line No veya Ünite) girin veya listeyi yenileyin."
            return
            
        bulunanlar = []
        for k_id, v in self.tum_bulut_verisi.items():
            if (kriter in v.get('hat_no','').lower() or 
                kriter in v.get('lokasyon','').lower()):
                bulunanlar.append((k_id, v))
                
        if not bulunanlar:
            self.lbl_liste.text = f"'{kriter}' kriterine uygun hat bulunamadı."
            self.secili_kayit_id = None
            return
            
        if len(bulunanlar) == 1:
            k_id, v = bulunanlar[0]
            
            global KULLANICI_ROLÜ
            if KULLANICI_ROLÜ == "yonetici":
                self.secili_kayit_id = k_id
                self.input_hat_no.text = v.get('hat_no','')
                self.input_cap.text = v.get('cap','')
                self.input_lokasyon.text = v.get('lokasyon','')
                self.input_ilerleme.text = v.get('ilerleme','')
                self.lbl_durum.text = f"DÜZENLEME MODU AKTİF"
                self.lbl_durum.color = BORU_MAVİSİ
            else:
                self.lbl_durum.text = f"HAT İNCELENİYOR (REVİZYON YETKİNİZ YOK)"
                self.lbl_durum.color = BUTON_PASIF
            
        rapor = f"--- ARAMA SONUÇLARI ({len(bulunanlar)} Hat) ---\n\n"
        for k_id, v in bulunanlar:
            rapor += f"📍 Line No: {v.get('hat_no')} | 📐 Çap: {v.get('cap','-')} | 🌍 Ünite: {v.get('lokasyon')} | 📊 İlerleme: {v.get('ilerleme')}\n\n"
        self.lbl_liste.text = rapor

    def tamamlananlari_listele_click(self, instance):
        if not self.tum_bulut_verisi:
            self.lbl_liste.text = "Lütfen önce listeyi yenileyin."
            return
        rapor = ""
        sayac = 0
        for k_id, v in self.tum_bulut_verisi.items():
            ilerleme_str = v.get('ilerleme', '').replace('%', '').strip()
            if ilerleme_str == "100":
                sayac += 1
                rapor += f"✅ Line No: {v.get('hat_no')} | 📐 Çap: {v.get('cap','-')} | 🌍 Ünite: {v.get('lokasyon')} | Durum: MONTAJ TAMAM!\n\n"
        self.lbl_liste.text = f"--- ⚡ MONTAJI BİTEN HATLAR ({sayac} Adet) ---\n\n" + (rapor if rapor else "Henüz %100 tamamlanan hat yok.")

    def excel_cikti_al_click(self, instance):
        if not self.tum_bulut_verisi:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "Piping Tracker Proje Raporu"
        ws.append(["Kayıt Bulut ID", "İzometrik Hat No (Line)", "Boru Çapı", "Lokasyon / Ünite", "İlerleme Yüzdesi", "Son Güncelleyen", "Son Güncelleme Tarihi"])
        
        for k_id, v in self.tum_bulut_verisi.items():
            ws.append([k_id, v.get('hat_no'), v.get('cap'), v.get('lokasyon'), v.get('ilerleme'), v.get('guncelleyen_kullanici'), v.get('tarih')])
            
        try:
            if platform == 'android':
                from android.storage import primary_external_storage_path
                kayit_yolu = os.path.join(primary_external_storage_path(), 'Download', 'Piping_Tracker_Proje_Raporu.xlsx')
            else:
                kayit_yolu = 'Piping_Tracker_Proje_Raporu.xlsx'
            wb.save(kayit_yolu)
            self.lbl_durum.text = "Excel İndirilenlere Aktarıldı!"
            self.lbl_durum.color = BUTON_YESIL
        except Exception as e:
            self.lbl_durum.text = "Excel Dosya Hatası!"

class PipingTrackerApp(App):
    def build(self):
        self.title = "Piping Tracker - Proje Takip Otomasyonu"
        sm = ScreenManager()
        sm.add_widget(GirisEkrani(name='giris_ekrani'))
        sm.add_widget(AnaTakipEkrani(name='ana_ekran'))
        sm.current = 'giris_ekrani'
        return sm

if __name__ == "__main__":
    Window.clearcolor = ARKA_PLAN
    PipingTrackerApp().run()
