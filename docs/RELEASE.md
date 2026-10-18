# Publishing a release

## Workflow

1. Push to `main`. GitHub Actions checks the code and builds the packages (a few minutes).
   The full ISO build – install and boot in QEMU (UEFI and BIOS) – runs for `v*` tags or
   on demand via *Actions → Build ISO → Run workflow*; use it for installer or system
   changes. The ISO and the boot screenshots are kept for 30 days under *Artifacts*.
2. Test the ISO in a VM.
3. When everything looks good, push a tag:
   ```bash
   git tag v1.0.0-alpha1 && git push origin v1.0.0-alpha1
   ```
   The pipeline builds again, uploads the ISO and README to SourceForge and creates a
   GitHub pre-release with the checksum and download link.

## Package updates (without a new ISO)

Frametide's own packages (App Store, Control, Develop, design, tuning, store catalog) are
published as a signed APT repository on GitHub Pages:
<https://chopstickguy.github.io/frametide-os/apt/>. Installed systems get new versions through
*Control → Updates* like any other update.

- Every `v*` tag publishes the packages together with the ISO.
- For an update without a new ISO, push an `update-*` tag
  (`git tag update-2026-10-18 && git push origin update-2026-10-18`) or run
  *Actions → Publish packages → Run workflow*.
- The package version is `1.0.<number of commits>`, so it rises with every commit.
- The signing key lives only in the `APT_SIGNING_KEY` secret. The public key is shipped in
  `frametide-base` (`/usr/share/keyrings/frametide-archive-keyring.gpg`) and in
  `docs/frametide-archive-key.asc`. Fingerprint: `9317 E2F8 7CFB 7AD8 DA65  E039 7761 6072 7C44 889C`.

Systems installed from 1.0.0-alpha1 don't know the repository yet. Enable it once:

```bash
wget -O /tmp/frametide-base.deb https://chopstickguy.github.io/frametide-os/frametide-base.deb
sudo apt install /tmp/frametide-base.deb
sudo apt update && sudo apt full-upgrade
```

Changes that only touch documentation (`*.md`, `docs/`) do not trigger a new ISO build.

## Why SourceForge?

GitHub releases allow at most **2 GB per file**, and our ISO is bigger. SourceForge is free,
has a worldwide mirror network and is used by many distributions, such as Manjaro,
MX Linux and Nobara.

## SourceForge setup (one time, already done)

- Project: <https://sourceforge.net/projects/frametide-os/> (admin: `chopstickguy`)
- GitHub secrets: `SF_USER`, `SF_PROJECT`, `SF_SSH_KEY`
- The public key for `SF_SSH_KEY` must be registered at
  <https://sourceforge.net/auth/shell_services>.

## SourceForge project page

The texts for the project page are in [SOURCEFORGE.md](SOURCEFORGE.md). They have to be
edited by hand under *Admin → General* on SourceForge, because there is no public API for
this.
