<<<<<<< HEAD
# Pixel-Glide
# Pixel-Glide
# Pixel-Glide
=======
# Pixel Glide

Pixel Glide adalah game platformer sci-fi berbasis Pygame. Pemain mengendalikan unit G7 melewati level procedural, mengumpulkan koin, membuka upgrade/cosmetic, dan mengalahkan boss CORE-X.

## Fitur

- 13 stage termasuk bonus level.
- 10 boss dengan ability dan dialog.
- Sistem save/load progress.
- Shop untuk upgrade, skin, weapon skin, dan senjata toko.
- Audio procedural untuk SFX dan BGM.
- Tutorial, story intro, settings, fullscreen, dan pause menu.
- Pilihan bahasa Indonesia dan English dari menu Settings.

## Cara Menjalankan

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python assets/main.py
```

## Kontrol

- `A/D` atau panah kiri/kanan: bergerak.
- `SPACE/W/UP`: lompat, glide, atau thrust di zona terbang.
- Klik kiri: tembak.
- `Q` atau scroll mouse: ganti senjata.
- `E`: tampil/sembunyikan senjata.
- `B`: buka toko saat bermain.
- `F5`: save progress.
- `ESC`: pause/kembali.
- `M`: mute.
- `[` dan `]`: volume turun/naik.
- `F11`: fullscreen/windowed.

## Bahasa

Bahasa default adalah Indonesia. Buka `PENGATURAN` / `SETTINGS`, lalu klik `Bahasa` / `Language` untuk mengganti antara Indonesia dan English. Pilihan bahasa tersimpan di `pixelglide_save.json`.

## Data Save

Save tersimpan di `pixelglide_save.json` pada root project. File ini diabaikan Git lewat `.gitignore`.

## Checklist Rilis Singkat

Sebelum menambah konten besar, jalankan checklist manual di `docs/manual_test_checklist.md` untuk memastikan flow utama tidak rusak.

## Membuat Paket Release

Jalankan syntax check dan script release:

```bash
python -m py_compile assets/main.py assets/ui_config.py
python scripts/make_release.py
```

Hasil release source tersedia di `dist/PixelGlide-source/` dan `dist/PixelGlide-source.zip`.

Sebelum membagikan build, ikuti checklist di `docs/release_checklist.md`.
>>>>>>> 14b738e (Fix runtime loop, render dispatch, and menu BGM)
