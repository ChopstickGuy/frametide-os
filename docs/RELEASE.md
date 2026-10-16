# Publishing a release

## Workflow

1. Push to `main`. GitHub Actions checks the code, builds the ISO and boots it in QEMU
   (UEFI and BIOS). The ISO and the boot screenshots are kept for 30 days under
   *Actions → Build ISO → Artifacts*.
2. Test the ISO in a VM.
3. When everything looks good, push a tag:
   ```bash
   git tag v1.0.0-alpha1 && git push origin v1.0.0-alpha1
   ```
   The pipeline builds again, uploads the ISO and README to SourceForge and creates a
   GitHub pre-release with the checksum and download link.

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
