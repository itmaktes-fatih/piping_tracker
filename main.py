import os
os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'  # Windows için en kararlı ekran kartı modu

import sqlite3
import csv
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

# --- ENDÜSTRİYEL RENK PALETİ ---
ARKA_PLAN = get_color_from_hex("#111625")       
ISG_SARISI = get_color_from_hex("#F39C12")      
KART_RENGI = get_color_from_hex("#1A2238")      
YAZI_RENGI = get_color_from_hex("#ECF0F1")      
BUTON_YESIL = get_color_from_hex("#27AE60")     
BUTON_MAVI = get_color_from_hex("#2980B9")      
BUTON_KIRMIZI = get_color_from_hex("#C0392B")    
BUTON_GRI = get_color_from_hex("#7F8C8D")

def get_db_path():
    try:
        app = App.get_running_app()
        if app and app.user_data_dir:
            return os.path.join(app.user_data_dir, "piping_qaqc_v3.db")
    except:
        pass
    return "piping_qaqc_v3.db"

def veritabanini_hazirla():
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # 1. Ana Projeler Tablosu
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ana_projeler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proje_adi TEXT UNIQUE,
        durum TEXT DEFAULT 'Aktif'
    )
    """)
    
    # 2. Hatlar Tablosu (Proje Kırılımlı)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projeler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proje_id INTEGER,
        project_name TEXT,
        line_no TEXT UNIQUE,
        iso_no TEXT,
        rev TEXT,
        material_grade TEXT,
        wps_no TEXT,
        fitup_status TEXT,
        ndt_result TEXT,
        punch_status TEXT,
        FOREIGN KEY(proje_id) REFERENCES ana_projeler(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Weld Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weld_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_no TEXT,
        weld_no TEXT,
        weld_type TEXT,
        fitup_date TEXT,
        weld_date TEXT,
        test_pressure TEXT,
        spec_no TEXT,
        FOREIGN KEY(line_no) REFERENCES projeler(line_no) ON DELETE CASCADE
    )
    """)
    
    # 4. Punch Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS punch_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        line_no TEXT,
        punch_type TEXT,
        description TEXT,
        punch_status TEXT,
        FOREIGN KEY(line_no) REFERENCES projeler(line_no) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

