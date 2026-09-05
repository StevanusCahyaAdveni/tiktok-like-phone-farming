import os
import re
import time
import random
import queue
import threading
import subprocess
import shutil
import json
import urllib.request
import urllib.error
import uiautomator2 as u2
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


def get_base_dir():
    """Mendapatkan direktori dasar tempat script ini berada."""
    return os.path.dirname(os.path.abspath(__file__))


DEFAULT_OPENROUTER_KEY = ""


def load_saved_api_key():
    """Membaca API Key OpenRouter yang tersimpan di file lokal jika ada."""
    key_file = os.path.join(get_base_dir(), "openrouter_key.txt")
    if os.path.isfile(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception:
            pass
    return os.environ.get("OPENROUTER_API_KEY", DEFAULT_OPENROUTER_KEY)


def save_api_key_to_file(api_key):
    """Menyimpan API Key ke file lokal agar tidak perlu mengetik ulang."""
    key_file = os.path.join(get_base_dir(), "openrouter_key.txt")
    try:
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(api_key.strip())
    except Exception:
        pass


def call_openrouter_ai_comments(api_key, model, context, count):
    """Memanggil OpenRouter API untuk menghasilkan daftar komentar TikTok."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    prompt = (
        f"Buatkan tepat {count} komentar TikTok bahasa Indonesia yang sangat natural, santai, bervariasi, "
        f"dan relevan untuk video dengan konteks: '{context}'.\n"
        f"Gunakan gaya bahasa netizen TikTok asli (gunakan emoji secukupnya, slang khas seperti checkout, racun, spill, worth it, dsb).\n"
        f"PENTING: Tulis HANYA daftar komentar, persis 1 baris per komentar, tanpa nomor urut (jangan ada 1. 2. dst), "
        f"tanpa tanda kutip di awal/akhir, tanpa pengantar atau penutup apapun."
    )
    
    payload = {
        "model": model or "minimax/minimax-m3:free",
        "messages": [
            {
                "role": "system",
                "content": "Kamu adalah asisten pembuat komentar TikTok Indonesia yang sangat natural, relevan, dan bervariasi. Format output HANYA baris-baris komentar tanpa nomor urut."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.85
    }
    
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://tiktok-phone-farming.local",
            "X-Title": "TikTok Multi-Device Farming Bot"
        }
    )
    
    with urllib.request.urlopen(req, timeout=40) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))
        raw_text = resp_data["choices"][0]["message"]["content"]
        
    lines = raw_text.strip().split("\n")
    cleaned_comments = []
    for line in lines:
        cleaned = re.sub(r"^\s*(\d+[\.\)\-:]|\-|\*)\s*", "", line.strip())
        cleaned = cleaned.strip(' "\'“”')
        if cleaned:
            cleaned_comments.append(cleaned)
            
    return cleaned_comments


def find_adb_executable():
    """Mencari lokasi adb.exe dari folder lokal scrcpy atau PATH sistem."""
    base_dir = get_base_dir()
    local_candidates = [
        os.path.join(base_dir, "scrcpy", "adb.exe"),
        os.path.join(base_dir, "scrcpy", "adb"),
        os.path.join(base_dir, "adb.exe"),
    ]
    for cand in local_candidates:
        if os.path.isfile(cand):
            return cand

    adb_name = "adb.exe" if os.name == "nt" else "adb"
    adb_path = shutil.which(adb_name)
    if adb_path:
        return adb_path

    candidates = [
        os.path.join(os.path.expanduser("~"), "Downloads", "scrcpy-win64-v3.3.4", "adb.exe"),
        os.path.join(os.path.expanduser("~"), "Downloads", "platform-tools", "adb.exe"),
        os.path.join("C:\\Program Files\\Android\\Android SDK\\platform-tools", "adb.exe"),
        os.path.join("C:\\Program Files (x86)\\Android\\android-sdk\\platform-tools", "adb.exe"),
        os.path.join("C:\\Program Files\\ASUS\\GlideX", "adb.exe"),
    ]

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    return None


def find_scrcpy_executable():
    """Mencari lokasi scrcpy.exe dari folder lokal scrcpy atau PATH sistem."""
    base_dir = get_base_dir()
    local_candidates = [
        os.path.join(base_dir, "scrcpy", "scrcpy.exe"),
        os.path.join(base_dir, "scrcpy", "scrcpy"),
        os.path.join(base_dir, "scrcpy.exe"),
    ]
    for cand in local_candidates:
        if os.path.isfile(cand):
            return cand

    scrcpy_name = "scrcpy.exe" if os.name == "nt" else "scrcpy"
    scrcpy_path = shutil.which(scrcpy_name)
    if scrcpy_path:
        return scrcpy_path

    candidates = [
        os.path.join(os.path.expanduser("~"), "Downloads", "scrcpy-win64-v3.3.4", "scrcpy.exe"),
        os.path.join("C:\\scrcpy", "scrcpy.exe"),
        os.path.join("C:\\Program Files\\scrcpy", "scrcpy.exe"),
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


class TikTokAllInOneLabU2:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok Multi-Device Farm - Distributed VT Engine (1 HP = 1 VT)")
        self.root.geometry("1000x960")
        self.is_running = False
        self.active_threads = []
        self.scrcpy_processes = []
        
        # Thread Locks & Data Struktur
        self.stats_lock = threading.Lock()
        
        self.global_clone_count = 0
        self.global_liked_videos = 0
        self.global_saved_videos = 0
        self.global_shared_videos = 0
        self.global_comment_count = 0
        
        self.device_stats = {}      # {device_id: {'clones': int, 'likes': int, 'saves': int, 'shares': int, 'comments': int}}
        self.device_ui_widgets = {} # {device_id: widget_dict}
        self.detected_devices = []

        self.setup_gui()
        self.logger = ThreadSafeConsoleLogger(self.log_text)
        self.scan_and_render_devices()

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
        # FRAME 1: GLOBAL CONFIGURATION (TARGET USER & DELAYS)
        # -------------------------------------------------------------
        frame_global = tk.LabelFrame(self.scrollable_content, text=" 1. Pengaturan Global Akun Target & Delay ", padx=10, pady=8)
        frame_global.pack(fill="x", pady=5)
        
        tk.Label(frame_global, text="Username Akun Target (misal: vionex):").grid(row=0, column=0, sticky="w", pady=3)
        self.entry_url = tk.Entry(frame_global, width=28)
        self.entry_url.grid(row=0, column=1, sticky="w", pady=3, padx=5)
        self.entry_url.insert(0, "vionex")

        tk.Label(frame_global, text="Jeda / Tonton per Video (Detik):").grid(row=0, column=2, sticky="w", pady=3, padx=(15, 0))
        self.entry_watch_delay = tk.Entry(frame_global, width=10)
        self.entry_watch_delay.grid(row=0, column=3, sticky="w", pady=3, padx=5)
        self.entry_watch_delay.insert(0, "6")

        tk.Label(frame_global, text="Mode Pesawat (Rotasi IP) per berapa Akun:").grid(row=1, column=0, sticky="w", pady=3)
        self.entry_airplane_interval = tk.Entry(frame_global, width=28)
        self.entry_airplane_interval.grid(row=1, column=1, sticky="w", pady=3, padx=5)
        self.entry_airplane_interval.insert(0, "10")

        tk.Label(frame_global, text="(0 = Nonaktifkan Rotasi IP)", fg="#7f8c8d", font=("Arial", 8, "italic")).grid(row=1, column=2, columnspan=2, sticky="w", padx=(15, 0))

        # -------------------------------------------------------------
        # FRAME 2: SCREEN MIRRORING & DISPLAY CONTROLS (SCRCPY)
        # -------------------------------------------------------------
        frame_mirror = tk.LabelFrame(self.scrollable_content, text=" 2. Tampilan Layar HP di PC (Live Mirroring scrcpy) ", padx=10, pady=8)
        frame_mirror.pack(fill="x", pady=5)

        btn_mirror_all = tk.Button(
            frame_mirror, 
            text="📱 Buka Layar Semua HP (Berjejer Rapi)", 
            bg="#8e44ad", 
            fg="white", 
            font=("Arial", 9, "bold"), 
            command=self.open_all_screens_scrcpy
        )
        btn_mirror_all.pack(side="left", padx=(0, 10), ipady=2)

        btn_close_mirrors = tk.Button(
            frame_mirror, 
            text="❌ Tutup Semua Layar Mirror", 
            bg="#95a5a6", 
            fg="white", 
            font=("Arial", 9), 
            command=self.close_all_scrcpy_mirrors
        )
        btn_close_mirrors.pack(side="left", padx=5, ipady=2)

        self.var_auto_mirror = tk.BooleanVar(value=False)
        chk_auto_mirror = tk.Checkbutton(
            frame_mirror, 
            text="Otomatis buka layar semua HP saat Start", 
            variable=self.var_auto_mirror,
            font=("Arial", 9)
        )
        chk_auto_mirror.pack(side="left", padx=(15, 0))

        # -------------------------------------------------------------
        # FRAME 3: AI COMMENT GENERATOR (OPENROUTER - MINIMAX-M3:FREE)
        # -------------------------------------------------------------
        frame_ai = tk.LabelFrame(
            self.scrollable_content, 
            text=" 3. ✨ AI Comment Generator (OpenRouter - minimax/minimax-m3:free) ", 
            padx=10, 
            pady=8,
            fg="#d35400",
            font=("Arial", 9, "bold")
        )
        frame_ai.pack(fill="x", pady=5)

        # Row 1: API Key & Model
        row_ai_1 = tk.Frame(frame_ai)
        row_ai_1.pack(fill="x", pady=2)

        tk.Label(row_ai_1, text="OpenRouter API Key:").pack(side="left")
        self.entry_ai_key = tk.Entry(row_ai_1, width=32, show="*")
        self.entry_ai_key.pack(side="left", padx=(4, 6))
        saved_key = load_saved_api_key()
        if saved_key:
            self.entry_ai_key.insert(0, saved_key)

        self.btn_toggle_key = tk.Button(row_ai_1, text="👁", width=3, command=self.toggle_api_key_visibility)
        self.btn_toggle_key.pack(side="left", padx=(0, 15))

        tk.Label(row_ai_1, text="Model:").pack(side="left")
        self.entry_ai_model = tk.Entry(row_ai_1, width=24)
        self.entry_ai_model.pack(side="left", padx=(4, 5))
        self.entry_ai_model.insert(0, "minimax/minimax-m3:free")

        # Row 2: Konteks Konten & Jumlah & Target HP
        row_ai_2 = tk.Frame(frame_ai)
        row_ai_2.pack(fill="x", pady=(6, 2))

        tk.Label(row_ai_2, text="Konteks / Topik Konten:").pack(side="left")
        self.entry_ai_context = tk.Entry(row_ai_2, width=34)
        self.entry_ai_context.pack(side="left", padx=(4, 10))
        self.entry_ai_context.insert(0, "Review skincare serum pencerah wajah glowing")

        tk.Label(row_ai_2, text="Jumlah Komen:").pack(side="left")
        self.entry_ai_count = tk.Entry(row_ai_2, width=6)
        self.entry_ai_count.pack(side="left", padx=(4, 10))
        self.entry_ai_count.insert(0, "15")

        tk.Label(row_ai_2, text="Terapkan Ke:").pack(side="left")
        self.combo_ai_target = ttk.Combobox(row_ai_2, values=["Semua HP"], state="readonly", width=12)
        self.combo_ai_target.pack(side="left", padx=(4, 12))
        self.combo_ai_target.set("Semua HP")

        self.btn_generate_ai = tk.Button(
            row_ai_2,
            text="✨ Generate Komentar AI",
            bg="#e67e22",
            fg="white",
            font=("Arial", 9, "bold"),
            command=self.handle_generate_ai_comments
        )
        self.btn_generate_ai.pack(side="left", padx=5, ipady=1)

        # -------------------------------------------------------------
        # FRAME 4: PER-DEVICE DISTRIBUTED VT CONFIGURATION
        # -------------------------------------------------------------
        self.frame_devices = tk.LabelFrame(
            self.scrollable_content, 
            text=" 4. Konfigurasi Khusus Per-Device (1 HP = 1 Target VT di Tab Liked) ", 
            padx=10, 
            pady=8
        )
        self.frame_devices.pack(fill="x", pady=5)

        self.devices_container = tk.Frame(self.frame_devices)
        self.devices_container.pack(fill="x", expand=True)

        # -------------------------------------------------------------
        # FRAME 5: CONTROL BUTTONS
        # -------------------------------------------------------------
        frame_controls = tk.Frame(self.scrollable_content, pady=8)
        frame_controls.pack(fill="x", pady=5)
        
        self.btn_start = tk.Button(
            frame_controls, 
            text="▶ Start Multi-Device Farm Engine", 
            bg="#2ecc71", 
            fg="white", 
            font=("Arial", 11, "bold"), 
            command=self.start_automation
        )
        self.btn_start.pack(side="left", padx=5, ipadx=12, ipady=3)

        self.btn_stop = tk.Button(
            frame_controls, 
            text="⏹ Emergency Stop", 
            bg="#e74c3c", 
            fg="white", 
            font=("Arial", 11, "bold"), 
            command=self.stop_automation, 
            state=tk.DISABLED
        )
        self.btn_stop.pack(side="left", padx=5, ipadx=12, ipady=3)

        self.btn_refresh = tk.Button(
            frame_controls, 
            text="🔄 Scan Devices / Refresh Form HP", 
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"), 
            command=self.scan_and_render_devices
        )
        self.btn_refresh.pack(side="right", padx=5, ipady=2)

        # -------------------------------------------------------------
        # FRAME 6: LIVE STATISTICS
        # -------------------------------------------------------------
        frame_stats = tk.LabelFrame(self.scrollable_content, text=" 5. Live Statistics ", padx=10, pady=8)
        frame_stats.pack(fill="x", pady=5)
        
        self.lbl_global_stats = tk.Label(
            frame_stats, 
            text="Total Clones: 0 | Total Likes: 0 | Total Simpan: 0 | Total Share: 0 | Total Comments: 0", 
            font=("Arial", 10, "bold"), 
            fg="#2980b9"
        )
        self.lbl_global_stats.pack(anchor="w")

        self.lbl_device_stats = tk.Label(frame_stats, text="Device Stats: Belum ada eksekusi", font=("Arial", 9), fg="#27ae60", justify="left")
        self.lbl_device_stats.pack(anchor="w", pady=(4, 0))

        # -------------------------------------------------------------
        # FRAME 7: EXECUTION LOGS CONSOLE
        # -------------------------------------------------------------
        frame_log = tk.LabelFrame(self.scrollable_content, text=" 6. Execution Logs Console ", padx=10, pady=8)
        frame_log.pack(fill="both", expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame_log, bg="#111111", fg="#00ff66", font=("Consolas", 9), height=14)
        self.log_text.pack(fill="both", expand=True)

    def toggle_api_key_visibility(self):
        """Toggle hide/show OpenRouter API Key."""
        if self.entry_ai_key.cget("show") == "":
            self.entry_ai_key.config(show="*")
        else:
            self.entry_ai_key.config(show="")

    def handle_generate_ai_comments(self):
        """Menjalankan proses generate komentar AI via OpenRouter secara background."""
        api_key = self.entry_ai_key.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Silakan masukkan OpenRouter API Key terlebih dahulu!\n(Bisa didapat gratis di openrouter.ai)")
            return

        save_api_key_to_file(api_key)

        model = self.entry_ai_model.get().strip() or "minimax/minimax-m3:free"
        context = self.entry_ai_context.get().strip()
        if not context:
            messagebox.showerror("Error", "Konteks / Topik Konten tidak boleh kosong!")
            return

        try:
            count = int(self.entry_ai_count.get().strip())
            if count <= 0: count = 10
        except ValueError:
            count = 10

        target_selection = self.combo_ai_target.get()

        self.btn_generate_ai.config(state=tk.DISABLED, text="⏳ Generating AI...")
        self.logger.log(f"AI COMMENT: Requesting {count} comments from OpenRouter ({model}) with context: '{context}'...")

        def _worker():
            try:
                comments = call_openrouter_ai_comments(api_key, model, context, count)
                if not comments:
                    raise Exception("Output komentar kosong dari AI.")

                cmt_text = "\n".join(comments)

                def _apply_to_ui():
                    applied_count = 0
                    if target_selection == "Semua HP":
                        for dev_id, w in self.device_ui_widgets.items():
                            w['comments_text'].delete("1.0", tk.END)
                            w['comments_text'].insert(tk.END, cmt_text)
                            w['target_cmt_entry'].delete(0, tk.END)
                            w['target_cmt_entry'].insert(0, str(len(comments)))
                            applied_count += 1
                    else:
                        for idx, dev_id in enumerate(self.detected_devices, start=1):
                            if target_selection == f"HP #{idx}":
                                if dev_id in self.device_ui_widgets:
                                    w = self.device_ui_widgets[dev_id]
                                    w['comments_text'].delete("1.0", tk.END)
                                    w['comments_text'].insert(tk.END, cmt_text)
                                    w['target_cmt_entry'].delete(0, tk.END)
                                    w['target_cmt_entry'].insert(0, str(len(comments)))
                                    applied_count += 1
                                break

                    self.logger.log(f"AI COMMENT: Sukses men-generate {len(comments)} komentar dan diterapkan ke {target_selection}!")
                    self.btn_generate_ai.config(state=tk.NORMAL, text="✨ Generate Komentar AI")
                    messagebox.showinfo("Sukses", f"Berhasil men-generate {len(comments)} komentar AI dan dimasukkan ke {target_selection}!")

                self.root.after(0, _apply_to_ui)

            except Exception as e:
                def _error():
                    self.logger.log(f"AI COMMENT ERROR: Gagal generate komentar - {str(e)}")
                    self.btn_generate_ai.config(state=tk.NORMAL, text="✨ Generate Komentar AI")
                    messagebox.showerror("AI Generation Error", f"Gagal menghubungi OpenRouter AI:\n{str(e)}")

                self.root.after(0, _error)

        t = threading.Thread(target=_worker)
        t.daemon = True
        t.start()

    def generate_ai_for_single_hp(self, dev_id, hp_idx):
        """Memunculkan dialog cepat untuk men-generate komentar AI khusus HP ini."""
        api_key = self.entry_ai_key.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Silakan masukkan OpenRouter API Key pada kolom Section 3 terlebih dahulu!")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"✨ AI Comment Gen - HP #{hp_idx}")
        dialog.geometry("450x230")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text=f"Generate Komentar AI untuk HP #{hp_idx}", font=("Arial", 10, "bold"), fg="#2980b9").pack(pady=8)

        frame_d = tk.Frame(dialog, padx=15)
        frame_d.pack(fill="x")

        tk.Label(frame_d, text="Konteks / Topik Konten VT:").grid(row=0, column=0, sticky="w", pady=4)
        entry_ctx = tk.Entry(frame_d, width=32)
        entry_ctx.grid(row=0, column=1, pady=4, padx=5)
        entry_ctx.insert(0, self.entry_ai_context.get().strip() or "Review produk keren banget racun tiktok")

        tk.Label(frame_d, text="Jumlah Komentar:").grid(row=1, column=0, sticky="w", pady=4)
        entry_cnt = tk.Entry(frame_d, width=10)
        entry_cnt.grid(row=1, column=1, sticky="w", pady=4, padx=5)
        entry_cnt.insert(0, "15")

        lbl_status = tk.Label(dialog, text="", fg="#e67e22")
        lbl_status.pack(pady=4)

        def _do_gen():
            ctx = entry_ctx.get().strip()
            if not ctx:
                messagebox.showerror("Error", "Konteks tidak boleh kosong!")
                return
            try:
                cnt = int(entry_cnt.get().strip())
            except ValueError:
                cnt = 15

            btn_submit.config(state=tk.DISABLED, text="⏳ Generating...")
            lbl_status.config(text="Sedang menghubungi OpenRouter AI...")

            def _t_work():
                try:
                    model = self.entry_ai_model.get().strip() or "minimax/minimax-m3:free"
                    cmts = call_openrouter_ai_comments(api_key, model, ctx, cnt)
                    
                    def _update_hp():
                        if dev_id in self.device_ui_widgets:
                            w = self.device_ui_widgets[dev_id]
                            w['comments_text'].delete("1.0", tk.END)
                            w['comments_text'].insert(tk.END, "\n".join(cmts))
                            w['target_cmt_entry'].delete(0, tk.END)
                            w['target_cmt_entry'].insert(0, str(len(cmts)))
                        self.logger.log(f"AI COMMENT: Berhasil generate {len(cmts)} komentar untuk HP #{hp_idx}!")
                        dialog.destroy()
                        messagebox.showinfo("Sukses", f"Berhasil memasukkan {len(cmts)} komentar ke HP #{hp_idx}!")

                    self.root.after(0, _update_hp)
                except Exception as ex:
                    def _err_dlg():
                        btn_submit.config(state=tk.NORMAL, text="✨ Generate")
                        lbl_status.config(text="")
                        messagebox.showerror("Error", f"Gagal generate komentar:\n{str(ex)}")
                    self.root.after(0, _err_dlg)

            t = threading.Thread(target=_t_work)
            t.daemon = True
            t.start()

        btn_submit = tk.Button(dialog, text="✨ Generate", bg="#e67e22", fg="white", font=("Arial", 9, "bold"), command=_do_gen)
        btn_submit.pack(pady=6, ipady=2, ipadx=10)

    def open_single_screen_scrcpy(self, device_id, title_suffix=""):
        """Membuka jendela live screen mirroring scrcpy untuk satu device tertentu."""
        scrcpy_exe = find_scrcpy_executable()
        if not scrcpy_exe:
            self.logger.log("ERROR: scrcpy.exe tidak ditemukan!")
            messagebox.showerror("scrcpy Error", "File scrcpy.exe tidak ditemukan di folder lokal atau sistem!")
            return

        cmd = [
            scrcpy_exe,
            "-s", device_id,
            "--window-title", f"HP {title_suffix} ({device_id})",
            "--window-width", "340",
            "--stay-awake"
        ]

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.scrcpy_processes.append(proc)
            self.logger.log(f"[{device_id}] Live screen window opened via scrcpy.")
        except Exception as e:
            self.logger.log(f"[{device_id}] Gagal membuka scrcpy: {str(e)}")

    def open_all_screens_scrcpy(self):
        """Membuka jendela live mirroring scrcpy untuk semua device berjejer rapi di layar PC."""
        scrcpy_exe = find_scrcpy_executable()
        if not scrcpy_exe:
            self.logger.log("ERROR: scrcpy.exe tidak ditemukan!")
            messagebox.showerror("scrcpy Error", "File scrcpy.exe tidak ditemukan di folder lokal atau sistem!")
            return

        if not self.detected_devices:
            messagebox.showinfo("Info", "Tidak ada perangkat yang terdeteksi.")
            return

        win_w = 330
        win_h = 680
        start_x = 20
        start_y = 40
        gap_x = win_w + 10

        self.logger.log(f"Membuka tampilan layar live untuk {len(self.detected_devices)} HP berjejer...")

        for idx, dev_id in enumerate(self.detected_devices, start=1):
            pos_x = start_x + ((idx - 1) * gap_x)
            pos_y = start_y
            
            cmd = [
                scrcpy_exe,
                "-s", dev_id,
                "--window-title", f"HP #{idx} ({dev_id})",
                "--window-x", str(pos_x),
                "--window-y", str(pos_y),
                "--window-width", str(win_w),
                "--window-height", str(win_h),
                "--stay-awake"
            ]

            try:
                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.scrcpy_processes.append(proc)
            except Exception as e:
                self.logger.log(f"[{dev_id}] Gagal membuka scrcpy: {str(e)}")

    def close_all_scrcpy_mirrors(self):
        """Menutup seluruh jendela scrcpy yang sedang aktif."""
        for p in self.scrcpy_processes:
            try:
                p.terminate()
            except Exception:
                pass
        self.scrcpy_processes.clear()
        
        try:
            subprocess.run(["taskkill", "/F", "/IM", "scrcpy.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.logger.log("Semua jendela mirroring scrcpy telah ditutup.")

    def scan_and_render_devices(self):
        """Mendeteksi HP via ADB dan otomatis merender card konfigurasi untuk setiap HP."""
        adb_path = find_adb_executable()
        if adb_path is None:
            self.logger.log("CRITICAL ERROR: ADB is not installed atau tidak ditemukan!")
            messagebox.showerror(
                "ADB Error",
                "ADB (Android Debug Bridge) tidak terdeteksi!\n\n" \
                "Pastikan Android SDK Platform Tools atau folder scrcpy sudah ada."
            )
            return

        try:
            result = subprocess.run([adb_path, "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
        except Exception as e:
            self.logger.log(f"CRITICAL ERROR: ADB execution failed - {str(e)}")
            return

        devices = []
        lines = output.splitlines()
        for line in lines[1:]:
            if line.strip() and "device" in line:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])

        self.detected_devices = devices
        
        # Update combobox pilihan target di Section AI
        target_options = ["Semua HP"] + [f"HP #{i}" for i in range(1, len(devices) + 1)]
        self.combo_ai_target.config(values=target_options)
        if self.combo_ai_target.get() not in target_options:
            self.combo_ai_target.set("Semua HP")

        # Bersihkan container form sebelumnya
        for widget in self.devices_container.winfo_children():
            widget.destroy()

        self.device_ui_widgets = {}

        if not devices:
            lbl_empty = tk.Label(
                self.devices_container, 
                text="⚠️ Tidak ada perangkat Android terdeteksi. Silakan colokkan HP (USB Debugging ON) lalu klik 'Scan Devices'.", 
                fg="#e74c3c", 
                font=("Arial", 10, "bold"),
                pady=15
            )
            lbl_empty.pack()
            self.logger.log("Scan Devices: 0 devices connected.")
            return

        self.logger.log(f"Scan Devices: Ditemukan {len(devices)} HP aktif.")

        default_comments_pool = [
            "komen1\nkomen2\nkomen3",
            "komen1\nkomen2\nkomen3",
            "komen1\nkomen2\nkomen3",
            "komen1\nkomen2\nkomen3",
            "komen1\nkomen2\nkomen3",
            "komen1\nkomen2\nkomen3"
        ]

        for idx, dev_id in enumerate(devices, start=1):
            default_vt = idx  # Default: HP 1 -> VT 1, HP 2 -> VT 2, HP 3 -> VT 3, dst.
            
            card_frame = tk.LabelFrame(
                self.devices_container, 
                text=f" 📱 HP #{idx} [Device ID: {dev_id}] - Konfigurasi Khusus ", 
                font=("Arial", 9, "bold"), 
                fg="#2980b9", 
                padx=10, 
                pady=6
            )
            card_frame.pack(fill="x", pady=6)

            # Row 1: Target VT, Range Clone, & Tombol Buka Layar HP Ini
            row1 = tk.Frame(card_frame)
            row1.pack(fill="x", pady=2)

            tk.Label(row1, text="Target VT ke-:", font=("Arial", 9, "bold"), fg="#c0392b").pack(side="left")
            entry_vt = tk.Entry(row1, width=6, font=("Arial", 9, "bold"))
            entry_vt.pack(side="left", padx=(4, 15))
            entry_vt.insert(0, str(default_vt))

            tk.Label(row1, text="Mulai Clone:").pack(side="left")
            entry_start_clone = tk.Entry(row1, width=7)
            entry_start_clone.pack(side="left", padx=(4, 10))
            entry_start_clone.insert(0, "1")

            tk.Label(row1, text="Sampai Clone:").pack(side="left")
            entry_end_clone = tk.Entry(row1, width=7)
            entry_end_clone.pack(side="left", padx=(4, 10))
            entry_end_clone.insert(0, "50")

            tk.Label(row1, text="Custom:").pack(side="left")
            entry_custom_clones = tk.Entry(row1, width=16)
            entry_custom_clones.pack(side="left", padx=(4, 10))
            entry_custom_clones.insert(0, "")

            # Tombol buka layar per HP
            btn_view_screen = tk.Button(
                row1, 
                text="📱 Tampilkan Layar", 
                bg="#34495e", 
                fg="white", 
                font=("Arial", 8, "bold"),
                command=lambda d_id=dev_id, num=idx: self.open_single_screen_scrcpy(d_id, f"#{num}")
            )
            btn_view_screen.pack(side="right", padx=5)

            # Row 2: Target Like, Simpan, Share, Komen
            row2 = tk.Frame(card_frame)
            row2.pack(fill="x", pady=3)

            tk.Label(row2, text="Target Like:").pack(side="left")
            entry_target_like = tk.Entry(row2, width=6)
            entry_target_like.pack(side="left", padx=(4, 12))
            entry_target_like.insert(0, "50")

            tk.Label(row2, text="Target Simpan:").pack(side="left")
            entry_target_save = tk.Entry(row2, width=6)
            entry_target_save.pack(side="left", padx=(4, 12))
            entry_target_save.insert(0, "0")

            tk.Label(row2, text="Target Share:").pack(side="left")
            entry_target_share = tk.Entry(row2, width=6)
            entry_target_share.pack(side="left", padx=(4, 12))
            entry_target_share.insert(0, "0")

            tk.Label(row2, text="Mulai Komen Akun #:").pack(side="left")
            entry_start_cmt_acc = tk.Entry(row2, width=6)
            entry_start_cmt_acc.pack(side="left", padx=(4, 12))
            entry_start_cmt_acc.insert(0, "1")

            tk.Label(row2, text="Target Komen:").pack(side="left")
            entry_target_cmt = tk.Entry(row2, width=6)
            entry_target_cmt.pack(side="left", padx=(4, 5))
            entry_target_cmt.insert(0, "0")

            tk.Label(row2, text="(0 = sesuai baris teks)", fg="#7f8c8d", font=("Arial", 8, "italic")).pack(side="left", padx=(5, 0))

            # Row 3: List Komentar Text Box + Tombol Quick AI
            row3_hdr = tk.Frame(card_frame)
            row3_hdr.pack(fill="x", pady=(4, 2))

            tk.Label(row3_hdr, text=f"List Komentar untuk VT HP #{idx} (1 Baris = 1 Komentar):", font=("Arial", 8, "bold")).pack(side="left")

            btn_quick_ai = tk.Button(
                row3_hdr,
                text="✨ AI Gen untuk HP Ini",
                bg="#e67e22",
                fg="white",
                font=("Arial", 8, "bold"),
                command=lambda d_id=dev_id, num=idx: self.generate_ai_for_single_hp(d_id, num)
            )
            btn_quick_ai.pack(side="right", padx=5)

            text_comments = tk.Text(card_frame, width=85, height=3, font=("Segoe UI", 9))
            text_comments.pack(fill="x", pady=2)

            sample_idx = (idx - 1) % len(default_comments_pool)
            text_comments.insert(tk.END, default_comments_pool[sample_idx])

            self.device_ui_widgets[dev_id] = {
                'vt_entry': entry_vt,
                'start_clone_entry': entry_start_clone,
                'end_clone_entry': entry_end_clone,
                'custom_clones_entry': entry_custom_clones,
                'like_entry': entry_target_like,
                'save_entry': entry_target_save,
                'share_entry': entry_target_share,
                'start_cmt_acc_entry': entry_start_cmt_acc,
                'target_cmt_entry': entry_target_cmt,
                'comments_text': text_comments,
            }

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

        # Urutkan berdasarkan luas area terbesar dan posisi yang lebih bawah (judul app selalu di bawah ikon)
        valid_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return valid_candidates[0][0]

    def device_worker_thread(self, device_id, target_account, watch_delay, airplane_interval, dev_cfg):
        """Worker Thread independen untuk 1 HP yang mengurus 1 Target VT."""
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

        target_vt = dev_cfg['target_vt']
        clone_names_list = dev_cfg['clone_names']
        target_likes = dev_cfg['target_likes']
        target_saves = dev_cfg['target_saves']
        target_shares = dev_cfg['target_shares']
        start_cmt_acc = dev_cfg['start_cmt_acc']
        target_comments = dev_cfg['target_comments']
        comments_queue = list(dev_cfg['comments_list'])

        total_clones_count = len(clone_names_list)

        self.logger.log(f"[{device_id}] CONFIG LOADED: Target VT #{target_vt} | Clones: {total_clones_count} | Target Likes: {target_likes}, Saves: {target_saves}, Shares: {target_shares}, Comments: {target_comments}")

        try:
            for idx, clone_name in enumerate(clone_names_list, start=1):
                if not self.is_running: raise StopAutomationException()
                
                self.logger.log(f"[{device_id}] [{idx}/{total_clones_count}] Launching Clone App for Account '{clone_name}' (Targeting VT #{target_vt})...")
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
                
                # 4. BUKA TARGET VT SPESIFIK KE-N (Grid Dinamis 3 Kolom)
                self.logger.log(f"[{device_id}] Calculating coordinates for Target VT #{target_vt}...")
                
                vid_idx_0_based = max(0, target_vt - 1)
                vid_row = vid_idx_0_based // 3
                vid_col = vid_idx_0_based % 3
                
                vid_col_x = [0.16, 0.50, 0.83]
                click_vid_x = vid_col_x[vid_col]
                
                vid_height_pct = ((screen_width / 3.0) * (16.0 / 9.0)) / screen_height
                current_tab_y_pct = tab_center_y / screen_height
                target_y = current_tab_y_pct + (vid_row * vid_height_pct) + (vid_height_pct / 2)
                
                # Jika target jatuh di bawah layar (> 88%), scroll ke bawah
                while target_y > 0.88:
                    self.logger.log(f"[{device_id}] Target VT #{target_vt} Y ({target_y:.2f}) is off-screen. Scrolling down...")
                    d.swipe(0.5, 0.80, 0.5, 0.30, duration=1.0)
                    smart_sleep(2)
                    
                    if heart_tab.exists(timeout=2):
                        bounds = heart_tab.info['bounds']
                        tab_center_y = bounds['top'] + ((bounds['bottom'] - bounds['top']) // 2)
                        current_tab_y_pct = tab_center_y / screen_height
                    else:
                        current_tab_y_pct = 0.15
                        
                    target_y = current_tab_y_pct + (vid_row * vid_height_pct) + (vid_height_pct / 2)
                    self.logger.log(f"[{device_id}] New Target Y calculated: {target_y:.2f}")

                click_vid_y = target_y
                if click_vid_y > 0.95:
                    click_vid_y = 0.90
                    
                self.logger.log(f"[{device_id}] Opening Target VT #{target_vt} at Coordinate: X={click_vid_x:.2f}, Y={click_vid_y:.2f}...")
                d.click(click_vid_x, click_vid_y)
                
                # Tonton video sesuai delay
                curr_delay = max(3, watch_delay + random.randint(-1, 2))
                self.logger.log(f"[{device_id}] Watching Target VT #{target_vt} for {curr_delay} seconds...")
                smart_sleep(curr_delay)
                
                # A. EVALUASI DAN EKSEKUSI LIKE (DOUBLE TAP)
                with self.stats_lock:
                    dev_likes = self.device_stats[device_id]['likes']
                
                if target_likes == 0 or dev_likes < target_likes:
                    self.logger.log(f"[{device_id}] Dispatching Double-Tap to LIKE VT #{target_vt}...")
                    d.double_click(0.5, 0.5, duration=0.04)
                    with self.stats_lock:
                        self.global_liked_videos += 1
                        self.device_stats[device_id]['likes'] += 1
                    self.update_stats_ui()
                    smart_sleep(1.5)

                # B. EVALUASI DAN EKSEKUSI SIMPAN / BOOKMARK
                with self.stats_lock:
                    dev_saves = self.device_stats[device_id]['saves']

                if target_saves > 0 and dev_saves < target_saves:
                    self.logger.log(f"[{device_id}] Executing SIMPAN / BOOKMARK action on VT #{target_vt}...")
                    saved = False
                    
                    bookmark_btn = d(descriptionMatches="(?i).*favorit.*|.*simpan.*|.*bookmark.*|.*save.*|.*koleksi.*|.*collect.*")
                    if not bookmark_btn.exists(timeout=1):
                        bookmark_btn = d(resourceIdMatches="(?i).*favorite.*|.*bookmark.*|.*collect.*")

                    if bookmark_btn.exists(timeout=1):
                        bookmark_btn.click()
                        saved = True
                    else:
                        self.logger.log(f"[{device_id}] Bookmark icon not found by desc, clicking coordinate (0.91, 0.72)...")
                        d.click(0.91, 0.72)
                        saved = True

                    if saved:
                        self.logger.log(f"[{device_id}] VT #{target_vt} SAVED / BOOKMARKED successfully!")
                        with self.stats_lock:
                            self.global_saved_videos += 1
                            self.device_stats[device_id]['saves'] += 1
                        self.update_stats_ui()
                        smart_sleep(1.5)

                # C. EVALUASI DAN EKSEKUSI SHARE (SALIN TAUTAN)
                with self.stats_lock:
                    dev_shares = self.device_stats[device_id]['shares']

                if target_shares > 0 and dev_shares < target_shares:
                    self.logger.log(f"[{device_id}] Executing SHARE -> SALIN TAUTAN action on VT #{target_vt}...")
                    
                    share_btn = d(descriptionMatches="(?i).*bagikan.*|.*share.*")
                    if not share_btn.exists(timeout=1):
                        share_btn = d(resourceIdMatches="(?i).*share.*")

                    if share_btn.exists(timeout=1):
                        share_btn.click()
                    else:
                        self.logger.log(f"[{device_id}] Share icon not found by desc, clicking coordinate (0.91, 0.80)...")
                        d.click(0.91, 0.80)
                    smart_sleep(2.5)

                    self.logger.log(f"[{device_id}] Clicking 'Salin Tautan' button...")
                    link_btn = d(textMatches="(?i).*salin tautan.*|.*copy link.*")
                    if not link_btn.exists(timeout=2):
                        link_btn = d(descriptionMatches="(?i).*salin tautan.*|.*copy link.*")

                    copied = False
                    if link_btn.exists(timeout=2):
                        link_btn.click()
                        copied = True
                    else:
                        self.logger.log(f"[{device_id}] 'Salin Tautan' text not found, clicking first share button (0.12, 0.72)...")
                        d.click(0.12, 0.72)
                        copied = True

                    smart_sleep(1.5)

                    # Hanya tutup panel share jika masih terbuka
                    if d(textMatches="(?i).*bagikan ke.*|.*share to.*").exists(timeout=0):
                        close_btn = d(descriptionMatches="(?i).*tutup.*|.*close.*")
                        if close_btn.exists(timeout=0):
                            close_btn.click()
                        else:
                            d.press("back")
                        smart_sleep(1.0)

                    if copied:
                        self.logger.log(f"[{device_id}] VT #{target_vt} Link COPIED / SHARED successfully!")
                        with self.stats_lock:
                            self.global_shared_videos += 1
                            self.device_stats[device_id]['shares'] += 1
                        self.update_stats_ui()
                        smart_sleep(1.0)

                # D. EVALUASI DAN EKSEKUSI KOMENTAR
                clone_num_val = int(clone_name) if str(clone_name).isdigit() else idx
                with self.stats_lock:
                    dev_cmts = self.device_stats[device_id]['comments']

                should_comment = False
                comment_text = None
                if clone_num_val >= start_cmt_acc and (target_comments > 0 and dev_cmts < target_comments):
                    if len(comments_queue) > 0:
                        comment_text = comments_queue.pop(0)
                        should_comment = True

                if should_comment and comment_text and self.is_running:
                    self.logger.log(f"[{device_id}] Extracted Comment for VT #{target_vt}: '{comment_text}'")
                    
                    if d(textContains="menonaktifkan").exists(timeout=2) or d(descriptionContains="menonaktifkan").exists(timeout=0):
                        self.logger.log(f"[{device_id}] Creator disabled comments! Returning comment back to queue...")
                        comments_queue.insert(0, comment_text)
                    else:
                        self.logger.log(f"[{device_id}] Opening Comment section...")
                        if d(descriptionMatches="(?i).*komentar.*|.*comment.*").exists(timeout=1):
                            d(descriptionMatches="(?i).*komentar.*|.*comment.*").click()
                        elif d(resourceIdMatches="(?i).*comment.*").exists(timeout=1):
                            d(resourceIdMatches="(?i).*comment.*").click()
                        elif d(textContains="Tambahkan komentar").exists(timeout=1):
                            d(textContains="Tambahkan komentar").click()
                        else:
                            d.click(0.91, 0.64)
                        smart_sleep(2.5)

                        self.logger.log(f"[{device_id}] Focusing Comment Input Box...")
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
                            edit_box.click()
                            smart_sleep(0.8)
                            edit_box.set_text(comment_text)
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

                            self.logger.log(f"[{device_id}] Comment SENT successfully on VT #{target_vt}!")
                            with self.stats_lock:
                                self.global_comment_count += 1
                                self.device_stats[device_id]['comments'] += 1
                            self.update_stats_ui()
                            smart_sleep(2)
                        else:
                            self.logger.log(f"[{device_id}] Failed to find Edit Box. Returning comment back to queue...")
                            comments_queue.insert(0, comment_text)

                        # Tutup lembar komentar HANYA via tombol X agar tidak keluar dari video
                        self.logger.log(f"[{device_id}] Closing Comment sheet...")
                        close_btn = d(descriptionMatches="(?i).*tutup.*|.*close.*")
                        if not close_btn.exists(timeout=0):
                            close_btn = d(resourceIdMatches="(?i).*close.*|.*btn_close.*|.*iv_close.*")
                            
                        if close_btn.exists(timeout=1):
                            close_btn.click()
                            smart_sleep(1.0)

                self.logger.log(f"[{device_id}] SUCCESS: Finished actions on Clone '{clone_name}' for VT #{target_vt}!")

                # 5. TUTUP PAKSA APLIKASI UNTUK MELEGAKAN RAM
                self.logger.log(f"[{device_id}] Clearing RAM: Force-stopping Clone App and TikTok processes...")
                d.app_stop("com.pengyou.cloneapp")
                d.app_stop("com.zhiliaoapp.musically.go")
                d.app_stop("com.zhiliaoapp.musically")
                smart_sleep(2.5)

                # UPDATE STATISTIK AKUN
                with self.stats_lock:
                    self.global_clone_count += 1
                    self.device_stats[device_id]['clones'] += 1
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

            self.logger.log(f"[{device_id}] Worker Thread finished execution lifecycle for VT #{target_vt}.")
        except StopAutomationException:
            self.logger.log(f"[{device_id}] 🛑 EMERGENCY STOP: Worker thread forcefully halted!")

    def update_stats_ui(self):
        """Thread-safe update of the statistics labels."""
        with self.stats_lock:
            global_c = self.global_clone_count
            global_l = self.global_liked_videos
            global_s = self.global_saved_videos
            global_sh = self.global_shared_videos
            global_cmt = self.global_comment_count
            
            # Breakdown per device
            dev_stats_list = []
            for dev, st in self.device_stats.items():
                vt_target = self.device_configs.get(dev, {}).get('target_vt', '?') if hasattr(self, 'device_configs') else '?'
                dev_stats_list.append(
                    f"📱 [{dev}] -> VT #{vt_target} | Clones: {st['clones']} | Likes: {st['likes']} | Simpan: {st['saves']} | Share: {st['shares']} | Komen: {st['comments']}"
                )
            dev_stats_str = "\n".join(dev_stats_list) if dev_stats_list else "Belum ada eksekusi"
            
        def _update():
            self.lbl_global_stats.config(
                text=f"Total Clones: {global_c} | Total Likes: {global_l} | Total Simpan: {global_s} | Total Share: {global_sh} | Total Comments: {global_cmt}"
            )
            self.lbl_device_stats.config(text=dev_stats_str)
            
        self.root.after(0, _update)

    def start_automation(self):
        if not self.detected_devices:
            self.scan_and_render_devices()
            if not self.detected_devices:
                messagebox.showerror("Error", "Tidak ada perangkat Android yang terdeteksi via ADB!")
                return

        target_account = self.entry_url.get().strip()
        if not target_account:
            messagebox.showerror("Error", "Username akun target tidak boleh kosong!")
            return

        try:
            watch_delay = int(self.entry_watch_delay.get().strip())
            airplane_interval = int(self.entry_airplane_interval.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Jeda dan Airplane Interval harus berupa angka bulat!")
            return

        # Parsing konfigurasi masing-masing device
        self.device_configs = {}
        for dev_id in self.detected_devices:
            if dev_id not in self.device_ui_widgets:
                continue
            
            w = self.device_ui_widgets[dev_id]
            
            # Target VT
            try:
                target_vt = int(w['vt_entry'].get().strip())
                if target_vt <= 0: target_vt = 1
            except ValueError:
                target_vt = 1

            # Clone names
            custom_raw = w['custom_clones_entry'].get().strip()
            clone_names = []
            if custom_raw:
                tokens = [t.strip() for t in custom_raw.split(",") if t.strip()]
                for token in tokens:
                    if "-" in token:
                        parts = token.split("-")
                        if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                            start_r = int(parts[0].strip())
                            end_r = int(parts[1].strip())
                            clone_names.extend([str(i) for i in range(start_r, end_r + 1)])
                        else:
                            clone_names.append(token)
                    else:
                        clone_names.append(token)
            else:
                s_str = w['start_clone_entry'].get().strip()
                e_str = w['end_clone_entry'].get().strip()
                if s_str.isdigit() and e_str.isdigit():
                    s_val = int(s_str)
                    e_val = int(e_str)
                    if e_val < s_val: e_val = s_val
                    clone_names = [str(i) for i in range(s_val, e_val + 1)]
                else:
                    clone_names = [s_str if s_str else "1"]

            if not clone_names:
                clone_names = ["1"]

            # Action Targets
            try:
                target_likes = int(w['like_entry'].get().strip())
            except ValueError:
                target_likes = len(clone_names)

            try:
                target_saves = int(w['save_entry'].get().strip())
            except ValueError:
                target_saves = 0

            try:
                target_shares = int(w['share_entry'].get().strip())
            except ValueError:
                target_shares = 0

            try:
                start_cmt_acc = int(w['start_cmt_acc_entry'].get().strip())
            except ValueError:
                start_cmt_acc = 1

            try:
                target_cmts = int(w['target_cmt_entry'].get().strip())
            except ValueError:
                target_cmts = 0

            raw_cmts = w['comments_text'].get("1.0", tk.END).strip().split("\n")
            comments_list = [c.strip() for c in raw_cmts if c.strip()]

            if target_cmts == 0 and len(comments_list) > 0:
                target_cmts = len(comments_list)

            self.device_configs[dev_id] = {
                'target_vt': target_vt,
                'clone_names': clone_names,
                'target_likes': target_likes,
                'target_saves': target_saves,
                'target_shares': target_shares,
                'start_cmt_acc': start_cmt_acc,
                'target_comments': target_cmts,
                'comments_list': comments_list
            }

        # Buka scrcpy otomatis jika opsi dicentang
        if self.var_auto_mirror.get():
            self.open_all_screens_scrcpy()

        # Reset hitungan global & per-device
        self.global_clone_count = 0
        self.global_liked_videos = 0
        self.global_saved_videos = 0
        self.global_shared_videos = 0
        self.global_comment_count = 0
        self.device_stats = {
            dev: {'clones': 0, 'likes': 0, 'saves': 0, 'shares': 0, 'comments': 0}
            for dev in self.detected_devices
        }
        self.update_stats_ui()

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.logger.log(f"MASTER CONTROL: Starting Multi-Device Farm on {len(self.detected_devices)} devices...")

        self.active_threads = []
        for dev_id in self.detected_devices:
            if dev_id in self.device_configs:
                t = threading.Thread(
                    target=self.device_worker_thread,
                    args=(dev_id, target_account, watch_delay, airplane_interval, self.device_configs[dev_id])
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
    app = TikTokAllInOneLabU2(root)
    root.mainloop()
