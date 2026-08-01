# Manual Test Checklist

Gunakan checklist ini setelah perubahan gameplay, save, shop, boss, atau scene transition.

## Startup Dan Menu

- Jalankan `python assets/main.py` tanpa crash.
- Opening bisa di-skip dengan klik atau keyboard.
- Menu utama tampil dengan tombol `GAME BARU`, `LANJUTKAN`, `CARA MAIN`, `PENGATURAN`, `DATA SAVE`, dan `KELUAR`.
- `LANJUTKAN` disabled saat belum ada save.
- `DATA SAVE` terbuka dan bisa ditutup dengan tombol/klik.

## New Game

- Klik `GAME BARU` masuk gameplay level 1.
- Tutorial muncul jika `tutorial_seen` belum true.
- Story intro bisa di-skip.
- Player bisa bergerak, lompat/glide, dan menembak.
- HUD menampilkan nyawa, HP, skor, koin, level, weapon, progress boss, dan status sound.

## Save Dan Continue

- Tekan `F5` saat bermain, lalu kembali ke menu.
- `LANJUTKAN` aktif setelah save.
- Continue memuat level, koin, upgrade shop, cosmetic, dan weapon permanen yang tersimpan.
- `total_plays` bertambah saat memulai New Game atau Continue.

## Shop

- Tekan `B` atau klik `TOKO [B]` saat bermain.
- Upgrade HP, Speed, dan Damage mengurangi koin dan langsung berefek.
- Tab skin bisa beli/pakai skin.
- Tab senjata bisa beli skin senjata dan senjata toko.
- Railgun, Nova Cannon, dan Pulse Rifle mengeluarkan SFX saat ditembak.
- Tutup shop dengan `ESC` atau klik luar panel.

## Boss Dan Level Clear

- Mendekati area boss memicu dialog boss.
- Dialog memakai dialog spesifik level jika tersedia.
- Boss intro muncul setelah dialog selesai.
- Boss bisa dikalahkan dan memicu level clear.
- Setelah level clear, game auto-save dan lanjut ke level berikutnya.
- Level terakhir masuk ending setelah boss final dikalahkan.

## Death Dan Game Over

- Saat HP habis, scene `KAMU KALAH` tampil.
- Jika nyawa masih ada, `R` atau klik respawn dari posisi aman.
- Jika nyawa habis, `R` atau klik masuk game over lalu kembali ke menu.

## Settings

- Menu settings bisa dibuka dari menu utama dan pause.
- Slider SFX/BGM mengubah volume.
- Mute toggle bekerja dan tersimpan.
- Fullscreen toggle bekerja dan tersimpan.
- Language toggle mengganti Indonesia/English dan pilihan tersimpan.
- Setelah ganti bahasa, menu, HUD, shop, pause, death/game over, opening/tutorial, story level, dan boss intro ikut berubah bahasa.
- `RESET AWAL` mengembalikan setting default.

## Regression Cepat

- Tidak ada crash saat berpindah `menu -> playing -> paused -> menu`.
- Tidak ada crash saat shop dibuka/ditutup berulang.
- Tidak ada crash saat fullscreen toggle dari menu/settings/gameplay.
- Save file rusak atau tidak valid tidak menghentikan game; game kembali ke default save.
