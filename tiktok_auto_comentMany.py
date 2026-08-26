import os
import re
import time
import random
import queue
import threading
import subprocess
import shutil
import uiautomator2 as u2
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


def find_adb_executable():
    """Mencari lokasi adb.exe secara otomatis dari PATH atau folder umum."""
    adb_name = "adb.exe" if os.name == "nt" else "adb"
    adb_path = shutil.which(adb_name)
    if adb_path:
        return adb_path

    candidates = [
        os.path.join(os.path.expanduser("~"), "Downloads", "adb.exe"),
        os.path.join(os.path.expanduser("~"), "Downloads", "platform-tools", "adb.exe"),
        os.path.join("C:\\Program Files\\Android\\Android SDK\\platform-tools", "adb.exe"),
        os.path.join("C:\\Program Files (x86)\\Android\\android-sdk\\platform-tools", "adb.exe"),
        os.path.join("C:\\Program Files\\ASUS\\GlideX", "adb.exe"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


class ThreadSafeConsoleLogger:
    """Mengelola pengiriman log dari berbagai thread ke GUI secara aman (Thread-Safe)."""
    def __init__(self, text_widget):
        self.log_queue = queue.Queue()
        self.text_widget = text_widget
        self.update_gui_loop()

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}\n")

    def update_gui_loop(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.text_widget.insert(tk.END, message)
                self.text_widget.see(tk.END)
        except queue.Empty:
            pass
        self.text_widget.after(100, self.update_gui_loop)


class TikTokCommentManyLabU2:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok Multi-Device Lab - Auto Comment Many Videos Engine")
        self.root.geometry("860x900")
        self.is_running = False
        self.active_threads = []
        
        # Thread Locks & Data Struktur Global
        self.stats_lock = threading.Lock()
        self.comment_lock = threading.Lock()
        
        self.global_clone_count = 0
        self.global_comment_count = 0
        
        self.device_clone_counts = {}
        self.device_comment_counts = {}
        
        self.video_comment_counts = {}      # {v_idx: int}
        self.shared_comments_per_video = {} # {v_idx: list of comments}
        self.video_ui_widgets = {}          # {v_idx: widget_dict}
        self.video_configs = {}             # {v_idx: config_dict}

        self.setup_gui()
        self.logger = ThreadSafeConsoleLogger(self.log_text)
        self.detect_devices_startup()

    def setup_gui(self):
        # 1. Main Scrollable Container untuk seluruh GUI
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_content = tk.Frame(canvas, padx=10, pady=5)

        self.scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel scroll binding
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # -------------------------------------------------------------
        # FRAME 1: TARGET & VIDEO COUNT CONFIGURATION
        # -------------------------------------------------------------
        frame_target = tk.LabelFrame(self.scrollable_content, text=" 1. Target & Video Configuration ", padx=10, pady=8)
        frame_target.pack(fill="x", pady=5)
        
        tk.Label(frame_target, text="Username Akun Target (misal: vionex):").grid(row=0, column=0, sticky="w", pady=3)
        self.entry_url = tk.Entry(frame_target, width=30)
        self.entry_url.grid(row=0, column=1, sticky="w", pady=3, padx=5)
        self.entry_url.insert(0, "vionex")
        
        tk.Label(frame_target, text="Jumlah Video yang Dikomentari per Akun:").grid(row=1, column=0, sticky="w", pady=3)
        self.entry_video_count = tk.Entry(frame_target, width=12)
        self.entry_video_count.grid(row=1, column=1, sticky="w", pady=3, padx=5)
        self.entry_video_count.insert(0, "3")

        btn_generate_video_ui = tk.Button(
            frame_target, 
            text="🔄 Generate / Sesuaikan Form Komentar", 
            bg="#3498db", 
            fg="white", 
            font=("Arial", 9, "bold"),
            command=self.generate_video_comment_forms
        )
        btn_generate_video_ui.grid(row=1, column=2, sticky="w", padx=10)

        tk.Label(frame_target, text="Jeda / Tonton per Video (Detik):").grid(row=2, column=0, sticky="w", pady=3)
        self.entry_watch_delay = tk.Entry(frame_target, width=12)
        self.entry_watch_delay.grid(row=2, column=1, sticky="w", pady=3, padx=5)
        self.entry_watch_delay.insert(0, "6")

        # -------------------------------------------------------------
        # FRAME 2: CLONE APP CONFIGURATION (BY EXACT NAME / NUMBER)
        # -------------------------------------------------------------
        frame_config = tk.LabelFrame(self.scrollable_content, text=" 2. Pengaturan Nama Aplikasi Clone (Pencarian Berdasarkan Nama/Angka) ", padx=10, pady=8)
        frame_config.pack(fill="x", pady=5)

        tk.Label(frame_config, text="Mulai dari Nama/Angka Clone:").grid(row=0, column=0, sticky="w", pady=3)
        self.entry_start_idx = tk.Entry(frame_config, width=15)
        self.entry_start_idx.grid(row=0, column=1, sticky="w", pady=3, padx=5)
        self.entry_start_idx.insert(0, "1")

        tk.Label(frame_config, text="Sampai dengan Nama/Angka Clone:").grid(row=0, column=2, sticky="w", pady=3, padx=(15, 0))
        self.entry_clones = tk.Entry(frame_config, width=15)
        self.entry_clones.grid(row=0, column=3, sticky="w", pady=3, padx=5)
        self.entry_clones.insert(0, "50")

        tk.Label(frame_config, text="Daftar Nama Clone Kustom (Opsional):").grid(row=1, column=0, sticky="w", pady=3)
        self.entry_custom_clones = tk.Entry(frame_config, width=45)
        self.entry_custom_clones.grid(row=1, column=1, columnspan=3, sticky="w", pady=3, padx=5)
        self.entry_custom_clones.insert(0, "")

        tk.Label(frame_config, text="(Biarkan kosong untuk menggunakan Mulai-Sampai, atau isi misal: 1, 2, 11, 12 atau 12-50)", fg="#7f8c8d", font=("Arial", 8, "italic")).grid(row=2, column=1, columnspan=3, sticky="w")

        tk.Label(frame_config, text="Mode Pesawat (Rotasi IP) per berapa Akun:").grid(row=3, column=0, sticky="w", pady=3)
        self.entry_airplane_interval = tk.Entry(frame_config, width=15)
        self.entry_airplane_interval.grid(row=3, column=1, sticky="w", pady=3, padx=5)
        self.entry_airplane_interval.insert(0, "10")

        tk.Label(frame_config, text="(0 = Nonaktifkan Rotasi IP)", fg="#7f8c8d", font=("Arial", 8, "italic")).grid(row=3, column=2, columnspan=2, sticky="w")

        # -------------------------------------------------------------
        # FRAME 3: DYNAMIC PER-VIDEO COMMENT CONFIGURATION
        # -------------------------------------------------------------
        self.frame_dynamic_comments = tk.LabelFrame(self.scrollable_content, text=" 3. Konfigurasi Komentar per Video ", padx=10, pady=8)
        self.frame_dynamic_comments.pack(fill="x", pady=5)

        self.dynamic_videos_container = tk.Frame(self.frame_dynamic_comments)
        self.dynamic_videos_container.pack(fill="x", expand=True)

        # Inisialisasi awal form video (default 3 video)
        self.generate_video_comment_forms()

        # -------------------------------------------------------------
        # FRAME 4: CONTROL BUTTONS
        # -------------------------------------------------------------
        frame_controls = tk.Frame(self.scrollable_content, pady=8)
        frame_controls.pack(fill="x", pady=5)
        
        self.btn_start = tk.Button(frame_controls, text="▶ Start Auto-Comment Engine", bg="#2ecc71", fg="white", font=("Arial", 11, "bold"), command=self.start_automation)
        self.btn_start.pack(side="left", padx=5, ipadx=12, ipady=3)

        self.btn_stop = tk.Button(frame_controls, text="⏹ Emergency Stop", bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), command=self.stop_automation, state=tk.DISABLED)
        self.btn_stop.pack(side="left", padx=5, ipadx=12, ipady=3)

        self.btn_refresh = tk.Button(frame_controls, text="🔍 Scan Devices", font=("Arial", 10), command=self.detect_devices_startup)
        self.btn_refresh.pack(side="right", padx=5, ipady=2)

        # -------------------------------------------------------------
        # FRAME 5: LIVE STATISTICS
        # -------------------------------------------------------------
        frame_stats = tk.LabelFrame(self.scrollable_content, text=" 4. Live Statistics & Monitoring ", padx=10, pady=8)
        frame_stats.pack(fill="x", pady=5)
        
        self.lbl_global_stats = tk.Label(frame_stats, text="Total Clones: 0 | Total Komentar Terkirim: 0", font=("Arial", 10, "bold"), fg="#2980b9")
        self.lbl_global_stats.pack(anchor="w")

        self.lbl_video_stats = tk.Label(frame_stats, text="Video Stats: None", font=("Arial", 9), fg="#27ae60")
        self.lbl_video_stats.pack(anchor="w", pady=(2, 0))
        
        self.lbl_device_stats = tk.Label(frame_stats, text="Device Stats: None", font=("Arial", 9), fg="#34495e")
        self.lbl_device_stats.pack(anchor="w", pady=(2, 0))

        # -------------------------------------------------------------
        # FRAME 6: EXECUTION LOGS CONSOLE
        # -------------------------------------------------------------
        frame_log = tk.LabelFrame(self.scrollable_content, text=" 5. Execution Logs Console ", padx=10, pady=8)
        frame_log.pack(fill="both", expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame_log, bg="#111111", fg="#00ff66", font=("Consolas", 9), height=14)
        self.log_text.pack(fill="both", expand=True)

    def generate_video_comment_forms(self):
        """Membuat form konfigurasi komentar dinamis berdasarkan jumlah video yang diinput."""
        try:
            total_videos = int(self.entry_video_count.get().strip())
            if total_videos <= 0:
                total_videos = 1
        except Exception:
            total_videos = 1

        for widget in self.dynamic_videos_container.winfo_children():
            widget.destroy()

        self.video_ui_widgets = {}

        sample_comments_pool = [
            "Visual packaging-nya ga ada obat! Slay banget asli 💅✨\nFix langsung meluncur ke keranjang kuning! Keracunan banget 😭🛒\nFormula & hasilnya ga pernah gagal. Valid no debat ini mah! 💯🔥",
            "Bagus banget kak review-nya, langsung checkout shade favorit! 💸✨\nRacun tiktok terparah bulan ini, worth it parah sih 👍🔥\nKualitasnya emang ga kaleng-kaleng, langganan banget pokoknya! ❤️",
            "Spill shade paling recommended-nya dong kak, mau auto checkout! 💸✨\nUdah pake ini 2 minggu dan emang sengefek itu gais 😍\nBintang 5 buat produk ini, packaging rapi dan pengiriman cepet banget! 🌟"
        ]

        for v in range(1, total_videos + 1):
            card_frame = tk.LabelFrame(
                self.dynamic_videos_container, 
                text=f" 💬 Video #{v} Comment Configuration ", 
                font=("Arial", 9, "bold"), 
                fg="#2c3e50", 
                padx=10, 
                pady=6
            )
            card_frame.pack(fill="x", pady=5)

            # Baris 1: Start Account & Target Comment Count
            row_cfg = tk.Frame(card_frame)
            row_cfg.pack(fill="x", pady=2)

            tk.Label(row_cfg, text="Mulai Komen dari Akun #:").pack(side="left")
            entry_start_acc = tk.Entry(row_cfg, width=8)
            entry_start_acc.pack(side="left", padx=(5, 15))
            entry_start_acc.insert(0, "1")

            tk.Label(row_cfg, text="Target Jumlah Komentar:").pack(side="left")
            entry_target_cmt = tk.Entry(row_cfg, width=8)
            entry_target_cmt.pack(side="left", padx=(5, 15))
            entry_target_cmt.insert(0, "0")

            tk.Label(row_cfg, text="(0 = Auto sesuai jumlah baris di bawah / Kosongkan jika tanpa komen)", fg="#7f8c8d", font=("Arial", 8, "italic")).pack(side="left")

            # Baris 2: List Komentar Text Box
            tk.Label(card_frame, text=f"List Komentar Video #{v} (1 Baris = 1 Komentar):", font=("Arial", 8, "bold")).pack(anchor="w", pady=(4, 2))
            text_comments = tk.Text(card_frame, width=75, height=3, font=("Segoe UI", 9))
            text_comments.pack(fill="x", pady=2)

            if v <= len(sample_comments_pool):
                text_comments.insert(tk.END, sample_comments_pool[v - 1])

            self.video_ui_widgets[v] = {
                'start_entry': entry_start_acc,
                'target_entry': entry_target_cmt,
                'text_area': text_comments
            }

    def detect_devices_startup(self):
        """Mendeteksi semua HP yang terhubung via ADB."""
        adb_path = find_adb_executable()
        if adb_path is None:
            self.logger.log("CRITICAL ERROR: ADB is not installed or not in PATH!")
            messagebox.showerror(
                "ADB Error",
                "ADB (Android Debug Bridge) tidak terdeteksi!\n\n" \
                "Pastikan Anda telah menginstal Android SDK Platform Tools dan menambahkannya ke PATH Windows."
            )
            return []

        self.logger.log(f"Using ADB executable: {adb_path}")
        try:
            result = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
        except Exception as e:
            self.logger.log(f"CRITICAL ERROR: ADB execution failed - {str(e)}")
            return []

        devices = []
        lines = output.splitlines()
        for line in lines[1:]:
            if line.strip() and "device" in line:
                parts = line.split()
                if parts[1] == "device":
                    devices.append(parts[0])
        
        self.log_text.delete("1.0", tk.END)
        self.logger.log(f"System Scan: Found {len(devices)} active Android device(s).")
        for dev in devices:
            self.logger.log(f"-> Detected Device ID: {dev}")
        
        if not devices:
            self.logger.log("WARNING: No devices found! Please enable USB Debugging.")
        
        return devices

    def find_clone_icon_element(self, d, clone_name):
        """
        Mencari elemen judul aplikasi clone dengan nama `clone_name`
        dan memfilter agar tidak salah mengklik badge notifikasi (misal angka '3' di ikon app 1).
        """
        target_str = str(clone_name).strip()
        escaped_name = re.escape(target_str)
        
        raw_candidates = []
        
        # 1. Exact text match
        try:
            elems = d(text=target_str)
            for i in range(len(elems)):
                if elems[i].exists:
                    raw_candidates.append(elems[i])
        except Exception:
            pass

        # 2. Exact description match
        try:
            elems = d(description=target_str)
            for i in range(len(elems)):
                if elems[i].exists:
                    raw_candidates.append(elems[i])
        except Exception:
            pass

        # 3. Exact whitespace-trimmed match
        try:
            elems = d(textMatches=rf"^\s*{escaped_name}\s*$")
            for i in range(len(elems)):
                if elems[i].exists:
                    raw_candidates.append(elems[i])
        except Exception:
            pass

        # 4. Strict TikTok + clone_name regex
        if not raw_candidates:
            try:
                elems = d(textMatches=rf"(?i)^\s*(TikTok\s*[-_()]*\s*{escaped_name}|{escaped_name}\s*[-_()]*\s*TikTok)\s*$")
                for i in range(len(elems)):
                    if elems[i].exists:
                        raw_candidates.append(elems[i])
            except Exception:
                pass

        if not raw_candidates:
            return None

        # Evaluasi kandidat: buang badge notifikasi kecil
        valid_candidates = []
        for cand in raw_candidates:
            try:
                info = cand.info
                bounds = info['bounds']
                width = bounds['right'] - bounds['left']
                height = bounds['bottom'] - bounds['top']
                res_id = str(info.get('resourceId', '')).lower()
                
                is_badge = False
                if any(k in res_id for k in ['badge', 'dot', 'unread', 'notify', 'count', 'red_point', 'msg']):
                    is_badge = True
                elif width < 75 and height < 75:
                    is_badge = True

                if not is_badge:
                    valid_candidates.append((cand, width * height, bounds['top']))
            except Exception:
                continue

        if not valid_candidates:
            return None

        valid_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return valid_candidates[0][0]

    def device_worker_thread(self, device_id, target_account, total_videos, watch_delay, clone_names_list, airplane_interval):
        """Worker Thread untuk Auto Comment Multi-Video per Clone."""
        self.logger.log(f"[{device_id}] Connecting via UIAutomator2 driver...")
        
        try:
            d = u2.connect(device_id)
            self.logger.log(f"[{device_id}] UIAutomator2 Connected. Screen Resolution: {d.window_size()}")
        except Exception as e:
            self.logger.log(f"[{device_id}] CRITICAL ERROR: Connection failed - {str(e)}")
            return

        class StopAutomationException(Exception): pass
        
        def smart_sleep(seconds):
            """Sleep yang bisa diinterupsi oleh tombol Stop."""
            end_time = time.time() + seconds
            while time.time() < end_time:
                if not self.is_running:
                    raise StopAutomationException()
                time.sleep(0.5)

        total_clones_count = len(clone_names_list)

        try:
            for idx, clone_name in enumerate(clone_names_list, start=1):
                if not self.is_running: raise StopAutomationException()
                
                self.logger.log(f"[{device_id}] [{idx}/{total_clones_count}] Launching Clone App for Account '{clone_name}'...")
                d.app_start("com.pengyou.cloneapp")
                smart_sleep(7.5)
                
                # 1. Cari ikon aplikasi berdasarkan nama persis (clone_name) dengan filter anti-badge
                self.logger.log(f"[{device_id}] Searching for exact Clone Icon named '{clone_name}' (Filtering badges)...")
                
                icon_found = False
                clone_icon = None
                
                for scroll_attempt in range(10):
                    if not self.is_running: raise StopAutomationException()
                    
                    clone_icon = self.find_clone_icon_element(d, clone_name)
                        
                    if clone_icon and clone_icon.exists(timeout=1):
                        self.logger.log(f"[{device_id}] Found valid Clone Icon '{clone_name}' on screen. Clicking...")
                        clone_icon.click()
                        icon_found = True
                        break
                    
                    self.logger.log(f"[{device_id}] Valid icon '{clone_name}' not found. Scrolling down (Attempt {scroll_attempt+1})...")
                    d.swipe(0.5, 0.75, 0.5, 0.35, duration=0.8)
                    smart_sleep(1.5)
                    
                if not icon_found:
                    self.logger.log(f"[{device_id}] ERROR: Could not find Clone Icon '{clone_name}' after scrolling. Skipping!")
                    continue
                
                # 2. Verifikasi bahwa aplikasi TikTok Clone benar-benar terbuka
                self.logger.log(f"[{device_id}] Verifying Cloned TikTok launch for '{clone_name}'...")
                tiktok_opened = False
                for _ in range(7):
                    if d(textMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=0) or d(descriptionMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=0):
                        tiktok_opened = True
                        break
                    smart_sleep(1)
                    
                if not tiktok_opened:
                    self.logger.log(f"[{device_id}] WARNING: Clone '{clone_name}' didn't launch on first click, retrying click...")
                    if clone_icon and clone_icon.exists(timeout=1):
                        clone_icon.click()
                    else:
                        self.logger.log(f"[{device_id}] Icon lost from screen, cannot retry.")
                    smart_sleep(5)
                    
                    if d(textMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=3) or d(descriptionMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=0):
                        tiktok_opened = True

                if not tiktok_opened:
                    self.logger.log(f"[{device_id}] ERROR: Failed to launch Clone '{clone_name}'! Skipping to prevent rogue clicks.")
                    continue
                
                self.logger.log(f"[{device_id}] Clearing potential overlays (Bottom Sheets/Popups)...")
                d.swipe(0.5, 0.6, 0.5, 0.9)
                smart_sleep(1)
                d.swipe(0.5, 0.15, 0.5, 0.02)
                smart_sleep(1)
                
                # 3. Navigasi Pencarian Akun Target
                self.logger.log(f"[{device_id}] Mencari navigasi pencarian (Jelajahi atau Ikon Search)...")
                if d(textMatches="(?i)jelajahi|discover").exists(timeout=2):
                    d(textMatches="(?i)jelajahi|discover").click()
                    smart_sleep(2)
                    self.logger.log(f"[{device_id}] (Lite) Clearing top banners then clicking Search Bar...")
                    d.swipe(0.5, 0.2, 0.5, 0.02)
                    smart_sleep(1)
                    if d(textMatches="(?i)temukan|search").exists(timeout=2):
                        d(textMatches="(?i)temukan|search").click()
                    else:
                        d.click(0.5, 0.08)
                elif d(descriptionMatches="(?i).*search.*|.*cari.*|.*jelajahi.*|.*discover.*").exists(timeout=0):
                    d(descriptionMatches="(?i).*search.*|.*cari.*|.*jelajahi.*|.*discover.*").click()
                else:
                    self.logger.log(f"[{device_id}] Ikon search tidak ditemukan, mencoba klik koordinat kanan atas (Global)...")
                    d.click(0.9, 0.08)
                smart_sleep(3)
                
                # Ketik username dan cari
                self.logger.log(f"[{device_id}] Searching for Account: {target_account}...")
                edit_search = d(className="android.widget.EditText")
                if edit_search.exists(timeout=3):
                    edit_search.click()
                    smart_sleep(1)
                    edit_search.set_text(target_account)
                    smart_sleep(1)
                    d.press("enter")
                    smart_sleep(2)
                    if d(textMatches="(?i)cari|search").exists(timeout=1):
                        d(textMatches="(?i)cari|search").click()
                else:
                    self.logger.log(f"[{device_id}] ERROR: Search box/EditText not found!")
                smart_sleep(4)
                
                # Klik hasil pencarian teratas (Blok User Profil)
                self.logger.log(f"[{device_id}] Clicking top search result for {target_account}...")
                screen_width, screen_height = d.window_size()
                profile_clicked = False
                
                try:
                    user_label = d(textMatches="(?i)pengguna|users|accounts")
                    if user_label.exists(timeout=3):
                        bounds = user_label[0].info['bounds']
                        click_y = bounds['bottom'] + int(screen_height * 0.08)
                        self.logger.log(f"[{device_id}] Found 'Pengguna/Users' label. Clicking below it at Y: {click_y}")
                        d.click(int(screen_width * 0.5), click_y)
                        profile_clicked = True
                except Exception as e:
                    self.logger.log(f"[{device_id}] Selection error by label: {str(e)}")
                    
                if not profile_clicked:
                    self.logger.log(f"[{device_id}] 'Pengguna' label not found, using coordinate fallback...")
                    d.click(0.4, 0.25)
                smart_sleep(4)
                
                # Klik tab Liked (Disukai) dengan Ikon Hati via Strategi "Swipe & Pin"
                self.logger.log(f"[{device_id}] Switching to 'Liked' (Heart) Tab...")
                screen_width, screen_height = d.window_size()
                
                # Normalisasi UI: 2x Swipe Kuat ke Atas untuk Pin Tab Bar ke Atas
                self.logger.log(f"[{device_id}] Normalizing UI: Scrolling down to hide Bio and pin Tab Bar to top...")
                d.swipe(0.5, 0.70, 0.5, 0.15, duration=0.4)
                smart_sleep(1.5)
                d.swipe(0.5, 0.70, 0.5, 0.15, duration=0.4)
                smart_sleep(2)
                
                tab_center_y = int(screen_height * 0.11)
                heart_tab = d(descriptionMatches="(?i).*disukai.*|.*suka.*|.*liked.*|.*likes.*")
                clicked_tab = False
                
                if heart_tab.exists(timeout=1):
                    for i in range(len(heart_tab)):
                        bounds = heart_tab[i].info['bounds']
                        if bounds['top'] < screen_height * 0.25:
                            tab_center_y = bounds['top'] + ((bounds['bottom'] - bounds['top']) // 2)
                            heart_tab[i].click()
                            clicked_tab = True
                            self.logger.log(f"[{device_id}] Heart tab clicked via text at pinned position Y: {tab_center_y}")
                            break
                            
                if not clicked_tab:
                    self.logger.log(f"[{device_id}] Heart tab text not found. Clicking pinned coordinate X=0.75, Y=0.11")
                    d.click(0.75, 0.11)
                    
                smart_sleep(3)
                
                # Buka Video Pertama (#1) dari Grid Tab Liked
                self.logger.log(f"[{device_id}] Opening FIRST Liked Video (Grid 1x1)...")
                click_vid_x = 0.16
                vid_height_pct = ((screen_width / 3.0) * (16.0 / 9.0)) / screen_height
                current_tab_y_pct = tab_center_y / screen_height
                target_y = current_tab_y_pct + (0 * vid_height_pct) + (vid_height_pct / 2)
                
                if target_y > 0.95:
                    target_y = 0.90
                    
                self.logger.log(f"[{device_id}] Target First Video Coordinate: X={click_vid_x:.2f}, Y={target_y:.2f}")
                d.click(click_vid_x, target_y)
                
                # 4. LOOPING MULTI-VIDEO: RENDERING & EKSEKUSI KOMENTAR PER VIDEO
                for v_idx in range(1, total_videos + 1):
                    if not self.is_running: raise StopAutomationException()
                    
                    self.logger.log(f"[{device_id}] [Video #{v_idx}/{total_videos}] Rendering & Watching video...")
                    curr_delay = max(3, watch_delay + random.randint(-1, 2))
                    smart_sleep(curr_delay)

                    cfg_video = self.video_configs.get(v_idx, {})
                    start_comment_acc = cfg_video.get('start_acc', 1)
                    target_comment_count = cfg_video.get('target_comments', 0)
                    
                    comment_text = None
                    # Cek apakah clone_name (atau index-nya) memenuhi syarat mulai komen
                    clone_num_val = int(clone_name) if str(clone_name).isdigit() else idx
                    if clone_num_val >= start_comment_acc:
                        with self.comment_lock:
                            curr_video_comments = self.video_comment_counts.get(v_idx, 0)
                            comments_queue = self.shared_comments_per_video.get(v_idx, [])
                            
                            if (target_comment_count > 0 and curr_video_comments < target_comment_count) and len(comments_queue) > 0:
                                comment_text = comments_queue.pop(0)

                    if comment_text and self.is_running:
                        self.logger.log(f"[{device_id}] [Video #{v_idx}] Extracted Comment for Video #{v_idx}: '{comment_text}'")
                        
                        if d(textContains="menonaktifkan").exists(timeout=2) or d(descriptionContains="menonaktifkan").exists(timeout=0):
                            self.logger.log(f"[{device_id}] [Video #{v_idx}] Creator disabled comments! Returning comment back to queue...")
                            with self.comment_lock:
                                self.shared_comments_per_video[v_idx].insert(0, comment_text)
                        else:
                            self.logger.log(f"[{device_id}] [Video #{v_idx}] Opening Comment section...")
                            if d(descriptionMatches="(?i).*komentar.*|.*comment.*").exists(timeout=2):
                                d(descriptionMatches="(?i).*komentar.*|.*comment.*").click()
                            elif d(textContains="Tambahkan komentar").exists(timeout=1):
                                d(textContains="Tambahkan komentar").click()
                            else:
                                d.click(0.91, 0.60)
                            smart_sleep(2.5)

                            self.logger.log(f"[{device_id}] [Video #{v_idx}] Focusing Comment Input Box...")
                            input_prompt = d(textMatches="(?i).*tambahkan komentar.*|.*add comment.*|.*say something.*")
                            if input_prompt.exists(timeout=2):
                                input_prompt.click()
                            else:
                                d.click(0.40, 0.95)
                            smart_sleep(2.0)

                            edit_box = d(className="android.widget.EditText")
                            if not edit_box.exists(timeout=3):
                                edit_box = d(focused=True)

                            if edit_box.exists(timeout=2):
                                edit_box.click() # Pastikan fokus
                                smart_sleep(0.8)
                                edit_box.set_text(comment_text) # Isi teks langsung tanpa ATX
                                smart_sleep(1.5)

                                # Eksekusi tombol kirim (Tombol bulat pink panah atas)
                                sent = False
                                screen_width, screen_height = d.window_size()

                                if d(descriptionMatches="(?i).*kirim.*|.*send.*|.*publish.*|.*unggah.*").exists(timeout=1):
                                    d(descriptionMatches="(?i).*kirim.*|.*send.*|.*publish.*|.*unggah.*").click()
                                    sent = True
                                elif d(resourceIdMatches="(?i).*send.*|.*publish.*|.*btn_send.*|.*iv_send.*").exists(timeout=1):
                                    d(resourceIdMatches="(?i).*send.*|.*publish.*|.*btn_send.*|.*iv_send.*").click()
                                    sent = True

                                if not sent:
                                    try:
                                        bounds = edit_box.info['bounds']
                                        send_x = int(screen_width * 0.895)
                                        send_y = bounds['bottom'] + int(screen_height * 0.035)
                                        self.logger.log(f"[{device_id}] Clicking Pink Send Button at X={send_x}, Y={send_y}...")
                                        d.click(send_x, send_y)
                                        sent = True
                                    except Exception:
                                        d.click(int(screen_width * 0.895), int(screen_height * 0.52))
                                        sent = True

                                smart_sleep(0.5)
                                # Trigger IME Enter/Send di keyboard
                                d.click(int(screen_width * 0.90), int(screen_height * 0.90))
                                d.press("enter")
                                d.shell("input keyevent 66")

                                self.logger.log(f"[{device_id}] [Video #{v_idx}] Comment SENT successfully on Video #{v_idx}!")
                                with self.stats_lock:
                                    self.global_comment_count += 1
                                    self.video_comment_counts[v_idx] = self.video_comment_counts.get(v_idx, 0) + 1
                                    self.device_comment_counts[device_id] = self.device_comment_counts.get(device_id, 0) + 1
                                self.update_stats_ui()
                                smart_sleep(2)
                            else:
                                self.logger.log(f"[{device_id}] [Video #{v_idx}] Failed to find Edit Box. Returning comment back to queue...")
                                with self.comment_lock:
                                    self.shared_comments_per_video[v_idx].insert(0, comment_text)

                            # Tutup lembar komentar HANYA via tombol X agar tidak keluar dari video
                            self.logger.log(f"[{device_id}] [Video #{v_idx}] Closing Comment sheet...")
                            close_btn = d(descriptionMatches="(?i).*tutup.*|.*close.*")
                            if not close_btn.exists(timeout=0):
                                close_btn = d(resourceIdMatches="(?i).*close.*|.*btn_close.*|.*iv_close.*")
                                
                            if close_btn.exists(timeout=1):
                                close_btn.click()
                                smart_sleep(1.0)

                    # SWIPE KE VIDEO BERIKUTNYA JIKA BELUM VIDEO TERAKHIR
                    if v_idx < total_videos:
                        self.logger.log(f"[{device_id}] Swiping down to NEXT video (#{v_idx + 1})...")
                        d.swipe(0.5, 0.82, 0.5, 0.18, duration=0.35)
                        smart_sleep(1.5)

                self.logger.log(f"[{device_id}] SUCCESS: Finished {total_videos} videos on Clone '{clone_name}'!")

                # 5. TUTUP PAKSA APLIKASI UNTUK MELEGAKAN RAM
                self.logger.log(f"[{device_id}] Clearing RAM: Force-stopping Clone App and TikTok processes...")
                d.app_stop("com.pengyou.cloneapp")
                d.app_stop("com.zhiliaoapp.musically.go")
                d.app_stop("com.zhiliaoapp.musically")
                smart_sleep(2.5)

                # UPDATE STATISTIK AKUN
                with self.stats_lock:
                    self.global_clone_count += 1
                    self.device_clone_counts[device_id] = self.device_clone_counts.get(device_id, 0) + 1
                self.update_stats_ui()

                is_last = (idx == total_clones_count)
                if not is_last and self.is_running:
                    self.logger.log(f"[{device_id}] Reopening Clone App Matrix for the next account...")
                    d.app_start("com.pengyou.cloneapp")
                    smart_sleep(4.5)

                    # 6. ROTASI IP (AIRPLANE MODE) JIKA DIAKTIFKAN
                    if airplane_interval > 0 and (idx % airplane_interval == 0):
                        self.logger.log(f"[{device_id}] Dispatching IP Rotation (Airplane Mode) every {airplane_interval} clones...")
                        d.shell("cmd connectivity airplane-mode enable")
                        d.shell("svc data disable")
                        self.logger.log(f"[{device_id}] IP Reset (Airplane/Data OFF). Menunggu 5 detik...")
                        smart_sleep(5)
                        
                        d.shell("cmd connectivity airplane-mode disable")
                        d.shell("svc data enable")
                        self.logger.log(f"[{device_id}] IP Reset (Airplane/Data ON). Menunggu 3 detik untuk koneksi ulang...")
                        smart_sleep(3)

            self.logger.log(f"[{device_id}] Worker Thread finished execution lifecycle.")
        except StopAutomationException:
            self.logger.log(f"[{device_id}] 🛑 EMERGENCY STOP: Worker thread forcefully halted!")

    def update_stats_ui(self):
        """Thread-safe update of the statistics labels."""
        with self.stats_lock:
            global_c = self.global_clone_count
            global_cmt = self.global_comment_count
            
            # Breakdown per video
            vid_stats_list = [
                f"V#{v}: {self.video_comment_counts.get(v, 0)} Komentar" 
                for v in sorted(self.video_configs.keys())
            ]
            vid_stats_str = " | ".join(vid_stats_list) if vid_stats_list else "None"

            # Breakdown per device
            dev_stats_list = [
                f"[{dev}]: {self.device_clone_counts.get(dev, 0)} accs ({self.device_comment_counts.get(dev, 0)} komentar)" 
                for dev in self.device_clone_counts.keys()
            ]
            dev_stats_str = " | ".join(dev_stats_list) if dev_stats_list else "None"
            
        def _update():
            self.lbl_global_stats.config(text=f"Total Clones: {global_c} | Total Komentar Terkirim: {global_cmt}")
            self.lbl_video_stats.config(text=f"Video Comments: {vid_stats_str}")
            self.lbl_device_stats.config(text=f"Device Stats: {dev_stats_str}")
            
        self.root.after(0, _update)

    def start_automation(self):
        devices = self.detect_devices_startup()
        if not devices:
            messagebox.showerror("Error", "No connected Android devices detected via ADB!")
            return

        target_account = self.entry_url.get().strip()
        try:
            total_videos = int(self.entry_video_count.get().strip())
            watch_delay = int(self.entry_watch_delay.get().strip())
            airplane_interval = int(self.entry_airplane_interval.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Jumlah Video, Jeda & Airplane Interval harus berupa angka bulat positif!")
            return

        # Parsing Daftar Nama Clone
        custom_clones_raw = self.entry_custom_clones.get().strip()
        clone_names_list = []

        if custom_clones_raw:
            tokens = [t.strip() for t in custom_clones_raw.split(",") if t.strip()]
            for token in tokens:
                if "-" in token:
                    parts = token.split("-")
                    if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                        start_r = int(parts[0].strip())
                        end_r = int(parts[1].strip())
                        clone_names_list.extend([str(i) for i in range(start_r, end_r + 1)])
                    else:
                        clone_names_list.append(token)
                else:
                    clone_names_list.append(token)
        else:
            start_val = self.entry_start_idx.get().strip()
            end_val = self.entry_clones.get().strip()

            if start_val.isdigit() and end_val.isdigit():
                s_num = int(start_val)
                e_num = int(end_val)
                if e_num < s_num:
                    e_num = s_num
                clone_names_list = [str(i) for i in range(s_num, e_num + 1)]
            else:
                clone_names_list = [start_val]

        if not clone_names_list:
            messagebox.showerror("Error", "Daftar nama clone tidak boleh kosong!")
            return

        # Parsing konfigurasi dinamis per-video (Komentar)
        self.video_configs = {}
        self.shared_comments_per_video = {}
        self.video_comment_counts = {}

        for v in range(1, total_videos + 1):
            if v in self.video_ui_widgets:
                w = self.video_ui_widgets[v]

                try:
                    start_acc = int(w['start_entry'].get().strip())
                except ValueError:
                    start_acc = 1

                raw_cmts = w['text_area'].get("1.0", tk.END).strip().split("\n")
                cmts = [c.strip() for c in raw_cmts if c.strip()]

                try:
                    target_cmt = int(w['target_entry'].get().strip())
                except ValueError:
                    target_cmt = 0

                if target_cmt == 0 and len(cmts) > 0:
                    target_cmt = len(cmts)

                self.video_configs[v] = {
                    'start_acc': start_acc,
                    'target_comments': target_cmt
                }
                self.shared_comments_per_video[v] = list(cmts)
                self.video_comment_counts[v] = 0
                
                self.logger.log(f"CONFIG Video #{v}: Komen Start #{start_acc} (Target {target_cmt} komentar, Antrean {len(cmts)} teks).")

        # Reset hitungan global
        self.global_clone_count = 0
        self.global_comment_count = 0
        self.device_clone_counts = {dev: 0 for dev in devices}
        self.device_comment_counts = {dev: 0 for dev in devices}
        self.update_stats_ui()

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.logger.log(f"MASTER CONTROL: Auto-Comment Engine deployed on {len(devices)} devices ({len(clone_names_list)} accounts: {clone_names_list[:5]}...)...")

        self.active_threads = []
        for device_id in devices:
            t = threading.Thread(
                target=self.device_worker_thread, 
                args=(device_id, target_account, total_videos, watch_delay, clone_names_list, airplane_interval)
            )
            t.daemon = True
            self.active_threads.append(t)
            t.start()

        self.root.after(1000, self.monitor_execution_status)

    def monitor_execution_status(self):
        still_running = any(t.is_alive() for t in self.active_threads)
        
        if still_running and self.is_running:
            self.root.after(1000, self.monitor_execution_status)
        else:
            self.is_running = False
            self.btn_start.config(state=tk.NORMAL)
            self.btn_refresh.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.logger.log("MASTER CONTROL: All processes terminated. Engine Idle.")

    def stop_automation(self):
        self.logger.log("MASTER CONTROL: Emergency Stop triggered by user.")
        self.is_running = False
        self.btn_stop.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = TikTokCommentManyLabU2(root)
    root.mainloop()
