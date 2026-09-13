# Prebuilt foreign binary: no build-id or debuginfo can be produced, so the
# debug package is disabled. The payload ships as-is from the release RPM.
%global debug_package %{nil}

# NOTE (verified by local rpmbuild of 9.4.0): %%global debug_package %%{nil}
# is what makes the default ELF-rewriting brp hooks run, not what skips them
# — Fedora's %%__os_install_post gates brp-strip / brp-strip-comment-note on
# %%__debug_package being *undefined*. With them in place every ELF file in
# the bundle loses its .comment section, so the payload stops matching
# upstream outside the documented chrpath delta below. brp-strip-lto and
# brp-strip-static-archive are not gated at all. Empty all four so the only
# remaining differences from the upstream RPM are the intended ones. Set them
# to %%{nil} rather than %%undefine'ing them: with rpm 6.0.2 %%undefine does
# not mask brp-strip / brp-strip-comment-note (verified — the hooks still ran,
# while %%undefine on the lto one did take effect).
%global __brp_strip %{nil}
%global __brp_strip_comment_note %{nil}
%global __brp_strip_lto %{nil}
%global __brp_strip_static_archive %{nil}

# brp-mangle-shebangs is not an ELF hook but rewrites payload bytes just the
# same: /usr/bin/onlyoffice-desktopeditors starts with #!/bin/sh, which the
# hook rewrites to #!/usr/bin/sh (+4 bytes), breaking byte-identity on its
# own. It is the only shebang in the payload. Unset it — /bin/sh is a
# symlink to /usr/bin/sh on Fedora, so the shipped script runs identically.
%global __brp_mangle_shebangs %{nil}

# add-determinism's brp hook (add-det) would regenerate /usr/lib/.build-id
# links from the payload's ELF build-id notes and otherwise normalize the
# payload. The payload must ship byte-identical apart from the chrpath delta,
# so unset the hook.
%undefine __brp_add_determinism

# check-rpaths stays ENABLED. Upstream bakes two build-machine paths into the
# dynamic section of seven files (/opt/qt/5.9.9/gcc_64/lib and a developer's
# /home/oleg/GIT/build_tools/... Qt build tree); those cannot exist on an
# end-user machine and fail %%install with ERROR 0002. %%prep removes exactly
# those entries with chrpath instead of skipping the check — same approach as
# the enteauth and localsend rewraps. See the loop in %%prep.

# The bundle ships its own Qt5/ICU/CEF/hunspell stack under
# /opt/onlyoffice/desktopeditors and resolves it through the launcher's
# $ORIGIN RPATH, not the system loader path. Those libs carry SONAMEs, so the
# dependency generator would both advertise them as system providers
# (libQt5Core.so.5, libicudata.so.74, libcef.so, ...) and require them back.
# Generation is therefore kept ON for the real system libraries (which is how
# the CEF/NSS, GTK and X libraries get picked up — the launcher cannot start
# without e.g. libnss3.so, which only libcef.so declares) and the 40
# bundle-private SONAMEs are excluded from it instead (same approach as the
# bitwarden and equibop rewraps). Excluded names are exactly the libs present
# in the bundle tree, so a system library that happens to share a name with a
# bundled one is still resolved by the bundle, as intended. The pattern is a
# prefix match without a trailing $ because the generated require string
# carries the arch qualifier (libcef.so()(64bit)), so an anchored pattern
# would never match (same note as in the bitwarden rewrap).
%global __provides_exclude_from ^/opt/onlyoffice/
%global __requires_exclude ^(libDjVuFile\.so|libDocxRenderer\.so|libEpubFile\.so|libFb2File\.so|libHWPFile\.so|libHtmlFile2\.so|libIWorkFile\.so|libOFDFile\.so|libPdfFile\.so|libQt5Core\.so\.5|libQt5DBus\.so\.5|libQt5Gui\.so\.5|libQt5Multimedia\.so\.5|libQt5MultimediaWidgets\.so\.5|libQt5Network\.so\.5|libQt5OpenGL\.so\.5|libQt5PrintSupport\.so\.5|libQt5Svg\.so\.5|libQt5Widgets\.so\.5|libQt5X11Extras\.so\.5|libQt5XcbQpa\.so\.5|libStarMathConverter\.so|libUnicodeConverter\.so|libXpsFile\.so|libascdocumentscore\.so|libcef\.so|libdoctrenderer\.so|libgraphics\.so|libhunspell\.so|libicudata\.so\.52|libicudata\.so\.74|libicui18n\.so\.52|libicuuc\.so\.52|libicuuc\.so\.74|libkernel\.so|libkernel_network\.so|libooxmlsignature\.so|libqgsttools_p\.so\.1|libqtascdocumentscore\.so|libvideoplayer\.so)
# /usr/bin/onlyoffice-desktopeditors is a shell script, so the generator still
# adds a Requires: /bin/sh from its shebang (verified); every ELF it launches
# lives under /opt, so the library requires come from those files, not it.

