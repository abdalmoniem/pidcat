from __future__ import annotations

import os
import sys
import glob
import shutil
import argparse
import threading
import subprocess

from typing import cast
from typing import List
from typing import Union
from typing import TextIO
from typing import Optional

from enum import StrEnum
from pathlib import Path
from subprocess import PIPE
from io import TextIOWrapper
from dataclasses import dataclass

from utils.Colored import Color, ColoredString

sysStdout = cast(TextIOWrapper, sys.stdout)
sysStderr = cast(TextIOWrapper, sys.stderr)

sysStdout.reconfigure(encoding="utf-8")
sysStderr.reconfigure(encoding="utf-8")

VERSION = "2.6.1"

TAB_WIDTH = 4
TAB_CHAR = " " * TAB_WIDTH

IS_WINDOWS = sys.platform == "win32"

scriptDir = str(Path(__file__).parent)
iconPath = str(Path(scriptDir).joinpath("resources", "icon.png"))
versionPath = str(Path(scriptDir).joinpath("resources", "version_info.py"))
workPath = str(Path(scriptDir).joinpath("generated", "build"))
distPath = str(Path(scriptDir).joinpath("generated", "dist"))
generatedPath = str(Path(scriptDir).joinpath("generated"))
mainScript = str(Path(scriptDir).parent.joinpath("main.py"))
setupScriptPath = str(Path(scriptDir).joinpath("setup"))
setupOutputPath = str(Path(setupScriptPath).joinpath("Output"))
setupScript = str(Path(setupScriptPath).joinpath("setup.iss"))
versionInfoScript = str(Path(scriptDir).joinpath("resources", "version_info.py"))


class CommandName(StrEnum):
    Clean = "clean"
    Build = "build"
    Rebuild = "rebuild"
    if IS_WINDOWS:
        BuildInstaller = "build-installer"
        BuildAll = "build-all"
        Install = "install"
        Reinstall = "reinstall"
    Help = "help"


@dataclass
class Command:
    @dataclass
    class Clean:
        pass

    @dataclass
    class Build:
        pass

    @dataclass
    class Rebuild:
        pass

    if IS_WINDOWS:

        @dataclass
        class BuildInstaller:
            isccPath: Optional[str] = None

        @dataclass
        class BuildAll:
            isccPath: Optional[str] = None

        @dataclass
        class Install:
            pass

        @dataclass
        class Reinstall:
            isccPath: Optional[str] = None

    if IS_WINDOWS:
        CommandType = Union[
            Clean,
            Build,
            Rebuild,
            BuildInstaller,
            BuildAll,
            Install,
            Reinstall,
        ]
    else:
        CommandType = Union[Clean, Build, Rebuild]

    @staticmethod
    def fromArgs(args: argparse.Namespace) -> CommandType:
        match CommandName(args.command):
            case CommandName.Clean:
                return Command.Clean()
            case CommandName.Build:
                return Command.Build()
            case CommandName.Rebuild:
                return Command.Rebuild()
            case CommandName.BuildInstaller:
                return Command.BuildInstaller(args.isccPath)
            case CommandName.BuildAll if IS_WINDOWS:
                return Command.BuildAll(args.isccPath)
            case CommandName.Install if IS_WINDOWS:
                return Command.Install()
            case CommandName.Reinstall if IS_WINDOWS:
                return Command.Reinstall(args.isccPath)
            case _:
                raise ValueError(f"Unknown Command '{args.command}'")


