import os
import time
import random
import queue
import threading
import subprocess
import uiautomator2 as u2
import tkinter as tk
from tkinter import messagebox, scrolledtext

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
        self.root.geometry("700x570")
        self.is_running = False
        self.active_threads = []

        self.setup_gui()
        self.logger = ThreadSafeConsoleLogger(self.log_text)
        self.detect_devices_startup()

    def setup_gui(self):
        # Frame Input URL
        frame_url = tk.LabelFrame(self.root, text=" 1. Target Configuration ", padx=10, pady=5)
        frame_url.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_url, text="Urutan Grup di Inbox (Baris ke berapa, misal: 3):").pack(anchor="w")
        self.entry_url = tk.Entry(frame_url, width=80)
        self.entry_url.pack(fill="x", pady=2)
        self.entry_url.insert(0, "3")

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

        # Console Log Window
        frame_log = tk.LabelFrame(self.root, text=" 3. Execution Logs Console ", padx=10, pady=5)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame_log, bg="black", fg="#00ff00", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

    def detect_devices_startup(self):
        """Mendeteksi semua HP yang terhubung via ADB."""
        try:
            result = subprocess.run(["adb", "devices"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout
        except Exception:
            output = ""

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

    def device_worker_thread(self, device_id, target_url, total_clones, start_index):
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
                
                # Grid Slot #0 diloncati karena berisi Folder Tools.
                # Clone #1 menempati Grid Slot #1 (Baris 0, Kolom 1)
                grid_slot = clone_num
                row = grid_slot // 4
                col = grid_slot % 4
                
                target_page = row // 4
                row_in_page = row % 4
                
                click_x = col_x_ratios[col]
                click_y = row_y_ratios[row_in_page]
                self.logger.log(f"[{device_id}] [Clone #{clone_num}/{total_clones}] Launching Clone App...")
                d.app_start("com.pengyou.cloneapp")
                # Jeda 4.5 detik untuk memastikan SplashActivity / Iklan Clone App selesai memuat
                smart_sleep(4.5)
                
                # Scroll halaman jika clone berada di halaman bawah
                if target_page > 0:
                    self.logger.log(f"[{device_id}] Scrolling grid down {target_page} page(s) to reach Clone #{clone_num}...")
                    for p in range(target_page):
                        d.swipe_ext("up", scale=0.52)
                        smart_sleep(1.2)
                
                # 1. Klik ikon aplikasi TikTok Clone (Klik presisi & re-click jika perlu)
                self.logger.log(f"[{device_id}] Clicking Clone Icon #{clone_num} at Grid (Row {row+1}, Col {col+1})...")
                d.click(click_x, click_y)
                smart_sleep(0.3)
                d.click(click_x, click_y)
                
                # 2. Verifikasi bahwa aplikasi TikTok Clone benar-benar terbuka
                self.logger.log(f"[{device_id}] Verifying Cloned TikTok launch...")
                tiktok_opened = False
                for _ in range(7):
                    # Deteksi elemen UI TikTok karena package Name bisa tetap Clone App
                    if d(textMatches="(?i)beranda|jelajahi|profil").exists(timeout=0) or d(descriptionMatches="(?i)beranda|jelajahi|profil").exists(timeout=0):
                        tiktok_opened = True
                        break
                    smart_sleep(1)
                    
                if not tiktok_opened:
                    self.logger.log(f"[{device_id}] WARNING: Clone #{clone_num} didn't launch on first click, retrying...")
                    d.click(click_x, click_y)
                    smart_sleep(5)
                
                # 3. Navigasi ke Video Target via Inbox (Group Chat Method)
                try:
                    chat_index = int(target_url)
                except:
                    chat_index = 3 # Default baris ke-3
                    
                self.logger.log(f"[{device_id}] Opening Inbox (Kotak Masuk)...")
                
                # Buka tab Kotak Masuk
                if d(textContains="Kotak Masuk").exists(timeout=2) or d(textMatches="(?i)kotak masuk|inbox").exists(timeout=0):
                    try:
                        d(textContains="Kotak Masuk").click()
                    except Exception:
                        d(textMatches="(?i)kotak masuk|inbox").click()
                    smart_sleep(3)
                else:
                    self.logger.log(f"[{device_id}] 'Kotak Masuk' text not found, using coordinate fallback...")
                    d.click(0.7, 0.95) # Koordinat menu Kotak Masuk di TikTok Lite (bawah kanan-tengah)
                    smart_sleep(3)
                    
                # Klik Grup berdasarkan urutan baris
                # Jarak antar chat di TikTok Lite adalah sekitar 0.083 dari tinggi layar.
                # Baris ke-1 (Aktivitas) ada di Y=0.133
                click_y = 0.133 + (chat_index - 1) * 0.083
                
                self.logger.log(f"[{device_id}] Clicking Chat Row #{chat_index} (Coordinate Y={click_y:.3f})...")
                smart_sleep(1.5) # Jeda penstabilan sebelum klik grup
                d.click(0.5, click_y)
                
                self.logger.log(f"[{device_id}] Waiting 5s for chat room to fully render...")
                smart_sleep(5) # Jeda lebih lama menunggu ruang chat terbuka sempurna
                
                # Klik Pesan Terakhir (Video Link)
                self.logger.log(f"[{device_id}] Clicking the latest video message in chat...")
                smart_sleep(1.5) # Jeda penstabilan sebelum klik video
                
                # Lakukan SATU kali klik presisi
                d.click(0.5, 0.78)
                smart_sleep(1.5) # Jeda sesudah klik
                delay_time = random.randint(7, 9)
                self.logger.log(f"[{device_id}] Waiting {delay_time}s for video rendering...")
                smart_sleep(delay_time)

                # 4. Eksekusi Double Click di Tengah Layar (Native Gesture u2)
                self.logger.log(f"[{device_id}] Dispatching Native Double-Tap to screen center (0.5, 0.5)...")
                d.double_click(0.5, 0.5, duration=0.04)
                self.logger.log(f"[{device_id}] Command Executed: Native Double-Tap Dispatched.")

                # 5. Tutup Paksa Aplikasi untuk Melegakan RAM (Clear Memory)
                self.logger.log(f"[{device_id}] Clearing RAM: Force-stopping all Clone App processes...")
                d.app_stop("com.pengyou.cloneapp")
                smart_sleep(2)

                is_last = (clone_num == total_clones)
                if not is_last and self.is_running:
                    # Buka kembali aplikasi Clone App
                    self.logger.log(f"[{device_id}] Reopening Clone App Matrix for the next account...")
                    d.app_start("com.pengyou.cloneapp")
                    smart_sleep(5) # Tunggu grid muncul sempurna

                    # 6. Sub-rutin Rotasi IP (Airplane Mode)
                    self.logger.log(f"[{device_id}] Dispatching IP Rotation (Airplane Mode)...")
                    
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

    def start_automation(self):
        devices = self.detect_devices_startup()
        if not devices:
            messagebox.showerror("Error", "No connected Android devices detected via ADB!")
            return

        target_url = self.entry_url.get().strip()
        try:
            total_clones = int(self.entry_clones.get().strip())
            start_index = int(self.entry_start_idx.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Total Clones & Start Index must be clean integers!")
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.logger.log("MASTER CONTROL: Clone App Matrix Orchestration deployed. Spawning parallel threads...")

        self.active_threads = []
        for device_id in devices:
            t = threading.Thread(
                target=self.device_worker_thread, 
                args=(device_id, target_url, total_clones, start_index)
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