Name:           onlyoffice-desktopeditors
Version:        9.4.0
Release:        %autorelease
Summary:        Desktop editors for text docs, spreadsheets, presentations, PDFs, and PDF forms
License:        AGPL-3.0-only
URL:            https://github.com/ONLYOFFICE/DesktopEditors
ExclusiveArch:  x86_64 aarch64

# Upstream publishes one RPM per arch with different filenames:
# onlyoffice-desktopeditors.x86_64.rpm and .aarch64.rpm. Both are listed
# unconditionally: a %ifarch-conditional Source would put only the
# SRPM-building host's RPM into the SRPM, and COPR builds every enabled
# chroot from that single SRPM — the aarch64 chroot would then fail %prep
# with "Bad file: ...aarch64.rpm". Carrying both keeps the SRPM
# self-contained for either chroot; %prep unpacks the one matching the build
# arch (upstream_rpm below).
Source0:        https://github.com/ONLYOFFICE/DesktopEditors/releases/download/v%{version}/onlyoffice-desktopeditors.x86_64.rpm
Source1:        https://github.com/ONLYOFFICE/DesktopEditors/releases/download/v%{version}/onlyoffice-desktopeditors.aarch64.rpm
# Arch -> bundled upstream RPM. ExclusiveArch above restricts the build to
# exactly these two, so upstream_rpm is always defined.
%ifarch x86_64
%global upstream_rpm %{SOURCE0}
%endif
%ifarch aarch64
%global upstream_rpm %{SOURCE1}
%endif
# Offline help: upstream ships the whole help tree (17,587 files, ~325 MB,
# 77 languages) as a separate noarch RPM that nothing in the main payload
# contains. It has no ELF files and no deps of its own beyond the main
# package, so it becomes the noarch -help subpackage below.
Source2:        https://github.com/ONLYOFFICE/DesktopEditors/releases/download/v%{version}/onlyoffice-desktopeditors-help.noarch.rpm
# Curated AppStream metadata: upstream ships none in the RPM (no
# /usr/share/metainfo entry, no appdata.xml in the release tree). The id
# follows Flathub's org.onlyoffice.desktopeditors and the launchable points at
# the desktop file the RPM actually ships. CI patches the <release>
# version/date on each new upstream release.
Source3:        org.onlyoffice.desktopeditors.metainfo.xml

BuildRequires:  desktop-file-utils
BuildRequires:  appstream
BuildRequires:  cpio
BuildRequires:  binutils
BuildRequires:  chrpath
BuildRequires:  file