def createArgParser() -> argparse.ArgumentParser:
    """Creates and returns the ArgumentParser instance."""

    helpParent = argparse.ArgumentParser(add_help=False)
    helpParent.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and exit",
    )

    parser = argparse.ArgumentParser(
        add_help=False,
        parents=[helpParent],
        prog=Path(sys.argv[0]).stem,
        description="Builds the PidCat executable using PyInstaller",
    )

    aboutOptions = parser.add_argument_group(title="Options")

    aboutOptions.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{Path(parser.prog).stem} v{VERSION}",
        help="Print the version number and exit",
    )

    subParsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    subParsers.add_parser(
        CommandName.Clean,
        add_help=False,
        parents=[helpParent],
        help="Clean generated files",
        description="Clean generated files",
    )

    subParsers.add_parser(
        CommandName.Build,
        add_help=False,
        parents=[helpParent],
        help="Build the executable using PyInstaller",
        description="Build the executable using PyInstaller",
    )

    subParsers.add_parser(
        CommandName.Rebuild,
        add_help=False,
        parents=[helpParent],
        help="Rebuild the executable package",
        description="Rebuild the executable package",
    )

    if IS_WINDOWS:
        subParsers.add_parser(
            CommandName.BuildInstaller,
            add_help=False,
            parents=[helpParent],
            help="Build the installer using Inno Setup Compiler",
            description="Build the installer using Inno Setup Compiler",
        ).add_argument(
            "-p",
            "--iscc-path",
            metavar="ISCC_PATH",
            dest="isccPath",
            action="store",
            default=None,
            help="Path to Inno Setup Compiler (ISCC) executable, default: %(default)s",
        )

        subParsers.add_parser(
            CommandName.BuildAll,
            add_help=False,
            parents=[helpParent],
            help="Build both the executable and installer packages",
            description="Build both the executable and installer packages",
        ).add_argument(
            "-p",
            "--iscc-path",
            metavar="ISCC_PATH",
            dest="isccPath",
            action="store",
            default=None,
            help="Path to Inno Setup Compiler (ISCC) executable, default: %(default)s",
        )

        subParsers.add_parser(
            CommandName.Install,
            add_help=False,
            parents=[helpParent],
            help="Install the application by running the generated installer",
            description="Install the application by running the generated installer",
        )

        subParsers.add_parser(
            CommandName.Reinstall,
            add_help=False,
            parents=[helpParent],
            help="Rebuild, build installer, and install",
            description="Rebuild, build installer, and install",
        ).add_argument(
            "-p",
            "--iscc-path",
            metavar="ISCC_PATH",
            dest="isccPath",
            action="store",
            default=None,
            help="Path to Inno Setup Compiler (ISCC) executable, default: %(default)s",
        )

    subParsers.add_parser(
        "help",
        add_help=False,
        parents=[helpParent],
        help="Show this help message or the help of a command and exit",
        description="Show this help message or the help of a command and exit",
    ).add_argument("helpCommand", nargs="?", metavar="COMMAND", help="Command to show help for")

    return parser


def updateMainScriptVersion() -> None:
    """
    Updates the version string in the main script file.

    This function reads the main script file, updates the version string,
    and writes the updated content back to the file.
    """

    with open(file=mainScript, mode="r+", encoding="utf-8") as fd:
        lines = fd.readlines()

        fd.seek(0)
        fd.truncate()

        for line in lines:
            if line.strip().startswith("VERSION"):
                fd.write(f'VERSION = "{VERSION}"\n')
            else:
                fd.write(line)


def updateSetupScriptVersion() -> None:
    """
    Updates the version string in the setup script file.

    This function reads the setup script file, updates the version string,
    and writes the updated content back to the file.
    """

    with open(file=setupScript, mode="r+", encoding="utf-8") as fd:
        lines = fd.readlines()

        fd.seek(0)
        fd.truncate()

        for line in lines:
            if line.strip().startswith("#define AppVersion"):
                fd.write(f'#define AppVersion "{VERSION}"\n')
            else:
                fd.write(line)


def updateVersionInfoScriptVersion() -> None:
    """
    Updates the version string in the version info script file.

    This function reads the version info script file, updates the version string,
    and writes the updated content back to the file.
    """

    versionParts = VERSION.split(".")
    versionTuple = tuple(int(versionPart) for versionPart in versionParts) + (0,) * (4 - len(versionParts))

    with open(file=versionInfoScript, mode="r+", encoding="utf-8") as fd:
        lines = fd.readlines()

        fd.seek(0)
        fd.truncate()

        for line in lines:
            if "filevers=" in line:
                fd.write(f"{TAB_CHAR}filevers={versionTuple},\n")
            elif "prodvers=" in line:
                fd.write(f"{TAB_CHAR}prodvers={versionTuple},\n")
            elif 'StringStruct("FileVersion"' in line:
                fd.write(f'{TAB_CHAR * 6}StringStruct("FileVersion", "{VERSION}"),  # Matches "File version"\n')
            elif 'StringStruct("ProductVersion"' in line:
                fd.write(f'{TAB_CHAR * 6}StringStruct("ProductVersion", "{VERSION}"),  # Matches "Product version"\n')
            else:
                fd.write(line)


def updateVersions() -> None:
    updateMainScriptVersion()
    updateSetupScriptVersion()
    updateVersionInfoScriptVersion()


def clean() -> None:
    """
    Cleans up generated files and directories.

    This function deletes the generated files and directories, without throwing an error if they do not exist.
    """
    shutil.rmtree(path=generatedPath, ignore_errors=True)
    shutil.rmtree(path=setupOutputPath, ignore_errors=True)


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
                    error = ColoredString(f"[!] {line.strip()}").color(Color.Red)
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
            error = ColoredString(f"[!] {errorMessage}: {message}").color(Color.Red)
        else:
            error = ColoredString(f"[!] {message}").color(Color.Red)

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
        error = ColoredString("\nProcess interrupted by user").color(Color.Red)
        print(error, file=sys.stderr)

        sys.exit(0)
    except subprocess.CalledProcessError as ex:
        error = ColoredString("\nERRORS:").color(Color.Red)
        print(error, file=sys.stderr)

        printException(str(ex))

        for line in ex.stderr.splitlines():
            error = ColoredString(f"[!] {line}").color(Color.Red)
            print(error, file=sys.stderr)

        sys.exit(ex.returncode)


