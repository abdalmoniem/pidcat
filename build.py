import os
import sys
import glob
import shutil
import argparse
import subprocess

from subprocess import PIPE

from pathlib import Path
from dataclasses import dataclass

from terminalColors import RED
from terminalColors import colorize

__version__ = "2.5.4"

TAB_WIDTH = 4
TAB_CHAR = " " * TAB_WIDTH

scriptDir = os.path.dirname(os.path.abspath(__file__))

projectRoot = scriptDir
iconPath = os.path.join(projectRoot, "resources", "icon.png")
versionPath = os.path.join(projectRoot, "resources", "version_info.py")
workPath = os.path.join(projectRoot, "generated", "build")
distPath = os.path.join(projectRoot, "generated", "dist")
specPath = os.path.join(projectRoot, "generated")
mainScript = os.path.join(projectRoot, "pidcat.py")
setupScript = os.path.join(projectRoot, "setup", "setup.iss")
versionInfoScript = os.path.join(projectRoot, "resources", "version_info.py")


@dataclass
class Args:
    """Args for the build script."""

    buildExecutable: bool = False
    """build the executable package"""

    buildInstaller: bool = False
    """build the installer package"""

    clean: bool = False
    """clean generated files"""

    rebuild: bool = False
    """rebuild the executable package"""

    buildAll: bool = False
    """build both the executable and installer packages"""

    install: bool = False
    """install after building"""

    reinstall: bool = False
    """rebuild, build installer, and install"""

    isccPath: str = ""
    """path to the Inno Setup Compiler (iscc.exe)"""


def createArgParser() -> argparse.ArgumentParser:
    """Creates and returns the ArgumentParser instance."""

    parser = argparse.ArgumentParser(
        add_help=False,
        prog=Path(sys.argv[0]).stem,
        description="Builds the PidCat executable using PyInstaller",
    )

    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit.",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{Path(parser.prog).stem} v{__version__}",
        help="Print the version number and exit",
    )

    parser.add_argument(
        "-e",
        "--build-executable",
        dest="buildExecutable",
        action="store_true",
        default=False,
        help="Build the executable using PyInstaller",
    )

    parser.add_argument(
        "-b",
        "--build-installer",
        dest="buildInstaller",
        action="store_true",
        default=False,
        help="Build the installer using Inno Setup Compiler",
    )

    parser.add_argument(
        "-c",
        "--clean",
        dest="clean",
        action="store_true",
        default=False,
        help="Clean generated files",
    )

    parser.add_argument(
        "-r",
        "--rebuild",
        dest="rebuild",
        action="store_true",
        default=False,
        help="Rebuild the executable package",
    )

    parser.add_argument(
        "-a",
        "--build-all",
        dest="buildAll",
        action="store_true",
        default=False,
        help="Build both the executable and installer packages",
    )

    parser.add_argument(
        "-i",
        "--install",
        dest="install",
        action="store_true",
        default=False,
        help="Install the application by running the generated installer",
    )

    parser.add_argument(
        "-R",
        "--reinstall",
        dest="reinstall",
        action="store_true",
        default=False,
        help="Rebuild, build installer, and install",
    )

    parser.add_argument(
        "-p",
        "--iscc-path",
        metavar="ISCC_PATH",
        dest="isccPath",
        action="store",
        default="",
        help="Path to Inno Setup Compiler (ISCC) executable",
    )

    return parser


def updateMainScriptVersion():
    with open(file=mainScript, mode="r+", encoding="utf-8") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if line.strip().startswith("__version__"):
                fileDescriptor.write(f'__version__ = "{__version__}"\n')
            else:
                fileDescriptor.write(line)


def updateSetupScriptVersion():
    with open(file=setupScript, mode="r+", encoding="utf-8") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if line.strip().startswith("#define AppVersion"):
                fileDescriptor.write(f'#define AppVersion "{__version__}"\n')
            else:
                fileDescriptor.write(line)


