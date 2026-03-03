alias r := run
alias b := build
alias c := clean
alias rb := rebuild
alias bi := build-installer
alias ba := build-all
alias i := install
alias ri := reinstall

[doc('List available recipes')]
default:
    @just --list --unsorted

[doc('Run the pidcat python script directly')]
[group('run')]
run:
    @uv run main.py

[doc('Build the pidcat executable using PyInstaller')]
[group('build')]
build:
    @uv run build/build.py --build-executable

[doc('Clean the build directory')]
[group('build')]
clean:
    @uv run build/build.py --clean

[doc('Rebuild the pidcat executable using PyInstaller')]
[group('build')]
rebuild:
    @uv run build/build.py --rebuild

[doc('Build the installer using Inno Setup Compiler')]
[group('build')]
build-installer:
    @uv run build/build.py --build-installer

[doc('Perform a full rebuild and create the installer')]
[group('build')]
build-all:
    @uv run build/build.py --build-all

[doc('Install the application by running the generated installer')]
[group('install')]
install:
    @uv run build/build.py --install

[doc('Perform a full rebuild, create the installer, and install the application')]
[group('install')]
reinstall:
    @uv run build/build.py --reinstall