# Runtime deps the ELF dependency generator cannot see. Everything linked
# (the CEF/NSS stack, GTK, X, XCB, GStreamer, AT-SPI, ALSA, …) is
# auto-detected from DT_NEEDED and deliberately not duplicated here:
# - The font packages are what the editor UI and the bundled document
#   renderer use by name; no ELF links them. Matches upstream's list; adding
#   dejavu-sans-mono-fonts is the only addition.
# - xdg-utils is shelled out to (xdg-open) for external links.
# - libXScrnSaver and the xcb-util-* libs are dlopen'd by Qt's xcb platform
#   plugin; upstream declares them for the same reason.
# - boost-filesystem and curl are dlopen'd by the converter binaries
#   (converter/x2t); no DT_NEEDED entry names them.
# - hicolor-icon-theme owns the /usr/share/icons/hicolor tree this package
#   installs its PNG icons into (upstream forgets this one).
# Deliberately NOT mirrored from upstream: "/bin/sh" (the generator adds it
# from the launcher's shebang itself) and "libstdc++ >= 4.8.0" (the versioned
# form is meaningless against Fedora's far newer gcc runtime).
Requires:       libXScrnSaver
Requires:       xcb-util-image
Requires:       xcb-util-keysyms
Requires:       xcb-util-renderutil
Requires:       xcb-util-wm
Requires:       boost-filesystem
Requires:       curl
Requires:       xdg-utils
Requires:       dejavu-sans-fonts
Requires:       dejavu-sans-mono-fonts
Requires:       dejavu-serif-fonts
Requires:       liberation-mono-fonts
Requires:       liberation-narrow-fonts
Requires:       liberation-sans-fonts
Requires:       liberation-serif-fonts
Requires:       hicolor-icon-theme

%description
ONLYOFFICE Desktop Editors is a free and open-source office suite that
comprises editors for text documents, spreadsheets, presentations, PDFs and
PDF forms, along with a Diagram Viewer. It works fully offline and is
compatible with the Office Open XML formats (.docx, .xlsx, .pptx). This
package rewraps the upstream prebuilt Linux RPM for Fedora (COPR only).

%package help
Summary:        Offline help for ONLYOFFICE Desktop Editors
BuildArch:      noarch
Requires:       %{name} = %{version}-%{release}

%description help
Offline (F1) help for ONLYOFFICE Desktop Editors in 77 languages. Upstream
ships this as a separate RPM because the help tree is large and optional; it
is repackaged here as a noarch subpackage of the same rewrap.

%prep
rpm2cpio %{upstream_rpm} | cpio -idmu --quiet
# The help payload is a pure subtree of the same /opt/onlyoffice/desktopeditors
# path and contains nothing else, so both RPMs extract into one merged tree.
rpm2cpio %{SOURCE2} | cpio -idmu --quiet
# Drop the foreign .build-id carried by the upstream RPM: 134 symlinks into a
# debuginfo tree we do not ship, and Fedora's packaging policy has packages
# not own /usr/lib/.build-id (brp-add-determinism is what generates ours, and
# it is disabled above because this payload must not be rewritten).
rm -rf usr/lib/.build-id
# Upstream bakes build-machine RPATH/RUNPATH entries into several files:
# /opt/qt/5.9.9/gcc_64/lib (libvideoplayer.so, libqtascdocumentscore.so and
# the DesktopEditors launcher on x86_64) and a developer's Qt build tree on
# both arches (the four libqgsttools_p.so names; /home/oleg/GIT/... on x86_64,
# /home/oleg/GITEA/... on aarch64). None can exist on an end-user machine and
# all trip Fedora's check-rpaths with ERROR 0002, failing %%install. Delete
# exactly those entries with chrpath so the rest of each file's dynamic
# section is untouched; behavior is identical because the loader falls back to
# the $ORIGIN entries plus the system paths.
#
# The entries to keep are exactly the ones check-rpaths itself scores as clean:
# $ORIGIN-relative paths and standard system library directories. Matching on
# that definition rather than on the individual build-host paths keeps the
# loop correct if upstream changes its build layout or path spelling.
# The launcher's RPATH is a list whose $ORIGIN entries are load-bearing, so
# the remaining entries are rebuilt rather than the whole RPATH dropped —
# `chrpath -d` on it would stop the app from finding its own bundled libs.
# The loop is a no-op if a future upstream release stops baking these in.
find opt -type f -exec file {} + | grep 'ELF' | cut -d: -f1 > rpath-candidates
while read -r f; do
  rpath=$(readelf -W -d "$f" 2>/dev/null | grep -E '\((RPATH|RUNPATH)\).*:' || true)
  [ -n "$rpath" ] || continue
  value=$(printf '%s\n' "$rpath" | sed -e 's!.*\[\(.*\)\]!\1!')
  kept=$(printf '%s\n' "$value" | tr ':' '\n' \
    | grep -E '^(\$ORIGIN|\$\{ORIGIN)|^/(lib|usr/lib|usr/lib64|usr/libexec|usr/X11R6/lib|usr/local/lib)' \
    | paste -sd:)
  [ "$kept" = "$value" ] && continue
  if [ -z "$kept" ]; then
    chrpath -d "$f"
  else
    chrpath -r "$kept" "$f"
  fi
