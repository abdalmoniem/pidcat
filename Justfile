set export := true

alias r := run
alias b := build
alias c := clean
alias rb := rebuild

# alias bi := build-installer
# alias ba := build-all
# alias i := install
# alias ri := reinstall

TARGET_OS := os()
export VENV := if TARGET_OS == "windows" { ".venv" } else { ".venv_unix" }
export UV_PROJECT_ENVIRONMENT := if TARGET_OS == "windows" { ".venv" } else { ".venv_unix" }

[doc('List available recipes')]
default:
    @just --list --unsorted

[doc('Clean the build directory')]
[group('build')]
clean:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run -m build.build clean

[doc('Build the pidcat executable using PyInstaller')]
[group('build')]
build:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run -m build.build build

[doc('Rebuild the pidcat executable using PyInstaller')]
[group('build')]
rebuild:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run -m build.build rebuild

[doc('Build the installer using Inno Setup Compiler')]
[group('build')]
[windows]
build-installer:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run -m build.build build-installer

[doc('Perform a full rebuild and create the installer')]
[group('build')]
[windows]
build-all:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run -m build.build build-all

[doc('Run the pidcat python script directly')]
[group('run')]
run args:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run main.py $args

[doc('Install the application by running the generated installer')]
[group('install')]
[windows]
install:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run -m build.build install

    @just post_install

[doc('Perform a full rebuild, create the installer, and install the application')]
[group('install')]
[windows]
reinstall:
    @env | grep UV_PROJECT_ENVIRONMENT

    @uv run build/build.py reinstall

    @just post_install

[arg('tag', help='the tag to show changelog for')]
[doc('shows changelog for tag')]
[group('changelog')]
tag_changelog tag:
    @git-cliff --offline --body="$(cat cliff_body.tera)" \
               "$(git describe --tags --abbrev=0 $tag^ 2>/dev/null || git rev-list --max-parents=0 HEAD)..$tag"

[doc('shows changelog for all tagged commits')]
[group('changelog')]
tags_changelog:
    @git-cliff --offline --body="$(cat cliff_body.tera)" --tag "$(git describe --tags --abbrev=0)"

[doc('shows changelog for untagged commits')]
[group('changelog')]
unreleased_changelog:
    @git-cliff --offline --body="$(cat cliff_body.tera)" "$(git describe --tags --abbrev=0)..HEAD"

[doc('shows changelog for all commits')]
[group('changelog')]
all_changelog:
    @git-cliff --offline --body="$(cat cliff_body.tera)"

[doc('updates CHANGELOG.md with changelog from all tagged commits')]
[group('changelog')]
update_changelog:
    @git-cliff --offline --body="$(cat cliff_body.tera)" --tag "$(git describe --tags --abbrev=0)" | tee CHANGELOG.md
    @echo
    @echo "changelog written to '$(realpath CHANGELOG.md)'!"

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