def updateVersionInfoScriptVersion():
    versionParts = __version__.split(".")
    versionTuple = tuple(int(versionPart) for versionPart in versionParts) + (0,) * (4 - len(versionParts))

    with open(file=versionInfoScript, mode="r+", encoding="utf-8") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if "filevers=" in line:
                fileDescriptor.write(f"{TAB_CHAR}filevers={versionTuple},\n")
            elif "prodvers=" in line:
                fileDescriptor.write(f"{TAB_CHAR}prodvers={versionTuple},\n")
            elif 'StringStruct("FileVersion"' in line:
                fileDescriptor.write(
                    f'{TAB_CHAR * 6}StringStruct("FileVersion", "{__version__}"),  # Matches "File version"\n'
                )
            elif 'StringStruct("ProductVersion"' in line:
                fileDescriptor.write(
                    f'{TAB_CHAR * 6}StringStruct("ProductVersion", "{__version__}"),  # Matches "Product version"\n'
                )
            else:
                fileDescriptor.write(line)


def clean():
    shutil.rmtree(path="generated", ignore_errors=True)
    shutil.rmtree(path="setup/Output", ignore_errors=True)


def runCommand(command: list[str], errorMessage: str | None = None) -> None:
    """Runs a command using subprocess and handles errors."""

    def printException(message: str) -> None:
        if errorMessage is not None:
            error = colorize(f"[!] {errorMessage}: {message}", foreground=RED)
            print(error, file=sys.stderr)

    try:
        pid = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        _, stderr = pid.communicate()

        if pid.returncode != 0:
            erroneousCommand = " ".join(command)
            raise subprocess.CalledProcessError(pid.returncode, erroneousCommand, stderr=stderr.decode().strip())

    except subprocess.CalledProcessError as ex:
        printException(str(ex))

        for line in ex.stderr.splitlines():
            error = colorize(f"[!] {line}", foreground=RED)
            print(error, file=sys.stderr)

        sys.exit(ex.returncode)


def runPyInstaller():
    command = [
        "pyinstaller",
        "--onefile",
        "--console",
        f"--workpath={workPath}",
        f"--distpath={distPath}",
        f"--specpath={specPath}",
        f"--icon={iconPath}",
        f"--version-file={versionPath}",
        "--name=PidCat",
        mainScript,
    ]

    runCommand(command=command, errorMessage="Error occurred while building executable")


def runBuildInstaller(args: Args):
    isccPath = "iscc" if not args.isccPath else args.isccPath
    command = [isccPath, setupScript]

    try:
        runCommand(command=command, errorMessage="Error occurred while building installer")
    except FileNotFoundError as ex:
        erroneiousPath = isccPath

        error = colorize(
            f"[!] Error occurred while building installer: {ex}: '{erroneiousPath}'",
            foreground=RED,
        )
        print(error, file=sys.stderr)

        error = colorize(
            f"[!] Inno Setup Compiler (iscc) not found at path: '{erroneiousPath}'. "
            "Please install Inno Setup and ensure 'iscc' is in your system PATH, "
            "or provide the correct path using the --iscc-path argument.",
            foreground=RED,
        )
        print(error, file=sys.stderr)

        sys.exit(ex.errno)


def runInstaller():
    installerPath = str(max(glob.glob("setup/Output/*.exe"), key=os.path.getmtime))

    try:
        subprocess.run([installerPath])
    except subprocess.CalledProcessError as ex:
        error = colorize(
            f"[!] Error occurred while running installer: {ex}",
            foreground=RED,
        )
        print(error, file=sys.stderr)
        sys.exit(ex.returncode)


def main() -> None:
    """The main entry point of the script."""
    parser = createArgParser()
    args = parser.parse_args()

    args = Args(**vars(args))

    if args.buildAll:
        args.buildExecutable = True
        args.buildInstaller = True

    print(f"[*] Building PidCat v{__version__}...")

    print("[*] Updating version information...")
    updateMainScriptVersion()
    updateSetupScriptVersion()
    updateVersionInfoScriptVersion()

    if args.clean:
        print("[*] Cleaning generated files...")
        clean()

    if args.rebuild:
        print("[*] Cleaning generated files...")
        clean()
        print("[*] Rebuilding executable...")
        runPyInstaller()

    if args.buildExecutable:
        print("[*] Running PyInstaller...")
        runPyInstaller()

    if args.buildInstaller:
        print("[*] Building installer...")
        runBuildInstaller(args)

    if args.install:
        print("[*] Running installer...")
        runInstaller()

    if args.reinstall:
        print("[*] Cleaning generated files...")
        clean()
        print("[*] Rebuilding executable...")
        runPyInstaller()
        print("[*] Building installer...")
        runBuildInstaller(args)
        print("[*] Running installer...")
        runInstaller()

    print("[✓] Build complete!")


if __name__ == "__main__":
    main()
