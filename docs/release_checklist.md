# Release Checklist

Gunakan checklist ini sebelum membagikan build Pixel Glide.

## Pre-Release

- Jalankan syntax check: `python -m py_compile assets/main.py assets/ui_config.py`.
- Jalankan game dari source: `python assets/main.py`.
- Selesaikan checklist manual di `docs/manual_test_checklist.md` minimal untuk startup, new game, save/continue, shop, boss spawn, dan settings.
- Test toggle bahasa Indonesia/English dari Settings dan pastikan pilihan tersimpan setelah restart.
- Pastikan `pixelglide_save.json` tidak ikut paket release.
- Pastikan `venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, dan file `.log` tidak ikut paket release.
- Pastikan file penting ikut release: `assets/main.py`, `assets/ui_config.py`, `requirements.txt`, dan `README.md`.
- Test di folder bersih tanpa save lama agar first-run player sama seperti user baru.

## Source Zip Release

- Jalankan: `python scripts/make_release.py`.
- Ambil zip dari folder `dist/`.
- Extract zip ke folder sementara.
- Jalankan install dependency di folder hasil extract: `pip install -r requirements.txt`.
- Jalankan game dari folder hasil extract: `python assets/main.py`.

## EXE Release Opsional

Jika nanti ingin build `.exe`, gunakan hasil source yang sudah bersih sebagai basis. Setelah `.exe` dibuat, test di folder baru tanpa `pixelglide_save.json`.

## Final Smoke Test

- Game bisa start dari folder release.
- Menu utama tampil.
- New Game bisa masuk level 1.
- Save bisa dibuat dan Continue aktif.
- Shop bisa dibuka dan ditutup.
- Settings bisa dibuka dan ditutup.
- Bahasa bisa diganti antara Indonesia dan English.
- Game bisa quit tanpa error.
