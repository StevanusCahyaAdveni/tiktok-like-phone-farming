import sys

with open('d:/Belajar/BOT-PHONE-FARMING-LEGAL/tiktok_auto_lab_cloneApp.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # lines 178 to 228 (0-indexed 177 to 227)
    if 177 <= i <= 227:
        if i == 177:
            new_code = """            # 2. Verifikasi bahwa aplikasi TikTok Clone benar-benar terbuka
            self.logger.log(f"[{device_id}] Verifying Cloned TikTok launch...")
            tiktok_opened = False
            for _ in range(7):
                # Deteksi elemen UI TikTok karena package Name bisa tetap Clone App
                if d(textMatches="(?i)beranda|jelajahi|profil").exists(timeout=0) or d(descriptionMatches="(?i)beranda|jelajahi|profil").exists(timeout=0):
                    tiktok_opened = True
                    break
                time.sleep(1)
                
            if not tiktok_opened:
                self.logger.log(f"[{device_id}] WARNING: Clone #{clone_num} didn't launch on first click, retrying...")
                d.click(click_x, click_y)
                time.sleep(5)
            
            # 3. Navigasi ke Video Target via Kolom Pencarian (Jelajahi)
            self.logger.log(f"[{device_id}] Opening TikTok Search bar (Jelajahi)...")
            
            # Abaikan Auto-Popup dari Clipboard, karena pop-up bisa melempar ke TikTok Lite asli (luar clone)
            if d(textMatches="(?i)jelajahi|temukan").exists(timeout=2):
                d(textMatches="(?i)jelajahi|temukan").click()
                time.sleep(2)
            else:
                self.logger.log(f"[{device_id}] 'Jelajahi' not found, using coordinate fallback...")
                d.click(0.3, 0.95) # Koordinat menu Jelajahi di TikTok Lite (bawah tengah-kiri)
                time.sleep(2)
                
            # Klik kolom pencarian (search box) di halaman Jelajahi
            if d(descriptionMatches="(?i).*cari.*|.*search.*").exists(timeout=1.5):
                d(descriptionMatches="(?i).*cari.*|.*search.*").click()
            else:
                d.click(0.5, 0.07) # Koordinat bar pencarian atas tengah
            time.sleep(2.5)
            
            # Masukkan URL dan Enter
            d.set_clipboard(target_url)
            d.send_keys(target_url)
            time.sleep(1)
            d.press("enter")
            self.logger.log(f"[{device_id}] Searching for target URL...")
            time.sleep(3.5)
            
            # Klik Video Pertama pada Hasil Pencarian
            self.logger.log(f"[{device_id}] Opening top video search result...")
            d.click(0.5, 0.35)
"""
            new_lines.append(new_code)
    else:
        new_lines.append(line)

with open('d:/Belajar/BOT-PHONE-FARMING-LEGAL/tiktok_auto_lab_cloneApp.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Done modifying cloneApp script!')
