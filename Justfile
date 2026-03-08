set export := true

alias r := run
alias b := build
alias c := clean
alias rb := rebuild
alias bi := build-installer
alias ba := build-all
alias i := install
alias ri := reinstall

TARGET_OS := os()

[doc('List available recipes')]
default:
    @just --list --unsorted

[doc('Run the pidcat python script directly')]
[group('run')]
run args:
    @uv run main.py $args

[doc('Build the pidcat executable using PyInstaller')]
[group('build')]
build:
    @uv run build/build.py build-executable

[doc('Clean the build directory')]
[group('build')]
clean:
    @uv run build/build.py clean

[doc('Rebuild the pidcat executable using PyInstaller')]
[group('build')]
rebuild:
    @uv run build/build.py rebuild

[doc('Build the installer using Inno Setup Compiler')]
[group('build')]
build-installer:
    @uv run build/build.py build-installer

[doc('Perform a full rebuild and create the installer')]
[group('build')]
build-all:
    @uv run build/build.py build-all

[doc('Install the application by running the generated installer')]
[group('install')]
install:
    @uv run build/build.py install

    @just post_install

[doc('Perform a full rebuild, create the installer, and install the application')]
[group('install')]
reinstall:
    @uv run build/build.py reinstall

    @just post_install

[private]
[script]
post_install:
    pidcat_exe="$(which pidcat)"
    pidcat_exe_basename="$(basename "$pidcat_exe")"

    echo
    if command -v ccze >/dev/null 2>&1; then
        just installed_message "$pidcat_exe" | ccze --raw-ansi
    else
        just installed_message "$pidcat_exe"
    fi

    if [ "$TARGET_OS" != "windows" ]; then
        strip "$pidcat_exe" 2>/dev/null || echo "could not strip $pidcat_exe_basename"
    fi

    if command -v ccze >/dev/null 2>&1; then
        just file_info "$pidcat_exe" | ccze --raw-ansi
        just ldd_info  "$pidcat_exe" | ccze --raw-ansi
        just du_info   "$pidcat_exe" | ccze --raw-ansi
    else
        just file_info "$pidcat_exe"
        just ldd_info  "$pidcat_exe"
        just du_info   "$pidcat_exe"
    fi

[private]
installed_message pidcat_exe:
    @echo "installed pidcat to "$pidcat_exe""

[private]
file_info pidcat_exe:
    @file "$pidcat_exe"

[private]
ldd_info pidcat_exe:
    @ldd "$pidcat_exe"

[private]
du_info pidcat_exe:
    @du -hs --time --time-style=+'%a, %d/%b/%Y - %r' "$pidcat_exe"