done < rpath-candidates
rm -f rpath-candidates

%build
# Nothing to compile: the prebuilt upstream RPM is unpacked in %%prep.
# The section exists so rpm's build hooks (e.g. macro-injected steps) run.

%install
cp -a opt %{buildroot}/
cp -a usr %{buildroot}/
install -Dm0644 %{SOURCE3} %{buildroot}%{_metainfodir}/org.onlyoffice.desktopeditors.metainfo.xml

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/onlyoffice-desktopeditors.desktop
appstreamcli validate --no-net %{buildroot}%{_metainfodir}/org.onlyoffice.desktopeditors.metainfo.xml

%files
%license /usr/share/licenses/onlyoffice-desktopeditors/LICENSE
%license /usr/share/licenses/onlyoffice-desktopeditors/LICENSE-CC.txt
%license /usr/share/licenses/onlyoffice-desktopeditors/3DPARTYLICENSE
%doc /usr/share/doc/onlyoffice-desktopeditors/ChangeLog
%doc /usr/share/doc/onlyoffice-desktopeditors/NEWS
%{_bindir}/desktopeditors
%{_bindir}/onlyoffice-desktopeditors
# The help tree belongs to the -help subpackage; %exclude keeps the glob below
# from claiming it in the main package. Upstream splits the offline help across
# one tree per editor (common, documenteditor, pdfeditor, presentationeditor,
# spreadsheeteditor, visioeditor — 17,255 files in total), so the glob has to
# cover every apps/<editor> path, not only apps/common.
%exclude /opt/onlyoffice/desktopeditors/editors/web-apps/apps/*/main/resources/help
/opt/onlyoffice/
%{_datadir}/applications/onlyoffice-desktopeditors.desktop
%{_datadir}/icons/hicolor/*/apps/onlyoffice-desktopeditors.png
%{_metainfodir}/org.onlyoffice.desktopeditors.metainfo.xml
# Release is %%autorelease. COPR builds this repo from an uploaded SRPM, where
# rpm's plain %%autorelease fallback applies: the release is a literal 1 plus
# the chroot's dist tag, NOT the changelog entry count (verified against the
# published builds: iloader's 2.3.3-1 was built from a spec with three
# changelog entries, and the only unique NVRs any of these projects ever
# published came from the CI's force_build path). A %%changelog entry therefore
# documents a spec change but does not on its own give an already-built
# upstream version a new NVR — publish it with the force_build workflow input,
# which rewrites Release to %%{autorelease}.f<run_id> (a unique, higher
# release), exactly as the earlier forced builds in these projects did.
#
# Note for anyone comparing against the vendor repo: ONLYOFFICE publishes this
# same package name in their own yum repository (download.onlyoffice.com) with
# a high release number (e.g. 129.el7), while an SRPM uploaded to COPR gets
# the literal release 1 plus the dist tag. rpm compares the release field
# segment by segment, so theirs outranks ours for any shared version and dnf
# prefers theirs when both repositories are enabled. See README.md.

%files help
/opt/onlyoffice/desktopeditors/editors/web-apps/apps/*/main/resources/help/

%changelog
* Sun Sep 13 2026 Anudeep D <anudeepd2@gmail.com> - 9.4.0-1
- Initial Fedora repackaging of upstream prebuilt RPMs (x86_64 + aarch64),
  with the offline help tree as a noarch -help subpackage