# Kivy Tasarım Moduyla Tam Uyumlu Renkli Kart Sınıfı
class RenkliKart(BoxLayout):
    bg_color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[8])
        self.bind(pos=self.guncelle, size=self.guncelle)

    def guncelle(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# --- 1. EKRAN: ANA PANEL ---
class MainMenuScreen(Screen):
    def on_enter(self):
        veritabanini_hazirla()

    def yeni_proje_popup(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.p_input = TextInput(hint_text="Proje Adı Girin (Örn: Rafineri Tank Sahası)", multiline=False)
        btn_kaydet = Button(text="KAYDET", background_normal='', background_color=BUTON_YESIL, bold=True)
        layout.add_widget(self.p_input)
        layout.add_widget(btn_kaydet)
        
        popup = Popup(title='Yeni Proje Kaydı', content=layout, size_hint=(0.8, 0.4))
        btn_kaydet.bind(on_press=lambda x: self.proje_kaydet(popup))
        popup.open()

    def proje_kaydet(self, popup):
        p_adi = self.p_input.text.strip()
        if p_adi:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO ana_projeler (proje_adi) VALUES (?)", (p_adi,))
                conn.commit()
            except:
                pass
            conn.close()
        popup.dismiss()

# --- 2. EKRAN: PROJE LİSTE EKRANI ---
class ProjectListScreen(Screen):
    def liste_yukle(self, mod):
        self.mod = mod 
        self.ids.lbl_baslik.text = f"{mod.upper()} PROJELER"
        self.ids.liste_container.clear_widgets()
        
        veritabanini_hazirla()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT id, proje_adi FROM ana_projeler WHERE durum = ?", (mod,))
        projeler = cursor.fetchall()
        conn.close()
        
        for p_id, p_adi in projeler:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=5)
            btn = Button(text=p_adi, background_normal='', background_color=KART_RENGI, halign='left', valign='middle')
            btn.bind(on_press=lambda x, pid=p_id, pname=p_adi: self.proje_sec(pid, pname))
            row.add_widget(btn)
            self.ids.liste_container.add_widget(row)

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

    def proje_durum_kontrol(self):
        app = App.get_running_app()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT durum FROM ana_projeler WHERE id = ?", (app.secili_proje_id,))
        durum = cursor.fetchone()
        conn.close()
        if durum and durum[0] == 'Biten':
            self.ids.btn_proje_bitir.text = "PROJEYİ AKTİFE AL"
            self.ids.btn_proje_bitir.background_color = ISG_SARISI
        else:
            self.ids.btn_proje_bitir.text = "PROJEYİ TAMAMLANDI YAP"
            self.ids.btn_proje_bitir.background_color = BUTON_KIRMIZI

    def proje_bitir_click(self):
        app = App.get_running_app()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        if self.ids.btn_proje_bitir.text == "PROJEYİ TAMAMLANDI YAP":
            cursor.execute("UPDATE ana_projeler SET durum = 'Biten' WHERE id = ?", (app.secili_proje_id,))
        else:
            cursor.execute("UPDATE ana_projeler SET durum = 'Aktif' WHERE id = ?", (app.secili_proje_id,))
        conn.commit()
        conn.close()
        self.manager.current = 'ana_menu'

    def hat_kaydet_click(self):
        app = App.get_running_app()
        lno = self.ids.input_lno.text.strip()
        if not lno: return
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO projeler (proje_id, project_name, line_no, iso_no, rev, material_grade, wps_no, fitup_status, ndt_result, punch_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (app.secili_proje_id, self.ids.input_pname.text, lno, self.ids.input_isono.text, self.ids.input_rev.text, self.ids.input_mat.text, self.ids.input_wps.text, self.ids.input_fitup.text, self.ids.input_ndt.text, self.ids.input_pstatus.text))
        conn.commit()
        conn.close()
        app.secili_line_no = lno
        self.hat_listele()
        self.form_temizle()

    def hat_sil(self, line_no):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projeler WHERE line_no = ?", (line_no,))
        conn.commit()
        conn.close()
        if App.get_running_app().secili_line_no == line_no:
            App.get_running_app().secili_line_no = None
            self.ids.lbl_secili_hat_ust.text = "⚠️ SEÇİLİ HAT MENÜSÜ (TIKLA)"
            self.ids.lbl_weld_liste.text = "Lütfen yukarıdan bir hat seçip işlem yapın..."
        self.hat_listele()

    def hat_duzenle(self, line_no):
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projeler WHERE line_no = ?", (line_no,))
        s = cursor.fetchone()
        conn.close()
        if s:
            self.ids.input_pname.text = s[2] or ""
            self.ids.input_lno.text = s[3] or ""
            self.ids.input_isono.text = s[4] or ""
            self.ids.input_rev.text = s[5] or ""
            self.ids.input_mat.text = s[6] or ""
            self.ids.input_wps.text = s[7] or ""
            self.ids.input_fitup.text = s[8] or ""
            self.ids.input_ndt.text = s[9] or ""
            self.ids.input_pstatus.text = s[10] or ""

    def hat_listele(self):
        app = App.get_running_app()
        self.ids.hat_list_container.clear_widgets()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT line_no, iso_no FROM projeler WHERE proje_id = ?", (app.secili_proje_id,))
        satirlar = cursor.fetchall()
        conn.close()
        
        for s in satirlar:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=5)
            btn_sec = Button(text=f"📍 {s[0]} (Iso: {s[1]})", background_normal='', background_color=KART_RENGI, halign='left')
            btn_sec.bind(on_press=lambda x, lno=s[0]: self.hat_hizli_sec(lno))
            
            btn_edit = Button(text="DÜZENLE", size_hint_x=0.2, background_normal='', background_color=BUTON_MAVI)
            btn_edit.bind(on_press=lambda x, lno=s[0]: self.hat_duzenle(lno))
            
            btn_del = Button(text="SİL", size_hint_x=0.15, background_normal='', background_color=BUTON_KIRMIZI)
            btn_del.bind(on_press=lambda x, lno=s[0]: self.hat_sil(lno))
            
            row.add_widget(btn_sec)
            row.add_widget(btn_edit)
            row.add_widget(btn_del)
            self.ids.hat_list_container.add_widget(row)

    def hat_hizli_sec(self, lno):
        App.get_running_app().secili_line_no = lno
        self.ids.lbl_secili_hat_ust.text = f"Seçili Hat: {lno}"
        self.weld_ve_punch_listele()

    def hat_secim_popup_ac(self):
        app = App.get_running_app()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        scroll = ScrollView()
        list_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        list_box.bind(minimum_height=list_box.setter('height'))
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT line_no FROM projeler WHERE proje_id = ?", (app.secili_proje_id,))
        hatlar = cursor.fetchall()
        conn.close()
        
        popup = Popup(title='Sistemde Kayıtlı Hatlar', content=layout, size_hint=(0.9, 0.7))
        
        for h in hatlar:
            b = Button(text=h[0], size_hint_y=None, height=45, background_normal='', background_color=KART_RENGI)
            b.bind(on_press=lambda x, lno=h[0]: [self.hat_hizli_sec(lno), popup.dismiss()])
            list_box.add_widget(b)
            
        scroll.add_widget(list_box)
        layout.add_widget(scroll)
        popup.open()

    def hat_arama_popup_ac(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        inp_ara = TextInput(hint_text="Aranacak Hat No Yazın...", multiline=False)
        scroll = ScrollView()
        sonuc_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        sonuc_box.bind(minimum_height=sonuc_box.setter('height'))
        
        layout.add_widget(inp_ara)
        layout.add_widget(scroll)
        scroll.add_widget(sonuc_box)
        
        popup = Popup(title='Gelişmiş Hat Arama', content=layout, size_hint=(0.9, 0.8))
        
        def arama_yap(*args):
            sonuc_box.clear_widgets()
            txt = inp_ara.text.strip()
            if not txt: return
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT line_no FROM projeler WHERE proje_id = ? AND line_no LIKE ?", (App.get_running_app().secili_proje_id, f"%{txt}%"))
            res = cursor.fetchall()
            conn.close()
            for r in res:
                b = Button(text=r[0], size_hint_y=None, height=45, background_normal='', background_color=KART_RENGI)
                b.bind(on_press=lambda x, lno=r[0]: [self.hat_hizli_sec(lno), popup.dismiss()])
                sonuc_box.add_widget(b)
                
        inp_ara.bind(text=arama_yap)
        popup.open()

    def weld_ekle_click(self):
        app = App.get_running_app()
        if not app.secili_line_no or not self.ids.input_wno.text: return
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO weld_logs (line_no, weld_no, weld_type, fitup_date, weld_date, test_pressure, spec_no) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (app.secili_line_no, self.ids.input_wno.text, self.ids.input_wtype.text, self.ids.input_fdate.text, self.ids.input_wdate.text, self.ids.input_tpress.text, self.ids.input_spec.text))
        conn.commit()
        conn.close()
        self.weld_ve_punch_listele()
        self.ids.input_wno.text = ""

    def punch_ekle_click(self):
        app = App.get_running_app()
        if not app.secili_line_no or not self.ids.input_ptype.text: return
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("INSERT INTO punch_logs (line_no, punch_type, description, punch_status) VALUES (?, ?, ?, 'Open')", (app.secili_line_no, self.ids.input_ptype.text, self.ids.input_pdesc.text))
        conn.commit()
        conn.close()
        self.weld_ve_punch_listele()
        self.ids.input_ptype.text = ""
        self.ids.input_pdesc.text = ""

    def punch_kapat_click(self):
        p_id = self.ids.input_punch_kapat_id.text.strip()
        if not p_id: return
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("UPDATE punch_logs SET punch_status = 'Kapalı' WHERE id = ?", (p_id,))
        conn.commit()
        conn.close()
        self.ids.input_punch_kapat_id.text = ""
        self.weld_ve_punch_listele()

    def weld_ve_punch_listele(self):
        app = App.get_running_app()
        if not app.secili_line_no: return
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT weld_no, weld_type, weld_date FROM weld_logs WHERE line_no = ?", (app.secili_line_no,))
        kaynaklar = cursor.fetchall()
        cursor.execute("SELECT id, punch_type, description, punch_status FROM punch_logs WHERE line_no = ?", (app.secili_line_no,))
        punchlar = cursor.fetchall()
        conn.close()
        
        rapor = f"⚙️ HAT LOG DETAYI: {app.secili_line_no}\n\n[ WELD LOGS ]\n"
        for k in kaynaklar: rapor += f"• W-No: {k[0]} ({k[1]}) | Tarih: {k[2]}\n"
        rapor += "\n[ PUNCH LIST ]\n"
        for p in punchlar: rapor += f"• ID: {p[0]} | Tip: {p[1]} | [{p[3]}] - Detay: {p[2]}\n"
        self.ids.lbl_weld_liste.text = rapor

    def form_temizle(self):
        self.ids.input_pname.text = ""
        self.ids.input_lno.text = ""
        self.ids.input_isono.text = ""
        self.ids.input_rev.text = ""
        self.ids.input_mat.text = ""
        self.ids.input_wps.text = ""
        self.ids.input_fitup.text = ""
        self.ids.input_ndt.text = ""
        self.ids.input_pstatus.text = ""

    def global_csv_cikti_al(self):
        app = App.get_running_app()
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        try:
            klasor = '/sdcard/Download' if os.path.exists('/sdcard/Download') else '.'
            dosya_yolu = os.path.join(klasor, f'{app.secili_proje_adi}_Santiye_Raporu.csv')
            
            with open(dosya_yolu, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([f"=== {app.secili_proje_adi} BORU HATLARI LISTESI ==="])
                writer.writerow(["ID", "ProjeID", "Project Name", "Line No", "Iso No", "Rev", "Material", "WPS", "FitUp", "NDT", "Punch"])
                cursor.execute("SELECT * FROM projeler WHERE proje_id = ?", (app.secili_proje_id,))
                writer.writerows(cursor.fetchall())
                
            self.ids.lbl_proje_ust.text = "Rapor İndirilenler Klasörüne Alındı!"
        except Exception as e:
            self.ids.lbl_proje_ust.text = f"Hata: {str(e)}"
        finally:
            conn.close()

# --- KIVY DESIGN STRING ---
from kivy.lang import Builder
Builder.load_string("""
<MainMenuScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 30
        spacing: 20
        Label:
            text: "PIPING QA/QC MÜHENDİSLİK"
            font_size: '22sp'
            bold: True
            color: 243/255, 156/255, 18/255, 1
            size_hint_y: 0.2
        Button:
            text: "➕ YENİ PROJE KAYIT"
            background_normal: ''
            background_color: 39/255, 174/255, 96/255, 1
            bold: True
            on_press: root.yeni_proje_popup()
        Button:
            text: "🔄 AKTİF PROJELER"
            background_normal: ''
            background_color: 41/255, 128/255, 185/255, 1
            bold: True
            on_press: 
                app.root.current = 'proje_liste'
                app.root.get_screen('proje_liste').liste_yukle('Aktif')
        Button:
            text: "✅ BİTEN PROJELER (ARŞİV)"
            background_normal: ''
            background_color: 127/255, 140/255, 141/255, 1
            bold: True
            on_press: 
                app.root.current = 'proje_liste'
                app.root.get_screen('proje_liste').liste_yukle('Biten')

<ProjectListScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 15
        spacing: 10
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.08
            Button:
                text: "⬅ GERİ"
                size_hint_x: 0.2
                on_press: app.root.current = 'ana_menu'
            Label:
                id: lbl_baslik
                text: "PROJELER"
                bold: True
                font_size: '16sp'
        ScrollView:
            BoxLayout:
                id: liste_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: 5

<HatYonetimScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 8
        
        # ÜST BAR
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.07
            spacing: 5
            Button:
                text: "🏠 ANA"
                size_hint_x: 0.2
                on_press: app.root.current = 'ana_menu'
            Label:
                id: lbl_proje_ust
                text: "PROJE BAŞLIĞI"
                bold: True
                color: 243/255, 156/255, 18/255, 1
            Button:
                id: btn_proje_bitir
                text: "PROJEYİ BİTİR"
                size_hint_x: 0.35
                background_normal: ''
                bold: True
                on_press: root.proje_bitir_click()

        # SEKMELER VE SEÇİLİ HAT BUTONU
        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: 0.06
            spacing: 5
            Button:
                id: lbl_secili_hat_ust
                text: "⚠️ SEÇİLİ HAT MENÜSÜ (TIKLA)"
                background_normal: ''
                background_color: 44/255, 62/255, 80/255, 1
                bold: True
                on_press: root.hat_secim_popup_ac()
            Button:
                text: "🔍 HAT ARA"
                size_hint_x: 0.25
                background_normal: ''
                background_color: 243/255, 156/255, 18/255, 1
                color: 0,0,0,1
                bold: True
                on_press: root.hat_arama_popup_ac()

        # ANA FORM VE LİSTE ALANI
        BoxLayout:
            orientation: 'vertical'
            spacing: 5
            
            # Form Giriş Alanı
            RenkliKart:
                bg_color: 26/255, 34/255, 56/255, 1
                orientation: 'vertical'
                padding: 6
                spacing: 4
                size_hint_y: 0.40
                TextInput:
                    id: input_pname
                    hint_text: "Sub-Project Name / Sistem"
                TextInput:
                    id: input_lno
                    hint_text: "Line No (Zorunlu)"
                TextInput:
                    id: input_isono
                    hint_text: "Iso No"
                TextInput:
                    id: input_rev
                    hint_text: "Revizyon"
                TextInput:
                    id: input_mat
                    hint_text: "Material Grade"
                TextInput:
                    id: input_wps
                    hint_text: "WPS No"
                TextInput:
                    id: input_fitup
                    hint_text: "FitUp Status"
                TextInput:
                    id: input_ndt
                    hint_text: "NDT Result"
                TextInput:
                    id: input_pstatus
                    hint_text: "Punch Status"
            
            BoxLayout:
                orientation: 'horizontal'
                size_hint_y: 0.06
                spacing: 5
                Button:
                    text: "💾 HATTI KAYDET / GÜNCELLE"
                    background_normal: ''
                    background_color: 39/255, 174/255, 96/255, 1
                    bold: True
                    on_press: root.hat_kaydet_click()
                Button:
                    text: "📊 CSV"
                    size_hint_x: 0.2
                    background_normal: ''
                    background_color: 41/255, 128/255, 185/255, 1
                    bold: True
                    on_press: root.global_csv_cikti_al()

            # Kayıtlı Hat Listesi
            ScrollView:
                size_hint_y: 0.24
                BoxLayout:
                    id: hat_list_container
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: 4

            # --- LOGLAMA VE KAYNAK ALANI ---
            BoxLayout:
                orientation: 'horizontal'
                size_hint_y: 0.30
                spacing: 5
                
                # Weld Log Form
                RenkliKart:
                    bg_color: 26/255, 34/255, 56/255, 1
                    orientation: 'vertical'
                    padding: 5
                    spacing: 3
                    TextInput:
                        id: input_wno
                        hint_text: "Weld No"
                    TextInput:
                        id: input_wtype
                        hint_text: "Type (BW/SW)"
                    TextInput:
                        id: input_fdate
                        hint_text: "FitUp Date"
                    TextInput:
                        id: input_wdate
                        hint_text: "Weld Date"
                    TextInput:
                        id: input_tpress
                        hint_text: "Test Press"
                    TextInput:
                        id: input_spec
                        hint_text: "Spec"
                    Button:
                        text: "KAYNAK EKLE"
                        background_normal: ''
                        background_color: 41/255, 128/255, 185/255, 1
                        bold: True
                        size_hint_y: 0.3
                        on_press: root.weld_ekle_click()

                # Punch List Form
                RenkliKart:
                    bg_color: 26/255, 34/255, 56/255, 1
                    orientation: 'vertical'
                    padding: 5
                    spacing: 3
                    TextInput:
                        id: input_ptype
                        hint_text: "Punch Tipi (A/B)"
                    TextInput:
                        id: input_pdesc
                        hint_text: "Açıklama"
                    TextInput:
                        id: input_punch_kapat_id
                        hint_text: "Kapatılacak ID"
                    BoxLayout:
                        orientation: 'horizontal'
                        spacing: 3
                        Button:
                            text: "PUNCH AÇ"
                            background_normal: ''
                            background_color: 192/255, 41/255, 43/255, 1
                            bold: True
                            on_press: root.punch_ekle_click()
                        Button:
                            text: "KAPAT"
                            background_normal: ''
                            background_color: 39/255, 174/255, 96/255, 1
                            bold: True
                            on_press: root.punch_kapat_click()

            # Detay Görüntüleme Alanı
            ScrollView:
                size_hint_y: 0.20
                RenkliKart:
                    bg_color: 26/255, 34/255, 56/255, 1
                    size_hint_y: None
                    height: self.minimum_height
                    padding: 5
                    Label:
                        id: lbl_weld_liste
                        text: "Lütfen yukarıdan bir hat seçip işlem yapın..."
                        size_hint_y: None
                        halign: 'left'
                        valign: 'top'
                        font_size: '12sp'
                        text_size: self.width, None
""")

# --- UYGULAMA YÖNETİCİSİ ---
class PipingQAQCApp(App):
    secili_proje_id = None
    secili_proje_adi = None
    secili_line_no = None

    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='ana_menu'))
        sm.add_widget(ProjectListScreen(name='proje_liste'))
        sm.add_widget(HatYonetimScreen(name='hat_yonetim'))
        return sm

if __name__ == "__main__":
    PipingQAQCApp().run()
