# Frametide OS compared (October 2026)

<sub>🇩🇪 [Deutsche Version](VERGLEICH.md)</sub>

## Overview

| | **Frametide 1.0** | CachyOS | SteamOS 3.8 | Bazzite | Nobara 44 |
|---|---|---|---|---|---|
| Base | Ubuntu 26.04 LTS | Arch (rolling) | Arch (Valve) | Fedora Atomic | Fedora |
| Updates / stability | LTS until 2031 | rolling | tested by Valve | atomic | semi-rolling |
| Kernel | Ubuntu HWE 7.0, signed | custom, BORE scheduler | Valve kernel | custom (HDR, handhelds) | patched |
| Packages for modern CPUs | optional x86-64-v3 | v3/v4/Zen4 + PGO/LTO | – | – | – |
| Proton variant | Valve Proton (+ ProtonPlus in the store) | **proton-cachyos** | Valve Proton | Valve/GE | GE-Proton (by the Nobara author) |
| Console mode (Big Picture) | – | handheld edition | **core feature** | yes | yes (HTPC edition) |
| Rollback / snapshots | **missing** | btrfs + Snapper | A/B image | **90 days, automatic after 3 failed boots** | – |
| Automatic drivers | yes (incl. 32-bit, hybrid) | chwd | fixed hardware | images | unified ISO |
| **Secure Boot without fiddling** | **yes (NVIDIA without MOK)** | no (manual) | no | with key enrollment | limited |
| RGB + fans in one GUI | **yes (Frametide Center)** | no | no | OpenRGB via command | no |
| Office/creative suite pre-installed | **ArtCraft** | no | no | no | no |
| Game check (ProtonDB + anti-cheat) | **yes** | no | no | no | no |
| Move-from-Windows assistant | **yes** | no | no | no | no |
| Own store | yes (curated + Flathub + containers) | Shelly | Discover | Bazaar | Discover |

In recent Phoronix tests, CachyOS is only **slightly** ahead of Ubuntu 26.04, and in some
workloads Ubuntu wins. Raw speed alone is therefore not what sets a distribution apart.
Frametide focuses on making the switch from Windows painless.

## What we are adopting next

| Priority | Idea (inspired by) | Benefit | Effort |
|---|---|---|---|
| 1 | **Snapshots before every update + rollback from the boot menu** (CachyOS, Bazzite) | A broken update can be undone with one click | medium |
| 2 | **Frametide Game Mode**: Steam Big Picture in Gamescope as its own login session (SteamOS, Bazzite) | Console experience on the TV, HDR in games | medium |
| 3 | **Keep Proton-GE / proton-cachyos up to date automatically** (CachyOS, Nobara) | More games work right away | small |
| 4 | **Kernel picker in the Center**: HWE / HWE-edge, later a custom gaming kernel (CachyOS) | Newest hardware without the terminal | small |
| 5 | **Own APT repository with x86-64-v3 builds and newer Mesa** (CachyOS) | Measurably faster on CPU-heavy work | large |
| 6 | **sched_ext schedulers** (scx_lavd/bpfland) as an option (CachyOS) | Less stutter under background load | medium |
| 7 | **Handheld edition** (Bazzite, SteamOS) | Legion Go, ROG Ally, MSI Claw | large |
| 8 | **Automatic rollback after 3 failed boots** (Bazzite) | No black screen after an update | medium (after #1) |

## Already unique to Frametide

1. **Game check:** Checks your Steam library and any game by name for ProtonDB ratings and
   anti-cheat blocks.
2. **Move from Windows:** Copies files, bookmarks, exported Wi-Fi profiles and Steam games.
3. **Frametide Bench:** Makes every optimization measurable and comparable.
4. **One-click dev environments:** Distrobox containers, e.g. for AI with CUDA/ROCm.
5. **One control center for hardware:** Drivers, RGB and fans together, which on Windows
   takes iCUE, Armoury Crate and Afterburner.

Next idea on the list: **one-click profiles** such as "Quiet / Balanced / Maximum". Each
profile switches fan curve, RGB, power profile and GPU level together.