def runPyInstaller() -> None:
    """
    Builds the PyInstaller executable.

    This function runs the PyInstaller command with the necessary arguments to build the executable.
    """

    pyinstallerLogConfig = (
        "import sys;"
        "import logging;"
        "from PyInstaller.__main__ import run;"
        "root = logging.getLogger();"
        "[root.removeHandler(handler) for handler in root.handlers];"
        "streamHandler = logging.StreamHandler(sys.stdout);"
        "streamHandler.addFilter(lambda logRecord: logRecord.levelno < logging.ERROR);"
        "root.addHandler(streamHandler);"
        "stderrHandler = logging.StreamHandler(sys.stderr);"
        "stderrHandler.setLevel(logging.ERROR);"
        "root.addHandler(stderrHandler);"
        "run()"
    )

    command = [
        # "pyinstaller",
        sys.executable,
        "-c",
        pyinstallerLogConfig,
        "--onefile",
        "--console",
        # "--log-level=DEBUG",
        f"--workpath={workPath}",
        f"--distpath={distPath}",
        f"--specpath={generatedPath}",
        f"--icon={iconPath}",
        f"--version-file={versionPath}",
        "--name=pidcat",
        mainScript,
    ]

    runCommand(command=command, errorMessage="Error occurred while building executable")


def runBuildInstaller(isccPath: Optional[str] = None) -> None:
    """
    Builds the Inno Setup installer.

    This function runs the Inno Setup compiler command with the necessary arguments to build the installer.

    Arguments:
        isccPath (str): path to the Inno Setup Compiler (iscc.exe).
    """

    isccPath = "iscc" if not isccPath else isccPath
    command = [isccPath, setupScript]

    try:
        runCommand(command=command, errorMessage="Error occurred while building installer")
    except FileNotFoundError as ex:
        erroneiousPath = isccPath

        error = ColoredString(f"[!] Error occurred while building installer: {ex}: '{erroneiousPath}'").color(Color.Red)
        print(error, file=sys.stderr)

        error = ColoredString(
            f"[!] Inno Setup Compiler (iscc) not found at path: '{erroneiousPath}'. "
            "Please install Inno Setup and ensure 'iscc' is in your system PATH, "
            "or provide the correct path using the --iscc-path argument."
        ).color(Color.Red)
        print(error, file=sys.stderr)

        sys.exit(ex.errno)


def runInstaller() -> None:
    """
    Runs the Inno Setup installer executable.

    This function runs the Inno Setup installer executable generated by the buildInstaller function.
    It searches for the latest installer executable in the setup/Output directory.
    """

    installersPaths = glob.glob(f"{setupOutputPath}/*.exe")

    if installersPaths:
        installerPath = str(max(installersPaths, key=os.path.getmtime))
        command = [installerPath]

        runCommand(command=command, errorMessage="Error occurred while running installer")
    else:
        error = ColoredString("[!] installer path not found!").color(Color.Red)
        print(error, file=sys.stderr)
        sys.exit(1)


def splitArgs(args: str) -> List[str]:
    return args.split(" ")


def main() -> None:
    """
    Main entry point for the build script.

    This function parses the command-line arguments, updates version information,
    and runs the necessary build steps.
    It will clean the generated files, run PyInstaller, build the installer,
    install the application, reinstall the application, or run the installer based on the arguments provided.
    """

    parser = createArgParser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == CommandName.Help:
        parser.parse_args(splitArgs(f"{args.helpCommand} --help") if args.helpCommand else splitArgs("--help"))
        sys.exit(0)

    command = Command.fromArgs(args)

    print(f"[*] Building PidCat v{VERSION}...")

    print("[*] Updating version information...")
    updateVersions()

    match command:
        case Command.Clean():
            print("[*] Cleaning generated files...")
            clean()

        case Command.Build():
            print("[*] Running PyInstaller...")
            runPyInstaller()

        case Command.Rebuild():
            print("[*] Cleaning generated files...")
            clean()

            print("[*] Rebuilding executable...")
            runPyInstaller()

        case Command.BuildInstaller(isccPath):
            print("[*] Building installer...")
            runBuildInstaller(isccPath)

        case Command.BuildAll(isccPath):
            print("[*] Running PyInstaller...")
            runPyInstaller()

            print("[*] Building installer...")
            runBuildInstaller(isccPath)

        case Command.Install():
            print("[*] Running installer...")
            runInstaller()

        case Command.Reinstall(isccPath):
            print("[*] Cleaning generated files...")
            clean()

            print("[*] Rebuilding executable...")
            runPyInstaller()

            print("[*] Building installer...")
            runBuildInstaller(isccPath)

            print("[*] Running installer...")
            runInstaller()

    print("[✓] Build complete!")


if __name__ == "__main__":
    main()
