# Enderchest

A personal inventory and maintenance app for your laptop. Photograph your things; Enderchest reads what it can (name, size, model number, expiry date), asks you to confirm it, gives each item a QR label, and helps with "do I already own this?", "this is about to expire or needs an inspection" and "keep my stuff organised". Inspired by SAP PM and QM ideas at personal scale; it is not SAP software.

Everything runs on your own computer. It works with no internet and no account.

## What you need
- Windows 10 or 11 with Docker Desktop installed and running (https://www.docker.com/products/docker-desktop/).
- A few GB of free disk space, and internet for the first build (it downloads the base images and a text-reading model).
- Chrome or Edge. A webcam (or a phone used as a webcam) for the camera features.

## Install
1. Unzip this folder on any drive, in any folder you will keep, for example `C:\Enderchest` or `E:\Apps\Enderchest`.
2. Double-click `build.bat`. The first build takes several minutes. It creates your data volume and a backup folder (`%USERPROFILE%\Enderchest-Backups`) and writes a small `.env` settings file. It never deletes anything and is safe to run again.
3. Double-click `run.bat`. Your browser opens Enderchest at http://127.0.0.1:8470 and asks your name on the first run.

## Every day
- Start: `run.bat`. Stop: `stop.bat`. Enderchest is only reachable from this computer.
- Reminders and notifications show while an Enderchest tab is open.
- When the camera page asks, allow the browser to use your camera.

## Your data
- Your inventory lives in a Docker volume named `enderchest_data`. Photos and the database stay on this computer.
- Enderchest makes backups by itself into `%USERPROFILE%\Enderchest-Backups`. `backup.bat` makes one more right now.
- `restore.bat` lists your backups and restores the one you pick. Your current data is copied to a safety backup first.
- To update, unzip the new version into a new folder and run `build.bat`, then `run.bat`. Your data stays in the volume; Enderchest backs it up before it changes its database.
- Never delete the `enderchest_data` volume, never run `docker compose down -v` or `docker volume prune`, and never use Docker Desktop's "Clean / Purge data" or "Reset to factory defaults". Each of these deletes your inventory.

## Optional: Gemini
Reading photos and the Assistant can use Google Gemini with your own API key: Settings, then Gemini. It is off until you add a key and switch it on, and the screen says exactly what leaves your computer. Without a key everything else works.

## If something goes wrong
- `build.bat` and `run.bat` save everything they print to a `.txt` file in the `logs` folder, and the window stays open on a problem. Send that file to whoever is helping you. Docker Desktop must use Linux containers and include Compose 2.17 or newer.
- "Port 8470 is already in use": close the other program, or change `ENDERCHEST_PORT` in the `.env` file, then run `run.bat` again.
- "Docker is not running": start Docker Desktop, wait until it says the engine is running, then try again.
- If Enderchest starts but shows a problem page, your data has not been changed; the page says what is wrong and what to do.
