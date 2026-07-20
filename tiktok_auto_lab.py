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

class TikTokAutomationLabU2:
    def __init__(self, root):
        self.root = root
        self.root.title("TikTok Multi-Device Lab v2.0 - UIAutomator2 Engine")
        self.root.geometry("700x550")
        self.is_running = False
        self.active_threads = []

        self.setup_gui()
        self.logger = ThreadSafeConsoleLogger(self.log_text)
        self.detect_devices_startup()

    def setup_gui(self):
        # Frame Input URL
        frame_url = tk.LabelFrame(self.root, text=" 1. Target Configuration ", padx=10, pady=5)
        frame_url.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_url, text="TikTok Video/VT URL:").pack(anchor="w")
        self.entry_url = tk.Entry(frame_url, width=80)
        self.entry_url.pack(fill="x", pady=2)
        self.entry_url.insert(0, "https://www.tiktok.com/@username/video/1234567890")

        # Frame Loop & App Configurations
        frame_config = tk.LabelFrame(self.root, text=" 2. Loop & Package Configuration ", padx=10, pady=5)
        frame_config.pack(fill="x", padx=10, pady=5)

        # Jumlah Akun
        frame_loop = tk.Frame(frame_config)
        frame_loop.pack(side="left", fill="y", padx=5)
        tk.Label(frame_loop, text="Accounts per App (N):").pack(anchor="w")
        self.entry_loops = tk.Entry(frame_loop, width=15)
        self.entry_loops.pack(anchor="w", pady=2)
        self.entry_loops.insert(0, "3")

        # Daftar Package
        frame_packages = tk.Frame(frame_config)
        frame_packages.pack(side="right", fill="both", expand=True, padx=5)
        tk.Label(frame_packages, text="Android Package Names (One per line):").pack(anchor="w")
        self.text_packages = scrolledtext.ScrolledText(frame_packages, height=4, width=45)
        self.text_packages.pack(fill="both", expand=True, pady=2)
        self.text_packages.insert(tk.END, "com.ss.android.ugc.trill\ncom.zhiliaoapp.musically")

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
        except Exception as e:
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

    def device_worker_thread(self, device_id, target_url, packages, execution_count):
        """Worker Thread berbasis uiautomator2."""
        self.logger.log(f"[{device_id}] Connecting via UIAutomator2 driver...")
        
        try:
            # Hubungkan uiautomator2 ke HP spesifik berdasarkan serial ID
            d = u2.connect(device_id)
            self.logger.log(f"[{device_id}] UIAutomator2 Connected. Screen Resolution: {d.window_size()}")
        except Exception as e:
            self.logger.log(f"[{device_id}] CRITICAL ERROR: Connection failed - {str(e)}")
            return

        for package in packages:
            if not self.is_running: break
            package = package.strip()
            if not package: continue

            for i in range(1, execution_count + 1):
                if not self.is_running: break
                self.logger.log(f"[{device_id}] Target App: {package} | Account Loop {i} of {execution_count}")

                # 1. Force stop aplikasi via u2
                self.logger.log(f"[{device_id}] Resetting application instance...")
                d.app_stop(package)
                time.sleep(1.5)
                
                # 2. Buka Deep Link langsung menggunakan shell u2
                self.logger.log(f"[{device_id}] Dispatching Deep Link Activity...")
                d.shell(f"am start -a android.intent.action.VIEW -d '{target_url}' {package}")
                
                # Jeda 10-12 detik untuk loading video
                delay_time = random.randint(10, 12)
                self.logger.log(f"[{device_id}] Waiting {delay_time}s for UI rendering...")
                time.sleep(delay_time)

                # 3. Eksekusi Double Click di Tengah Layar (Native Gesture u2)
                self.logger.log(f"[{device_id}] Dispatching Native Double-Tap to screen center (0.5, 0.5)...")
                
                # d.double_click mendukung koordinat rasio float (0.5 = 50% layar)
                # duration=0.04 ms membuat ketukan sangat cepat & presisi untuk MIUI/HyperOS
                d.double_click(0.5, 0.5, duration=0.04)
                
                self.logger.log(f"[{device_id}] Command Executed: Native Double-Tap Dispatched.")

                # 4. Sub-rutin Rotasi IP (Airplane Mode) dan Ganti Akun
                is_last_overall = (packages.index(package) == len(packages) - 1) and (i == execution_count)
                if not is_last_overall and self.is_running:
                    self.logger.log(f"[{device_id}] Dispatching IP Rotation (Airplane Mode)...")
                    
                    # Hidupkan mode pesawat & Matikan data via u2 shell
                    d.shell("cmd connectivity airplane-mode enable")
                    d.shell("svc data disable")
                    self.logger.log(f"[{device_id}] IP Reset (Airplane/Data OFF). Menunggu 5 detik...")
                    time.sleep(5)
                    
                    # Matikan mode pesawat & Hidupkan data via u2 shell
                    d.shell("cmd connectivity airplane-mode disable")
                    d.shell("svc data enable")
                    self.logger.log(f"[{device_id}] IP Reset (Airplane/Data ON). Menunggu 3 detik untuk koneksi ulang...")
                    time.sleep(3)

        self.logger.log(f"[{device_id}] Worker Thread finished execution lifecycle.")

    def start_automation(self):
        devices = self.detect_devices_startup()
        if not devices:
            messagebox.showerror("Error", "No connected Android devices detected via ADB!")
            return

        target_url = self.entry_url.get().strip()
        try:
            execution_count = int(self.entry_loops.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Execution count must be a clean integer!")
            return

        packages = [p.strip() for p in self.text_packages.get("1.0", tk.END).splitlines() if p.strip()]
        if not packages:
            messagebox.showerror("Error", "Please input at least one Android Package Name!")
            return

        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_refresh.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        self.logger.log("MASTER CONTROL: Orchestration system deployed. Spawning parallel threads...")

        self.active_threads = []
        for device_id in devices:
            t = threading.Thread(
                target=self.device_worker_thread, 
                args=(device_id, target_url, packages, execution_count)
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
    app = TikTokAutomationLabU2(root)
    root.mainloop()