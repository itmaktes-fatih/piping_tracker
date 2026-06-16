import os
# Windows test ortamı için en kararlı ekran kartı arka plan motoru
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'  

import csv
import traceback
import requests  # Firebase REST API için standart ve APK uyumlu kütüphane

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import ListProperty
from kivy.lang import Builder

# --- GÜNCEL FIREBASE BAĞLANTI AYARI ---
FIREBASE_URL = "https://piping-tracker-default-rtdb.europe-west1.firebasedatabase.app/"

# --- ENDÜSTRİYEL QA/QC RENK PALETİ ---
ARKA_PLAN = get_color_from_hex("#111625")       
ISG_SARISI = get_color_from_hex("#F39C12")      
KART_RENGI = get_color_from_hex("#1A2238")      
YAZI_RENGI = get_color_from_hex("#ECF0F1")      
BUTON_YESIL = get_color_from_hex("#27AE60")     
BUTON_MAVI = get_color_from_hex("#2980B9")      
BUTON_KIRMIZI = get_color_from_hex("#C0392B")    
BUTON_GRI = get_color_from_hex("#7F8C8D")

# Kivy Tasarım Moduyla Tam Uyumlu Renkli Kart Sınıfı
class RenkliKart(BoxLayout):
    bg_color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self.color_instruction = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])

        self.bind(pos=self.guncelle, size=self.guncelle, bg_color=self.renk_guncelle)

    def guncelle(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def renk_guncelle(self, *args):
        self.color_instruction.rgba = self.bg_color

# --- 1. EKRAN: ANA PANEL ---
class MainMenuScreen(Screen):
    def yeni_proje_popup(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.p_input = TextInput(hint_text="Proje Adı Girin (Örn: Rafineri)", multiline=False)
        btn_kaydet = Button(text="KAYDET", background_normal='', background_color=BUTON_YESIL, bold=True)
        layout.add_widget(self.p_input)
        layout.add_widget(btn_kaydet)
        
        popup = Popup(title='Yeni Proje Kaydı', content=layout, size_hint=(0.8, 0.4))
        btn_kaydet.bind(on_press=lambda x: self.proje_kaydet(popup))
        popup.open()

    def proje_kaydet(self, popup):
        p_adi = self.p_input.text.strip()
        if p_adi:
            try:
                # Proje adını Firebase'e uygun bir key haline getirmek için temizliyoruz
                safe_key = p_adi.replace(".", "_").replace("$", "_").replace("#", "_")
                data = {"proje_adi": p_adi, "durum": "Aktif"}
                requests.put(f"{FIREBASE_URL}ana_projeler/{safe_key}.json", json=data)
            except Exception as e:
                print("Firebase Hata:", e)
        popup.dismiss()

# --- 2. EKRAN: PROJE LİSTE EKRANI ---
class ProjectListScreen(Screen):
    mod = "Aktif"

    def on_enter(self):
        self.liste_yukle(self.mod)

    def liste_yukle(self, mod):
        self.mod = mod 
        self.ids.lbl_baslik.text = f"{mod.upper()} PROJELER"
        self.ids.liste_container.clear_widgets()
        
        try:
            response = requests.get(f"{FIREBASE_URL}ana_projeler.json")
            projeler = response.json() or {}
            
            for key, val in projeler.items():
                if val.get("durum") == mod:
                    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=5)
                    btn = Button(text=val.get("proje_adi"), background_normal='', background_color=KART_RENGI, halign='left', valign='middle')
                    btn.bind(on_press=lambda x, pid=key, pname=val.get("proje_adi"): self.proje_sec(pid, pname))
                    row.add_widget(btn)
                    self.ids.liste_container.add_widget(row)
        except Exception as e:
            self.ids.lbl_baslik.text = "Bağlantı Hatası!"

    def proje_sec(self, pid, pname):
        app = App.get_running_app()
        app.secili_proje_id = pid
        app.secili_proje_adi = pname
        self.manager.current = 'hat_yonetim'

# --- 3. EKRAN: HAT YÖNETİMİ VE LOG ANA EKRANI ---
class HatYonetimScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        self.ids.lbl_proje_ust.text = f"PROJE: {app.secili_proje_adi}"
        self.hat_listele()
        self.proje_durum_kontrol()
        self.weld_ve_punch_listele()

    def proje_durum_kontrol(self):
        app = App.get_running_app()
        try:
            res = requests.get(f"{FIREBASE_URL}ana_projeler/{app.secili_proje_id}.json").json()
            if res and res.get("durum") == 'Biten':
                self.ids.btn_proje_bitir.text = "PROJEYİ AKTİFE AL"
                self.ids.btn_proje_bitir.background_color = ISG_SARISI
            else:
                self.ids.btn_proje_bitir.text = "PROJEYİ TAMAMLANDI YAP"
                self.ids.btn_proje_bitir.background
