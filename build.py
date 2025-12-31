import os
import sys
import glob
import shutil
import argparse
import threading
import subprocess

from subprocess import PIPE

from pathlib import Path
from dataclasses import dataclass

from io import TextIOWrapper
from typing import TextIO, cast

from terminalColors import RED
from terminalColors import colorize

sysStdout = cast(TextIOWrapper, sys.stdout)
sysStderr = cast(TextIOWrapper, sys.stderr)

sysStdout.reconfigure(encoding="utf-8")
sysStderr.reconfigure(encoding="utf-8")

VERSION = "2.6.0"

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
    """
    Holds the command-line arguments for the build script.

    Attributes:
        buildExecutable (bool): build the executable package
        buildInstaller (bool): build the installer package
        clean (bool): clean generated files
        rebuild (bool): rebuild the executable package
        buildAll (bool): build both the executable and installer packages
        install (bool): install after building
        reinstall (bool): rebuild, build installer, and install
        isccPath (str): path to the Inno Setup Compiler (iscc.exe)
    """

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
        version=f"{Path(parser.prog).stem} v{VERSION}",
        help="Print the version number and exit",
    )

    parser.add_argument(
        "-e",
        "--build-executable",
        dest="buildExecutable",
        action="store_true",
        default=True,
        help="Build the executable using PyInstaller, default: %(default)s",
    )

    parser.add_argument(
        "-b",
        "--build-installer",
        dest="buildInstaller",
        action="store_true",
        default=False,
        help="Build the installer using Inno Setup Compiler, default: %(default)s",
    )

    parser.add_argument(
        "-c",
        "--clean",
        dest="clean",
        action="store_true",
        default=False,
        help="Clean generated files, default: %(default)s",
    )

    parser.add_argument(
        "-r",
        "--rebuild",
        dest="rebuild",
        action="store_true",
        default=False,
        help="Rebuild the executable package, default: %(default)s",
    )

    parser.add_argument(
        "-a",
        "--build-all",
        dest="buildAll",
        action="store_true",
        default=False,
        help="Build both the executable and installer packages, default: %(default)s",
    )

    parser.add_argument(
        "-i",
        "--install",
        dest="install",
        action="store_true",
        default=False,
        help="Install the application by running the generated installer, default: %(default)s",
    )

    parser.add_argument(
        "-R",
        "--reinstall",
        dest="reinstall",
        action="store_true",
        default=False,
        help="Rebuild, build installer, and install, default: %(default)s",
    )

    parser.add_argument(
        "-p",
        "--iscc-path",
        metavar="ISCC_PATH",
        dest="isccPath",
        action="store",
        default=None,
        help="Path to Inno Setup Compiler (ISCC) executable, default: %(default)s",
    )

    return parser


def updateMainScriptVersion() -> None:
    """
    Updates the version string in the main script file.

    This function reads the main script file, updates the version string, and writes the updated content back to the file.
    """

    with open(file=mainScript, mode="r+", encoding="utf-8") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if line.strip().startswith("VERSION"):
                fileDescriptor.write(f'VERSION = "{VERSION}"\n')
            else:
                fileDescriptor.write(line)


def updateSetupScriptVersion() -> None:
    """
    Updates the version string in the setup script file.

    This function reads the setup script file, updates the version string, and writes the updated content back to the file.
    """

    with open(file=setupScript, mode="r+", encoding="utf-8") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if line.strip().startswith("#define AppVersion"):
                fileDescriptor.write(f'#define AppVersion "{VERSION}"\n')
            else:
                fileDescriptor.write(line)


def updateVersionInfoScriptVersion() -> None:
    """
    Updates the version string in the version info script file.

    This function reads the version info script file, updates the version string, and writes the updated content back to the file.
    """

    versionParts = VERSION.split(".")
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
                    f'{TAB_CHAR * 6}StringStruct("FileVersion", "{VERSION}"),  # Matches "File version"\n'
                )
            elif 'StringStruct("ProductVersion"' in line:
                fileDescriptor.write(
                    f'{TAB_CHAR * 6}StringStruct("ProductVersion", "{VERSION}"),  # Matches "Product version"\n'
                )
            else:
                fileDescriptor.write(line)


