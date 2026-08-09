import os
import time
import random
import queue
import threading
import subprocess
import shutil
import uiautomator2 as u2
import tkinter as tk
from tkinter import messagebox, scrolledtext


def find_adb_executable():
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

class TikTokCloneAppLabU2:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok Multi-Device Lab v2.0 - Clone App Matrix Engine")
        self.root.geometry("700x750")
        self.is_running = False
        self.active_threads = []
        
        self.global_comment_count = 0
        self.comment_lock = threading.Lock()
        
        self.global_clone_count = 0
        self.device_clone_counts = {}
        self.stats_lock = threading.Lock()

        self.setup_gui()
        self.logger = ThreadSafeConsoleLogger(self.log_text)
        self.detect_devices_startup()

    def setup_gui(self):
        # Frame Input Target Profil
        frame_url = tk.LabelFrame(self.root, text=" 1. Target Configuration ", padx=10, pady=5)
        frame_url.pack(fill="x", padx=10, pady=5)
        
        # Username Input
        tk.Label(frame_url, text="Username Akun Target (misal: vionex):").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_url = tk.Entry(frame_url, width=40)
        self.entry_url.grid(row=0, column=1, sticky="w", pady=2, padx=5)
        self.entry_url.insert(0, "vionex")
        
        # Video Index Input
        tk.Label(frame_url, text="Urutan Video di Tab Liked (misal: 1):").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_video_index = tk.Entry(frame_url, width=10)
        self.entry_video_index.grid(row=1, column=1, sticky="w", pady=2, padx=5)
        self.entry_video_index.insert(0, "1")

        # Frame Loop & Clone App Configurations
        frame_config = tk.LabelFrame(self.root, text=" 2. Clone App Matrix Configuration ", padx=10, pady=5)
        frame_config.pack(fill="x", padx=10, pady=5)

        # Jumlah Total Clone & Start Index
        frame_loop = tk.Frame(frame_config)
        frame_loop.pack(side="left", fill="y", padx=5)
        
        tk.Label(frame_loop, text="Total Clones to Process (N):").pack(anchor="w")
        self.entry_clones = tk.Entry(frame_loop, width=20)
        self.entry_clones.pack(anchor="w", pady=2)
        self.entry_clones.insert(0, "50")

        tk.Label(frame_loop, text="Start Clone Index (Start from #):").pack(anchor="w", pady=(5,0))
        self.entry_start_idx = tk.Entry(frame_loop, width=20)
        self.entry_start_idx.pack(anchor="w", pady=2)
        self.entry_start_idx.insert(0, "1")

        # Frame Auto Commenting
        frame_ai = tk.LabelFrame(self.root, text=" 3. Auto Commenting Configuration ", padx=10, pady=5)
        frame_ai.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_ai, text="Target Comment Count:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_comment_target = tk.Entry(frame_ai, width=20)
        self.entry_comment_target.grid(row=0, column=1, sticky="w", pady=2, padx=5)
        self.entry_comment_target.insert(0, "0") # Default 0 = Disable Commenting

        tk.Label(frame_ai, text="List Komentar\n(1 Baris = 1 Komentar):").grid(row=1, column=0, sticky="nw", pady=2)
        self.text_prompt = tk.Text(frame_ai, width=60, height=5)
        self.text_prompt.grid(row=1, column=1, sticky="w", pady=2, padx=5)
        default_comments = (
            "Visual packaging-nya ga ada obat! Slay banget asli 💅✨\n"
            "Fix langsung meluncur ke keranjang kuning! Keracunan banget 😭🛒\n"
            "Formula & hasilnya ga pernah gagal. Valid no debat ini mah! 💯🔥\n"
            "Spill shade paling recommended-nya dong kak, mau auto checkout! 💸✨"
        )
        self.text_prompt.insert(tk.END, default_comments)

        # Information Box
        frame_info = tk.Frame(frame_config)
        frame_info.pack(side="right", fill="both", expand=True, padx=5)
        tk.Label(frame_info, text="Clone App Info:", font=("Arial", 9, "bold")).pack(anchor="w")
        info_text = (
            "• Target App: Clone App (com.pengyou.cloneapp)\n"
            "• Grid Layout: 4 Columns per Row\n"
            "• Slot #0 (Folder Tools) ditautkan otomatis\n"
            "• Auto-Scroll dinamis setelah setiap 4 baris\n"
            "• Double-Tap Native & Rotasi IP Aktif"
        )
        lbl_info = tk.Label(frame_info, text=info_text, justify="left", anchor="w", fg="#333333")
        lbl_info.pack(fill="both", expand=True, pady=2)

        # Kontrol Tombol
        frame_controls = tk.Frame(self.root, pady=5)
        frame_controls.pack(fill="x", padx=10)
        
        self.btn_start = tk.Button(frame_controls, text="Start Automation", bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), command=self.start_automation)
        self.btn_start.pack(side="left", padx=5, ipadx=10)

        self.btn_stop = tk.Button(frame_controls, text="Emergency Stop", bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), command=self.stop_automation, state=tk.DISABLED)
        self.btn_stop.pack(side="left", padx=5, ipadx=10)

        self.btn_refresh = tk.Button(frame_controls, text="Scan Devices", command=self.detect_devices_startup)
        self.btn_refresh.pack(side="right", padx=5)

        # Statistics Window
        frame_stats = tk.LabelFrame(self.root, text=" 4. Live Statistics ", padx=10, pady=5)
        frame_stats.pack(fill="x", padx=10, pady=5)
        
        self.lbl_global_clones = tk.Label(frame_stats, text="Total Clones Executed: 0", font=("Arial", 10, "bold"), fg="blue")
        self.lbl_global_clones.pack(anchor="w")
        
        self.lbl_device_stats = tk.Label(frame_stats, text="Device Stats: None", font=("Arial", 9), fg="black")
        self.lbl_device_stats.pack(anchor="w")

        # Console Log Window
        frame_log = tk.LabelFrame(self.root, text=" 5. Execution Logs Console ", padx=10, pady=5)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame_log, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

    def detect_devices_startup(self):
        """Mendeteksi semua HP yang terhubung via ADB."""
        adb_path = find_adb_executable()
        if adb_path is None:
            self.logger.log("CRITICAL ERROR: ADB is not installed or not in PATH!")
            messagebox.showerror(
                "ADB Error",
                "ADB (Android Debug Bridge) tidak terdeteksi!\n\n" \
                "Pastikan Anda telah menginstal Android SDK Platform Tools dan menambahkannya ke PATH Windows laptop client ini.\n\n" \
                "Jika sudah memiliki adb.exe di Downloads atau SDK, pindahkan ke PATH atau ke folder yang dikenali."
            )
            return []

        self.logger.log(f"Using ADB executable: {adb_path}")
        try:
            result = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
        except Exception as e:
            self.logger.log(f"CRITICAL ERROR: ADB execution failed - {str(e)}")
            messagebox.showerror(
                "ADB Error",
                "ADB ditemukan tetapi gagal dijalankan. Periksa instalasi Android SDK Platform Tools dan izin file.\n\n" \
                f"Detail: {str(e)}"
            )
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

    def device_worker_thread(self, device_id, target_account, video_index, total_clones, start_index, comment_target):
        """Worker Thread berbasis uiautomator2 untuk Clone App Matrix."""
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

        col_x_ratios = [0.125, 0.375, 0.625, 0.875]
        row_y_ratios = [0.165, 0.295, 0.425, 0.555]

        try:
            for clone_num in range(start_index, total_clones + 1):
                if not self.is_running: raise StopAutomationException()
                
                self.logger.log(f"[{device_id}] [Clone #{clone_num}/{total_clones}] Launching Clone App...")
                d.app_start("com.pengyou.cloneapp")
                # Jeda 7.5 detik (tambahan 3 detik) untuk memastikan SplashActivity / Iklan Clone App selesai memuat
                smart_sleep(7.5)
                
                # 1. Cari ikon aplikasi berdasarkan nama persis (angka clone_num)
                self.logger.log(f"[{device_id}] Searching for Clone Icon named '{clone_num}'...")
                
                icon_found = False
                clone_icon = None
                for scroll_attempt in range(10): # Maksimal 10 kali scroll
                    if not self.is_running: raise StopAutomationException()
                    
                    # Cari teks yang SAMA PERSIS dengan nomor clone (misal "9") atau yang mengandung kata TikTok
                    clone_icon = d(text=str(clone_num))
                    if not clone_icon.exists(timeout=0):
                        # Coba alternatif jika user masih memakai nama panjang
                        clone_icon = d(textMatches=f"(?i).*TikTok.*{clone_num}.*|.*{clone_num}.*TikTok.*")
                        
                    if clone_icon.exists(timeout=1):
                        self.logger.log(f"[{device_id}] Found Clone Icon '{clone_num}' on screen. Clicking...")
                        clone_icon.click()
                        icon_found = True
                        break
                    
                    self.logger.log(f"[{device_id}] Icon '{clone_num}' not found. Scrolling down (Attempt {scroll_attempt+1})...")
                    # Lakukan scroll pendek ke bawah layar (geser jari ke atas)
                    d.swipe(0.5, 0.75, 0.5, 0.35, duration=0.8)
                    smart_sleep(1.5)
                    
                if not icon_found:
                    self.logger.log(f"[{device_id}] ERROR: Could not find Clone Icon '{clone_num}' after scrolling. Skipping!")
                    continue
                
                # 2. Verifikasi bahwa aplikasi TikTok Clone benar-benar terbuka
                self.logger.log(f"[{device_id}] Verifying Cloned TikTok launch...")
                tiktok_opened = False
                for _ in range(7):
                    # Deteksi elemen UI TikTok karena package Name bisa tetap Clone App
                    if d(textMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=0) or d(descriptionMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=0):
                        tiktok_opened = True
                        break
                    smart_sleep(1)
                    
                if not tiktok_opened:
                    self.logger.log(f"[{device_id}] WARNING: Clone #{clone_num} didn't launch on first click, retrying click...")
                    if clone_icon and clone_icon.exists(timeout=1):
                        clone_icon.click()
                    else:
                        self.logger.log(f"[{device_id}] Icon lost from screen, cannot retry.")
                    smart_sleep(5)
                    
                    # Cek ulang apakah TikTok berhasil terbuka setelah retry
                    if d(textMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=3) or d(descriptionMatches="(?i)beranda|jelajahi|profil|home|discover|profile").exists(timeout=0):
                        tiktok_opened = True

                # CRITICAL FIX: Jika TikTok GAGAL TERBUKA, jangan lanjutkan ke logika pencarian!
                if not tiktok_opened:
                    self.logger.log(f"[{device_id}] ERROR: Failed to launch Clone #{clone_num}! Skipping this clone to prevent rogue clicks.")
                    continue # Langsung lanjut ke aplikasi Clone berikutnya!
                
                self.logger.log(f"[{device_id}] Clearing potential overlays (Bottom Sheets/Popups)...")
                d.swipe(0.5, 0.6, 0.5, 0.9) # Swipe ke bawah untuk menutup "Share/Report" jika tak sengaja tertekan
                smart_sleep(1)
                d.swipe(0.5, 0.15, 0.5, 0.02) # Swipe atas untuk menutup banner notifikasi di puncak layar
                smart_sleep(1)
                
                # 3. Navigasi Pencarian Akun Target
                self.logger.log(f"[{device_id}] Mencari navigasi pencarian (Jelajahi atau Ikon Search)...")
                
                # Coba cari berdasarkan teks atau deskripsi untuk tombol pencarian/jelajahi
                if d(textMatches="(?i)jelajahi|discover").exists(timeout=2):
                    d(textMatches="(?i)jelajahi|discover").click()
                    smart_sleep(2)
                    self.logger.log(f"[{device_id}] (Lite) Clearing top banners then clicking Search Bar...")
                    d.swipe(0.5, 0.2, 0.5, 0.02) # Usir paksa notifikasi "Pesan Baru" yang menutupi Search Bar
                    smart_sleep(1)
                    if d(textMatches="(?i)temukan|search").exists(timeout=2):
                        d(textMatches="(?i)temukan|search").click()
                    else:
                        d.click(0.5, 0.08) # Koordinat Search Bar (Tengah Atas)
                elif d(descriptionMatches="(?i).*search.*|.*cari.*|.*jelajahi.*|.*discover.*").exists(timeout=0):
                    d(descriptionMatches="(?i).*search.*|.*cari.*|.*jelajahi.*|.*discover.*").click()
                else:
                    self.logger.log(f"[{device_id}] Ikon search tidak ditemukan, mencoba klik koordinat kanan atas (Global)...")
                    d.click(0.9, 0.08) # Koordinat fallback ikon Kaca Pembesar di TikTok Global
                smart_sleep(3)
                
                # Ketik username dan cari
                self.logger.log(f"[{device_id}] Searching for Account: {target_account}...")
                edit_search = d(className="android.widget.EditText")
                if edit_search.exists(timeout=3):
                    # Terkadang klik search icon otomatis fokus ke EditText, namun kita klik untuk pasti
                    edit_search.click()
                    smart_sleep(1)
                    edit_search.set_text(target_account)
                    smart_sleep(1)
                    d.press("enter")
                    smart_sleep(2)
                    # Coba klik tombol 'Cari' atau 'Search' di sebelah kanan jika enter tidak memicu pencarian
                    if d(textMatches="(?i)cari|search").exists(timeout=1):
                        d(textMatches="(?i)cari|search").click()
                else:
                    self.logger.log(f"[{device_id}] ERROR: Search box/EditText not found!")
                    # Tetap lanjut
                smart_sleep(4) # Tunggu hasil pencarian muncul
                
                # Klik hasil pencarian teratas (Biasanya blok User Profil)
                self.logger.log(f"[{device_id}] Clicking top search result for {target_account}...")
                
                screen_width, screen_height = d.window_size()
                profile_clicked = False
                
                try:
                    # Sesuai saran: Cari label 'Pengguna' (atau Users) lalu klik persis di bawahnya.
                    # Ini jauh lebih aman daripada mencari textContains yang bisa menembak judul video.
                    user_label = d(textMatches="(?i)pengguna|users|accounts")
                    if user_label.exists(timeout=3):
                        # Ambil elemen pertama (yang paling atas jika ada beberapa)
                        bounds = user_label[0].info['bounds']
                        click_y = bounds['bottom'] + int(screen_height * 0.08) # Klik sekitar 8% layar di bawah label "Pengguna"
                        self.logger.log(f"[{device_id}] Found 'Pengguna/Users' label. Clicking below it at Y: {click_y}")
                        d.click(int(screen_width * 0.5), click_y)
                        profile_clicked = True
                except Exception as e:
                    self.logger.log(f"[{device_id}] Selection error by label: {str(e)}")
                    
                if not profile_clicked:
                    self.logger.log(f"[{device_id}] 'Pengguna' label not found, using coordinate fallback...")
                    # Fallback koordinat hasil pencarian pengguna teratas
                    # Y=0.25 lebih aman karena posisinya pas di bawah teks "PENGGUNA" dan pas di avatar profil
                    d.click(0.4, 0.25)
                smart_sleep(4) # Tunggu profil dimuat
                
                # Klik tab Liked (Disukai) dengan Ikon Hati
                self.logger.log(f"[{device_id}] Switching to 'Liked' (Heart) Tab...")
                heart_tabs = d(descriptionMatches="(?i).*disukai.*|.*suka.*|.*liked.*|.*likes.*")
                
                screen_width, screen_height = d.window_size()
                
                aspect_ratio = screen_height / screen_width
                if aspect_ratio < 1.9:
                    fallback_y = 0.58 # HP Layar Pendek, tab lebih di bawah
                elif aspect_ratio < 2.1:
                    fallback_y = 0.52 
                else:
                    fallback_y = 0.48 # HP Layar Panjang, tab lebih di atas
                    
                # STRATEGI 4 (PALING AMPUH): "Swipe & Pin"
                # Kita scroll profil ke bawah secara paksa agar Bio yang panjang dan Statistik "Suka" 
                # menghilang dari layar. Ini akan membuat Tab Bar "mentok" (pinned) di bagian atas layar.
                self.logger.log(f"[{device_id}] Normalizing UI: Scrolling down to hide Bio and pin Tab Bar to top...")
                
                # Lakukan dua kali swipe kuat ke atas
                d.swipe(0.5, 0.70, 0.5, 0.15, duration=0.4)
                smart_sleep(1.5)
                d.swipe(0.5, 0.70, 0.5, 0.15, duration=0.4)
                smart_sleep(2)
                
                # Setelah di-swipe, Tab Bar PASTI menempel di atas (sekitar Y=0.11) 
                # Tidak peduli sepanjang apa pun bionya, karena bionya sudah tersingkir!
                tab_center_y = int(screen_height * 0.11)
                
                # Coba cari Heart Tab berdasarkan deskripsi, KARENA stat "396 rb Suka" sudah hilang dari layar,
                # jadi kalau ketemu kata "suka", itu PASTI tab hati.
                heart_tab = d(descriptionMatches="(?i).*disukai.*|.*suka.*|.*liked.*|.*likes.*")
                clicked_tab = False
                
                if heart_tab.exists(timeout=1):
                    for i in range(len(heart_tab)):
                        bounds = heart_tab[i].info['bounds']
                        # Pastikan posisinya ada di area atas (karena tab bar sudah di-pin)
                        if bounds['top'] < screen_height * 0.25:
                            tab_center_y = bounds['top'] + ((bounds['bottom'] - bounds['top']) // 2)
                            heart_tab[i].click()
                            clicked_tab = True
                            self.logger.log(f"[{device_id}] Heart tab clicked via text at pinned position Y: {tab_center_y}")
                            break
                            
                # Jika tab hati tidak punya deskripsi teks, kita gunakan klik koordinat aman di Y=0.11
                # X=0.75 adalah titik aman untuk menyentuh Ikon Hati terlepas dari jumlah tab (2, 3, atau 4 tab)
                if not clicked_tab:
                    self.logger.log(f"[{device_id}] Heart tab text not found. Clicking pinned coordinate X=0.75, Y=0.11")
                    d.click(0.75, 0.11)
                    
                smart_sleep(3)
                
                # Buka Video ke-N dari Grid Liked
                self.logger.log(f"[{device_id}] Opening Liked Video #{video_index}...")
                
                # --- PENCARIAN KOORDINAT TOTAL DINAMIS (TANPA ASUMSI SCROLL) ---
                vid_idx_0_based = video_index - 1
                vid_row = vid_idx_0_based // 3
                vid_col = vid_idx_0_based % 3
                
                vid_col_x = [0.16, 0.50, 0.83]
                click_vid_x = vid_col_x[vid_col]
                
                # Tinggi 1 video adalah 16/27 dari lebar layar (Aspek rasio 9:16, dibagi 3 kolom)
                # Rumus: (screen_width / 3) * (16 / 9) / screen_height = persentase tinggi video
                vid_height_pct = ((screen_width / 3.0) * (16.0 / 9.0)) / screen_height
                
                # Hitung posisi absolut Y dari target
                current_tab_y_pct = tab_center_y / screen_height
                target_y = current_tab_y_pct + (vid_row * vid_height_pct) + (vid_height_pct / 2)
                
                # Jika video target jatuh di luar layar bawah (> 90%), kita HARUS scroll
                while target_y > 0.88:
                    self.logger.log(f"[{device_id}] Target Y ({target_y:.2f}) is off-screen. Scrolling down...")
                    # Scroll layar perlahan sebesar setengah layar
                    d.swipe(0.5, 0.80, 0.5, 0.30, duration=1.0)
                    smart_sleep(2)
                    
                    # CARI ULANG posisi Tab Hati setelah scroll!
                    if heart_tab.exists(timeout=2):
                        bounds = heart_tab.info['bounds']
                        tab_center_y = bounds['top'] + ((bounds['bottom'] - bounds['top']) // 2)
                        current_tab_y_pct = tab_center_y / screen_height
                    else:
                        # Jika tak terlihat, biasanya karena Tab sudah "Pinned" di paling atas layar (sekitar 0.12 - 0.15)
                        current_tab_y_pct = 0.15 
                        
                    # Kalkulasi Ulang Target Y
                    target_y = current_tab_y_pct + (vid_row * vid_height_pct) + (vid_height_pct / 2)
                    self.logger.log(f"[{device_id}] New Target Y calculated: {target_y:.2f}")

                click_vid_y = target_y
                if click_vid_y > 0.95:
                    click_vid_y = 0.90
                    
                self.logger.log(f"[{device_id}] Target Video Coordinate: X={click_vid_x:.2f}, Y={click_vid_y:.2f}")
                d.click(click_vid_x, click_vid_y)
                
                delay_time = random.randint(7, 9)
                self.logger.log(f"[{device_id}] Waiting {delay_time}s for video rendering...")
                smart_sleep(delay_time)

                # 4. Eksekusi Double Click di Tengah Layar (Native Gesture u2)
                self.logger.log(f"[{device_id}] Dispatching Native Double-Tap to screen center (0.5, 0.5)...")
                d.double_click(0.5, 0.5, duration=0.04)
                self.logger.log(f"[{device_id}] Command Executed: Native Double-Tap Dispatched.")
                smart_sleep(1.5)

                # --- FITUR AUTO COMMENTING ---
                comment_text = None
                with self.comment_lock:
                    if self.global_comment_count < comment_target and self.shared_comments:
                        comment_text = self.shared_comments.pop(0) # Ambil komentar pertama lalu hapus dari list
                
                if comment_text and self.is_running:
                    self.logger.log(f"[{device_id}] Extracted Comment from List: '{comment_text}'")
                    
                    # Cek apakah fitur komentar dinonaktifkan oleh kreator
                    if d(textContains="menonaktifkan").exists(timeout=2) or d(descriptionContains="menonaktifkan").exists(timeout=0):
                        self.logger.log(f"[{device_id}] Creator disabled comments! Skipping and saving comment for next video...")
                        with self.comment_lock:
                            # Kembalikan komentar ke antrean paling depan agar tidak terbuang sia-sia
                            self.shared_comments.insert(0, comment_text)
                    else:
                        self.logger.log(f"[{device_id}] Opening Comment section...")
                        # 1. Coba klik text box di bawah
                        if d(textContains="Tambahkan komentar").exists(timeout=2):
                            d(textContains="Tambahkan komentar").click()
                        # 2. Coba klik ikon komentar di sebelah kanan via deskripsi
                        elif d(descriptionMatches="(?i).*komentar.*|.*comment.*").exists(timeout=2):
                            d(descriptionMatches="(?i).*komentar.*|.*comment.*").click()
                        # 3. Fallback terakhir: klik koordinat ikon komentar di kanan layar (Sangat aman dari tombol navigasi)
                        else:
                            self.logger.log(f"[{device_id}] Button not found by text/desc, using coordinate fallback (0.91, 0.60)...")
                            d.click(0.91, 0.60)
                        smart_sleep(2.5)
                        
                        self.logger.log(f"[{device_id}] Typing comment...")
                        edit_box = d(className="android.widget.EditText")
                        if edit_box.exists(timeout=2):
                            edit_box.click() # Pastikan fokus
                            smart_sleep(1)
                            edit_box.set_text(comment_text) # Isi teks
                            smart_sleep(1.5)
                            
                            # Klik tombol kirim merah
                            if d(descriptionMatches="(?i).*kirim.*|.*send.*").exists(timeout=2):
                                d(descriptionMatches="(?i).*kirim.*|.*send.*").click()
                            else:
                                # Dynamic relative calculation
                                bounds = edit_box.info['bounds']
                                screen_width, _ = d.window_size()
                                # Tombol panah biasanya berada di pojok kanan, sedikit di bawah kotak teks
                                send_x = int(screen_width * 0.90) 
                                send_y = bounds['bottom'] + int((bounds['bottom'] - bounds['top']) * 0.7)
                                
                                self.logger.log(f"[{device_id}] Send button text not found, using relative fallback (X={send_x}, Y={send_y})...")
                                d.click(send_x, send_y)
                                
                            self.logger.log(f"[{device_id}] Comment SENT successfully!")
                            with self.comment_lock:
                                self.global_comment_count += 1
                                self.logger.log(f"--- GLOBAL COMMENT PROGRESS: {self.global_comment_count}/{comment_target} ---")
                            smart_sleep(2)
                        else:
                            self.logger.log(f"[{device_id}] Failed to find Edit Box.")
                            
                        # Tutup menu komentar (tekan back)
                        d.press("back")
                        smart_sleep(1.5)
                elif self.global_comment_count >= comment_target and comment_target > 0:
                    self.logger.log(f"[{device_id}] Target comments reached. Skipping comment...")
                elif not comment_text and comment_target > 0:
                    self.logger.log(f"[{device_id}] Comment list is empty! Skipping comment...")
                # ---------------------------

                # 5. Tutup Paksa Aplikasi untuk Melegakan RAM (Clear Memory)
                self.logger.log(f"[{device_id}] Clearing RAM: Force-stopping Clone App and TikTok processes...")
                d.app_stop("com.pengyou.cloneapp")
                d.app_stop("com.zhiliaoapp.musically.go") # TikTok Lite fallback kill
                d.app_stop("com.zhiliaoapp.musically")    # TikTok Global fallback kill
                smart_sleep(2.5)

                # UPDATE STATISTIK
                with self.stats_lock:
                    self.global_clone_count += 1
                    self.device_clone_counts[device_id] = self.device_clone_counts.get(device_id, 0) + 1
                self.update_stats_ui()

                is_last = (clone_num == total_clones)
                if not is_last and self.is_running:
                    # Buka kembali aplikasi Clone App
                    self.logger.log(f"[{device_id}] Reopening Clone App Matrix for the next account...")
                    d.app_start("com.pengyou.cloneapp")
                    smart_sleep(4.5) # Tunggu grid muncul sempurna

                    # 6. Sub-rutin Rotasi IP (Airplane Mode)
                    if clone_num % 10 == 0:
                        self.logger.log(f"[{device_id}] Dispatching IP Rotation (Airplane Mode) every 10 clones...")
                        
                        # Hidupkan mode pesawat & Matikan data via u2 shell
                        d.shell("cmd connectivity airplane-mode enable")
                        d.shell("svc data disable")
                        self.logger.log(f"[{device_id}] IP Reset (Airplane/Data OFF). Menunggu 5 detik...")
                        smart_sleep(5)
                        
                        # Matikan mode pesawat & Hidupkan data via u2 shell
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
            dev_stats = " | ".join([f"[{dev}]: {cnt} clones" for dev, cnt in self.device_clone_counts.items()])
            
        def _update():
            self.lbl_global_clones.config(text=f"Total Clones Executed: {global_c}")
            self.lbl_device_stats.config(text=f"Device Stats: {dev_stats if dev_stats else 'None'}")
            
        self.root.after(0, _update)

    def start_automation(self):
        devices = self.detect_devices_startup()
        if not devices:
            messagebox.showerror("Error", "No connected Android devices detected via ADB!")
            return

        target_account = self.entry_url.get().strip()
        try:
            video_index = int(self.entry_video_index.get().strip())
            total_clones = int(self.entry_clones.get().strip())
            start_index = int(self.entry_start_idx.get().strip())
            comment_target = int(self.entry_comment_target.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Video Index, Clones, Start Index & Comment Target must be clean integers!")
            return

        raw_comments = self.text_prompt.get("1.0", tk.END).strip().split("\n")
        self.shared_comments = [c.strip() for c in raw_comments if c.strip()]

        self.global_comment_count = 0 # Reset hitungan global
        
        # Reset stats
        self.global_clone_count = 0
        self.device_clone_counts = {dev: 0 for dev in devices}
        self.update_stats_ui()

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.logger.log("MASTER CONTROL: Clone App Matrix Orchestration deployed. Spawning parallel threads...")

        self.active_threads = []
        for device_id in devices:
            t = threading.Thread(
                target=self.device_worker_thread, 
                args=(device_id, target_account, video_index, total_clones, start_index, comment_target)
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
        self.logger.log("EMERGENCY STOP TRIGGERED: Stopping all processes safely...")
        self.is_running = False

if __name__ == "__main__":
    root = tk.Tk()
    app = TikTokCloneAppLabU2(root)
    root.mainloop()