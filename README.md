# onlyoffice-fedora-copr-ci

[ONLYOFFICE Desktop Editors](https://github.com/ONLYOFFICE/DesktopEditors) is a
free and open-source office suite with editors for text documents,
spreadsheets, presentations, PDFs and PDF forms, plus a Diagram Viewer. It
works fully offline and is compatible with the Office Open XML formats
(.docx, .xlsx, .pptx).

This repo packages it for Fedora by rewrapping the upstream prebuilt Linux
RPMs (`onlyoffice-desktopeditors.x86_64.rpm` / `.aarch64.rpm`) with a Fedora
spec. Both `x86_64` and `aarch64` are supported, matching upstream's prebuilt
release artifacts. The offline help tree upstream ships separately
(`onlyoffice-desktopeditors-help.noarch.rpm`, ~325 MB, 77 languages) is
repackaged as a noarch `-help` subpackage. A GitHub Actions workflow runs
daily at 12AM UTC to check the latest release from
https://github.com/ONLYOFFICE/DesktopEditors and rebuilds COPR only when a new
version is published. Each downloaded RPM is verified against the sha256
digest GitHub publishes for that release asset before submission.

The COPR project repository is available from: https://copr.fedorainfracloud.org/coprs/anudeepd/onlyoffice

## ⚠️ Conflicts with ONLYOFFICE's own repository

ONLYOFFICE publishes their own yum repository, and it carries **the same
package name**:

```
[onlyoffice]
name=onlyoffice repo
baseurl=http://download.onlyoffice.com/repo/centos/main/noarch/
gpgcheck=1
enabled=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-ONLYOFFICE
```

Their builds carry a high numeric release because their packaging accumulates
build iterations. This repo uses `Release: %{autorelease}`, which for an SRPM
uploaded to COPR resolves to a literal `1` plus the chroot's dist tag — the
release segment is `1` whatever the chroot. rpm compares the release field
segment by segment, numerically first, so theirs outranks this repo's `1`, and
**when both repositories are enabled `dnf` keeps theirs** while this package
looks like it refuses to install.

That is version precedence, not a package defect, and it holds for every
shared version: this repo's release number never outranks theirs. Pick one:

```
sudo dnf install --disablerepo=onlyoffice onlyoffice-desktopeditors
```

or set a higher priority on the COPR repo. Installing theirs is equally valid —
the payload is the same upstream release either way. The two are not
byte-identical, though: the vendor repo rebuilds from its own sources, so its
RPM has a different sha256 from the GitHub release asset this repo packages
(which is also why their published checksums cannot be used to verify this
repo's sources).

The `-help` subpackage collides the same way (`onlyoffice-desktopeditors-help`
also exists in their repo).

## Packaging compliance

This package is distributed via COPR only. It rewraps the upstream prebuilt
binary RPMs, so it is **not eligible for the official Fedora repositories**:
the Fedora Packaging Guidelines require all binaries to be built from source
in the Fedora build system, and this repo intentionally ships the upstream
blob as-is (see `specs/onlyoffice-desktopeditors.spec`).

Everything else follows the guidelines:

- `ExclusiveArch: x86_64 aarch64` — matches upstream's prebuilt artifacts.
  Both upstream RPMs are declared as `Source0`/`Source1` unconditionally so
  the SRPM carries a payload for either arch, and `%ifarch` selects which one
  `%prep` unpacks. (An arch-conditional source would put only the SRPM
  building host's RPM into the SRPM, and COPR builds every enabled chroot
  from that one SRPM — the aarch64 chroot would then fail `%prep` with
  `Bad file: ...aarch64.rpm`.)
- `%build` present (empty — nothing to compile) so rpm's build hooks run.
- `%check` runs `desktop-file-validate` and `appstreamcli validate` on the
  packaged files inside the build.
- `rpmlint` runs in CI on the built RPMs (both arches + the noarch help
  subpackage); every flagged pattern is inherent to rewrapping the
  Qt/CEF blob (private libs under `/opt`, required `$ORIGIN` runpaths,
  unstripped prebuilt binaries, non-setuid `chrome-sandbox` tripping the
  setgroups pattern, CEF's legacy `gethostbyname` call, GUI app without man
  page) and is filtered in `rpmlintrc` with per-filter rationales.
- `%{_bindir}`, `%{_datadir}`, `%{_metainfodir}` macros used in `%files`.
- License provenance: the RPM payload itself ships the license texts
  (`/usr/share/licenses/onlyoffice-desktopeditors/{LICENSE,LICENSE-CC.txt,3DPARTYLICENSE}`),
  so `%files` declares them with `%license` from the packaged files rather
  than fetching anything. `License: AGPL-3.0-only` (SPDX) matches the
  packaged AGPLv3 text — `AGPLv3` in the upstream RPM header is not valid
  SPDX, and the upstream *source* tree's `LICENSE` is the same AGPLv3 text.
- `%global debug_package %{nil}` with an explicit rationale: the prebuilt
  foreign binary cannot produce debuginfo, so the debug package is meaningless
  for a rewrap. Note that this is what *enables* Fedora's ELF-rewriting brp
  hooks rather than skipping them: `%__os_install_post` gates `brp-strip` and
  `brp-strip-comment-note` on `%__debug_package` being undefined, and with
  them active every ELF file in the bundle loses its `.comment` section, i.e.
  the payload stops being byte-identical to the upstream RPM.
  `brp-strip-lto` and `brp-strip-static-archive` are not gated at all. All
  four hooks plus `add-det` are emptied in the spec, so the payload ships
  byte-identical apart from the documented deltas — and the RPM build test
  workflow diffs the packaged tree against the upstream payload to keep it
  that way.
- `brp-mangle-shebangs` is emptied too: `/usr/bin/onlyoffice-desktopeditors`
  is the one shell script in the payload, and the hook rewrites its
  `#!/bin/sh` to `#!/usr/bin/sh` (+4 bytes), breaking byte-identity on its
  own. `/bin/sh` is a symlink to `/usr/bin/sh` on Fedora, so it runs the same.
- The bundle ships its own Qt5/ICU/CEF stack under `/opt/onlyoffice/desktopeditors`
  with SONAMEs (`libQt5Core.so.5`, `libicudata.so.74`, `libcef.so`, …), so the
  generator would advertise them as system providers and require them back.
  `__provides_exclude_from` suppresses the bogus provides across `/opt`, and
  `__requires_exclude` drops exactly the 40 SONAMEs that live in the bundle.
  Generation stays **on** for real system libraries, which is what pulls the
  CEF/NSS (`libnss3.so`, `libnspr4.so`, `libsmime3.so` — declared only by the
  bundled `libcef.so`), GTK, X, XCB, GStreamer, AT-SPI and ALSA stack. Note
  the exclude pattern has no trailing `$`: generated require strings carry an
  arch qualifier (`libcef.so()(64bit)`), so an anchored pattern silently
  never matches.
  Upstream's own RPM declares no library requires at all, which is why an
  unmodified upstream install on a minimal Fedora system fails to start
  (`libnss3.so`, then `libasound.so.2`, …). This package is strictly better
  specified here: `dnf install` resolves the real set.
- Explicit requires are only what no ELF reveals: the font packages the editor
  and its document renderer use by name, `xdg-utils` (shelled out to for
  external links), `libXScrnSaver` and the `xcb-util-*` libs (dlopen'd by
  Qt's xcb platform plugin), `boost-filesystem` and `curl` (dlopen'd by the
  converter binaries in `converter/x2t`), and `hicolor-icon-theme` (owns the
  icon tree this package installs into; upstream omits it). The `libnss3.so`
  trap above is covered by a CI step that resolves every ELF's shared
  libraries with `ldd`, so a regression in the exclude pattern fails the run
  instead of shipping a package that cannot start.
- Two minimal, documented transformations, both in `%prep`:
  1. Upstream bakes build-machine `RPATH`/`RUNPATH` entries into seven files
     (`/opt/qt/5.9.9/gcc_64/lib` and a developer's Qt build tree under
     `/home/oleg/GIT/build_tools/...`), which cannot exist on an end-user
     machine and fail Fedora's `check-rpaths` with `ERROR 0002`. Those
     entries are deleted with `chrpath`. On the `DesktopEditors` launcher the
     RPATH is a list whose `$ORIGIN` entries are load-bearing, so the
     remaining entries are rebuilt rather than the whole RPATH dropped —
     `chrpath -d` there would stop the app from finding its own bundled libs.
     The loop is a no-op if upstream stops baking these in.
  2. Upstream's 134 `/usr/lib/.build-id` symlinks are dropped: they point into
     a debuginfo tree this package does not ship, and Fedora policy has
     packages not own that path (`brp-add-determinism` generates ours, and it
     is disabled because this payload must not be rewritten).
- Upstream ships no AppStream metadata in the RPMs and none in the release
  tree, so this repo ships a curated
  `org.onlyoffice.desktopeditors.metainfo.xml` (RDNS id following Flathub's,
  launchable pointing at the shipped `onlyoffice-desktopeditors.desktop`);
  the upstream desktop file and icons are kept as-is.
- `%postun` in the upstream RPM only deletes stale mime files that the
  payload does not install, and declares no `%post`; nothing is scriptlet-
  dependent here, so no scriptlets are carried over.
- Every downloaded RPM is verified against the sha256 digest GitHub publishes
  for that release asset (same-origin integrity: guards truncated/mismatched
  or substituted downloads; upstream publishes no detached signatures)
  before submission to COPR. A missing digest fails the run rather than
  skipping the check.

### Cost note

The help subpackage is not free. Because the SRPM must carry a payload for
every chroot COPR builds, each CI run downloads all three upstream RPMs —
`x86_64` (380 MB) + `aarch64` (375 MB) + `help` (325 MB) ≈ **1.08 GB** — and
the resulting SRPM is about the same size. Upstream ships help separately for
the same reason; it is repackaged here rather than skipped so that F1 help
works offline.

### Verification status

Verified locally with a full `rpmbuild -ba` plus a `--target aarch64`
cross-build, in a `fedora` container, and by running the packaged application
on a real desktop session (Wayland + Xwayland):

- both arches build with `check-rpaths` enabled; the payload differs from the
  upstream RPM in exactly 7 files (the documented chrpath delta), with
  `/usr/lib/.build-id` the only dropped paths and the curated metainfo the
  only addition;
- `desktop-file-validate` and `appstreamcli validate --no-net` pass;
- `rpmlint -r rpmlintrc` reports **0 errors, 0 warnings** across the three
  built packages;
- `dnf install` of both packages succeeds on declared dependencies alone
  (`--setopt=install_weak_deps=False`), `rpm -V` is clean, and the help tree is
  owned by the `-help` subpackage;
- the packaged payload launched from its `%install` output on a real display:
  the start screen renders, and opening a `.docx` loads the full document
  editor (ribbon, rulers, page count, word count) with the file's text
  displayed. Launch it through the `/usr/bin/onlyoffice-desktopeditors`
  wrapper, which exports `LD_LIBRARY_PATH` for the bundled `/opt` libraries;
  running `opt/onlyoffice/desktopeditors/DesktopEditors` directly fails with
  "could not find or load the Qt platform plugin xcb" — that direct invocation
  is not the supported entry point and the desktop file does not use it.

Note for anyone reproducing this: the launcher is unstable under a bare
headless `Xvfb` (it aborts in GTK style-context init with "Can't create a
GtkStyleContext without a display connection"). The unmodified upstream RPM
fails identically in the same container, so that is an Xvfb limitation rather
than anything about this package. Verify the GUI on a real session.

# Instructions

Enable the COPR repository then install the package.

<pre>
sudo dnf copr enable anudeepd/onlyoffice
sudo dnf install onlyoffice-desktopeditors
</pre>

The offline help is a separate package:

<pre>
sudo dnf install onlyoffice-desktopeditors-help
</pre>

If ONLYOFFICE's own repository is enabled as well, see the conflict section
above before installing.

## Credits

Pattern and workflow structure adapted from
[anudeepd/equibop-fedora-copr-ci](https://github.com/anudeepd/equibop-fedora-copr-ci)
(which itself descends from
[anudeepd/iloader-fedora-copr-ci](https://github.com/anudeepd/iloader-fedora-copr-ci))
— thanks for the clean reference implementation.

<h3> COPR build status </h3>

[![Copr build status](https://copr.fedorainfracloud.org/coprs/anudeepd/onlyoffice/package/onlyoffice-desktopeditors/status_image/last_build.png)](https://copr.fedorainfracloud.org/coprs/anudeepd/onlyoffice/package/onlyoffice-desktopeditors/)

<h3> GitHub action workflow status </h3>

[![onlyoffice Fedora COPR CI](https://github.com/anudeepd/onlyoffice-fedora-copr-ci/actions/workflows/onlyoffice-ci.yml/badge.svg)](https://github.com/anudeepd/onlyoffice-fedora-copr-ci/actions/workflows/onlyoffice-ci.yml)

## Latest version
<a href="https://github.com/ONLYOFFICE/DesktopEditors/releases">
  <img src="https://img.shields.io/github/v/release/ONLYOFFICE/DesktopEditors" alt="ONLYOFFICE Desktop Editors latest release">
</a>
