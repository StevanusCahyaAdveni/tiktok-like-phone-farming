## PRODUCT REQUIREMENT DOCUMENT (PRD)

### 1. Project Overview & Objective

* **Project Name:** Modular TikTok Multi-Device & Multi-App Automation Lab
* **Objective:** Membangun aplikasi *desktop* berbasis Python untuk mengotomatisasi aksi "Like" pada video TikTok secara simultan di banyak perangkat Android fisik (*Multi-Device*). Sistem harus mampu menangani beberapa aplikasi TikTok hasil kloning (*Multi-App*) dan melakukan perulangan akun (*Multi-Account*) di dalam masing-masing aplikasi tersebut secara independen menggunakan protokol ADB dan pengenalan elemen berbasis XML.

### 2. System Architecture & Core Components

Sistem ini dirancang menggunakan arsitektur *Master-Worker* yang terdistribusi secara lokal:

* **Master (Laptop):** Bertindak sebagai *orchestrator* yang mengelola GUI, membaca *payload* input pengguna, memparse struktur UI XML, dan mendistribusikan instruksi melalui *Multithreading*.
* **Workers (Android Devices):** Bertindak sebagai perangkat eksekusi pasif yang menerima perintah *low-level* ADB (`input tap`, `monkey launcher`, `uiautomator dump`).

### 3. Functional Requirements

#### A. GUI Module (Tkinter)

* **Input Fields:**
* `Target URL / Username`: String input untuk target video.
* `Execution Count per App (N)`: Integer input untuk jumlah akun yang akan di-*looping* di dalam satu aplikasi.


* **Dynamic Configuration Table/List:**
* Kolom untuk mendaftarkan daftar *Package Names* aplikasi TikTok (Contoh: `com.zhiliaoapp.musically`, `com.zhiliaoapp.musically.clone1`).


* **Control Buttons:** `Start Automation` dan `Emergency Stop`.
* **Asynchronous Log Console:** Jendela *text area* yang diperbarui secara *real-time* dari berbagai *thread* tanpa membuat GUI *freeze/crash* (menggunakan `queue.Queue` atau *thread-safe logging*).

#### B. Device Discovery Module

* Menggunakan `subprocess` untuk mengeksekusi `adb devices`.
* Melakukan *string parsing* untuk menyaring *device ID* yang berstatus `device` dan mengabaikan perangkat yang `unauthorized` atau `offline`.

#### C. Orchestration & Execution Module (The Nested Loop)

Setiap perangkat berjalan di atas `threading.Thread` terpisah. Di dalam setiap *thread* perangkat, sistem wajib mengeksekusi algoritma *Nested Loop* (Perulangan Bersarang) berikut:

```text
FOR EACH package_name IN package_list:
    FOR i = 1 TO execution_count (N):
        1. Jalankan aplikasi berdasarkan package_name saat ini.
        2. Navigasi ke Target URL.
        3. Terapkan Jeda Acak (Anti-Bot Latency).
        4. Jalankan UI Automator Dump -> Ambil XML secara lokal.
        5. Parse XML -> Ekstrak koordinat Tombol "Like".
        6. Eksekusi ADB Input Tap pada target koordinat.
        7. JIKA i < execution_count:
             - Jalankan Sub-rutin Ganti Akun (Pindah ke Akun i+1).
             - Jeda untuk loading pergantian sesi.

```

#### D. XML Parser & Target Coordinate Engine

* Memanfaatkan `xml.etree.ElementTree` untuk membaca file `.xml` layout yang ditarik dari HP.
* **Kriteria Pencarian Elemen Tombol Like:** Mencari *node* yang memiliki atribut `content-desc="Like"` atau `resource-id="com.zhiliaoapp.musically:id/like_button"` (disesuaikan dinamis berdasarkan nama paket).
* **Regex/String Bound Extractor:** Mengubah string koordinat bawaan Android `[x1,y1][x2,y2]` menjadi nilai integer, lalu menghitung titik tengahnya:

$$X_{center} = \frac{x1 + x2}{2}$$


$$Y_{center} = \frac{y1 + y2}{2}$$



#### E. Robustness & Exception Handling

* **Isolation Constraint:** Kegagalan pada satu perangkat (misal kabel terlepas) atau kegagalan pada satu aplikasi kloning (misal *force close*) **tidak boleh** menghentikan *thread* perangkat lain atau iterasi aplikasi selanjutnya.
* **Garbage Collection:** File XML *layout temporary* yang ditarik ke laptop harus otomatis dihapus setelah koordinat ditemukan agar tidak membebani penyimpanan lokal.

---