def clean() -> None:
    """
    Cleans up generated files and directories.

    This function deletes the generated files and directories, without throwing an error if they do not exist.
    """
    shutil.rmtree(path="generated", ignore_errors=True)
    shutil.rmtree(path="setup/Output", ignore_errors=True)


def runCommand(command: list[str], errorMessage: str | None = None) -> None:
    """
    Runs a command and prints its output.

    Arguments:
        command (list[str]): The command to run.
        errorMessage (str | None, optional): An error message to print if the command fails. Defaults to None.
    """

    stderr = []

    def streamReader(pipe: TextIO, file: TextIO) -> None:
        """
        Streams the output of a pipe to a file.

        This function reads the output of a pipe and prints it to a file, with optional colorization.
        If the file is sys.stderr, the output is colored red and prefixed with "[!] ".
        If the file is not sys.stderr, the output is colored green and prefixed with "[*] ".

        Arguments:
            pipe (TextIO): The pipe to read from.
            file (TextIO): The file to print the output to.
        """

        with pipe:
            for line in iter(pipe.readline, ""):
                if file == sys.stderr:
                    stderr.append(line.strip())
                    error = colorize(f"[!] {line.strip()}", foreground=RED)
                    print(error, file=file, flush=True)
                else:
                    print(f"[*] {line.strip()}", file=file, flush=True)

    def printException(message: str) -> None:
        """
        Prints an error message to sys.stderr, with optional colorization.

        If errorMessage is provided, it is prefixed to the error message.

        Arguments:
            message (str): The error message to print.
        """

        if errorMessage:
            error = colorize(f"[!] {errorMessage}: {message}", foreground=RED)
        else:
            error = colorize(f"[!] {message}", foreground=RED)

        print(error, file=sys.stderr)

    try:
        pid = subprocess.Popen(
            command,
            stdout=PIPE,
            stderr=PIPE,
            text=True,  # Automatically decode bytes to strings
            bufsize=1,  # Line buffered
            universal_newlines=True,
        )

        assert pid.stdout and pid.stderr

        stdoutThread = threading.Thread(target=streamReader, args=(pid.stdout, sys.stdout))
        stderrThread = threading.Thread(target=streamReader, args=(pid.stderr, sys.stderr))

        stdoutThread.start()
        stderrThread.start()

        pid.wait()

        stdoutThread.join()
        stderrThread.join()

        if pid.returncode != 0:
            erroneousCommand = " ".join(command)
            raise subprocess.CalledProcessError(pid.returncode, erroneousCommand, stderr="\n".join(stderr))

    except KeyboardInterrupt:
        error = colorize("\nProcess interrupted by user", foreground=RED)
        print(error, file=sys.stderr)

        sys.exit(0)
    except subprocess.CalledProcessError as ex:
        error = colorize("\nERRORS:", foreground=RED)
        print(error, file=sys.stderr)

        printException(str(ex))

        for line in ex.stderr.splitlines():
            error = colorize(f"[!] {line}", foreground=RED)
            print(error, file=sys.stderr)

        sys.exit(ex.returncode)


def runPyInstaller() -> None:
    """
    Builds the PyInstaller executable.

    This function runs the PyInstaller command with the necessary arguments to build the executable.
    """

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


def runBuildInstaller(args: Args) -> None:
    """
    Builds the Inno Setup installer.

    This function runs the Inno Setup compiler command with the necessary arguments to build the installer.

    Arguments:
        args (Args): The parsed command-line arguments.
    """

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


def runInstaller() -> None:
    """
    Runs the Inno Setup installer executable.

    This function runs the Inno Setup installer executable generated by the buildInstaller function.
    It searches for the latest installer executable in the setup/Output directory.
    """

    installerPath = str(max(glob.glob("setup/Output/*.exe"), key=os.path.getmtime))
    command = [installerPath]

    runCommand(command=command, errorMessage="Error occurred while running installer")


def main() -> None:
    """
    Main entry point for the build script.

    This function parses the command-line arguments, updates version information, and runs the necessary build steps.
    It will clean the generated files, run PyInstaller, build the installer, install the application, reinstall the application, or run the installer based on the arguments provided.
    """

    parser = createArgParser()
    args = parser.parse_args()

    args = Args(**vars(args))

    if args.buildAll:
        args.buildExecutable = True
        args.buildInstaller = True

    print(f"[*] Building PidCat v{VERSION}...")

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
