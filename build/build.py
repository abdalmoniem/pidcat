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

from utils.colored import Color, ColoredString

sys_stdout = cast(TextIOWrapper, sys.stdout)
sys_stderr = cast(TextIOWrapper, sys.stderr)

sys_stdout.reconfigure(encoding="utf-8")
sys_stderr.reconfigure(encoding="utf-8")

VERSION = "2.6.1"

TAB_WIDTH = 4
TAB_CHAR = " " * TAB_WIDTH

IS_WINDOWS = sys.platform == "win32"

script_dir = str(Path(__file__).parent)
icon_path = str(Path(script_dir).joinpath("resources", "icon.png"))
version_path = str(Path(script_dir).joinpath("resources", "version_info.py"))
work_path = str(Path(script_dir).joinpath("generated", "build"))
dist_path = str(Path(script_dir).joinpath("generated", "dist"))
generated_path = str(Path(script_dir).joinpath("generated"))
main_script = str(Path(script_dir).parent.joinpath("main.py"))
setup_script_path = str(Path(script_dir).joinpath("setup"))
setup_output_path = str(Path(setup_script_path).joinpath("Output"))
setup_script = str(Path(setup_script_path).joinpath("setup.iss"))
version_info_script = str(Path(script_dir).joinpath("resources", "version_info.py"))


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
            iscc_path: Optional[str] = None

        @dataclass
        class BuildAll:
            iscc_path: Optional[str] = None

        @dataclass
        class Install:
            pass

        @dataclass
        class Reinstall:
            iscc_path: Optional[str] = None

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
    def from_args(args: argparse.Namespace) -> CommandType:
        match CommandName(args.command):
            case CommandName.Clean:
                return Command.Clean()
            case CommandName.Build:
                return Command.Build()
            case CommandName.Rebuild:
                return Command.Rebuild()
            case CommandName.BuildInstaller:
                return Command.BuildInstaller(args.iscc_path)
            case CommandName.BuildAll if IS_WINDOWS:
                return Command.BuildAll(args.iscc_path)
            case CommandName.Install if IS_WINDOWS:
                return Command.Install()
            case CommandName.Reinstall if IS_WINDOWS:
                return Command.Reinstall(args.iscc_path)
            case _:
                raise ValueError(f"Unknown Command '{args.command}'")


def get_arg_parser() -> argparse.ArgumentParser:
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
            dest="iscc_path",
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
            dest="iscc_path",
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
            dest="iscc_path",
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


def update_main_script_version() -> None:
    """
    Updates the version string in the main script file.

    This function reads the main script file, updates the version string,
    and writes the updated content back to the file.
    """

    with open(file=main_script, mode="r+", encoding="utf-8") as fd:
        lines = fd.readlines()

        fd.seek(0)
        fd.truncate()

        for line in lines:
            if line.strip().startswith("VERSION"):
                fd.write(f'VERSION = "{VERSION}"\n')
            else:
                fd.write(line)


def update_setup_script_version() -> None:
    """
    Updates the version string in the setup script file.

    This function reads the setup script file, updates the version string,
    and writes the updated content back to the file.
    """

    with open(file=setup_script, mode="r+", encoding="utf-8") as fd:
        lines = fd.readlines()

        fd.seek(0)
        fd.truncate()

        for line in lines:
            if line.strip().startswith("#define AppVersion"):
                fd.write(f'#define AppVersion "{VERSION}"\n')
            else:
                fd.write(line)


def update_version_info_script_version() -> None:
    """
    Updates the version string in the version info script file.

    This function reads the version info script file, updates the version string,
    and writes the updated content back to the file.
    """

    version_parts = VERSION.split(".")
    version_tuple = tuple(int(versionPart) for versionPart in version_parts) + (0,) * (4 - len(version_parts))

    with open(file=version_info_script, mode="r+", encoding="utf-8") as fd:
        lines = fd.readlines()

        fd.seek(0)
        fd.truncate()

        for line in lines:
            if "filevers=" in line:
                fd.write(f"{TAB_CHAR}filevers={version_tuple},\n")
            elif "prodvers=" in line:
                fd.write(f"{TAB_CHAR}prodvers={version_tuple},\n")
            elif 'StringStruct("FileVersion"' in line:
                fd.write(f'{TAB_CHAR * 6}StringStruct("FileVersion", "{VERSION}"),  # Matches "File version"\n')
            elif 'StringStruct("ProductVersion"' in line:
                fd.write(f'{TAB_CHAR * 6}StringStruct("ProductVersion", "{VERSION}"),  # Matches "Product version"\n')
            else:
                fd.write(line)


def update_versions() -> None:
    update_main_script_version()
    update_setup_script_version()
    update_version_info_script_version()


def clean() -> None:
    """
    Cleans up generated files and directories.

    This function deletes the generated files and directories, without throwing an error if they do not exist.
    """
    shutil.rmtree(path=generated_path, ignore_errors=True)
    shutil.rmtree(path=setup_output_path, ignore_errors=True)


def run_command(command: list[str], err_msg: str | None = None) -> None:
    """
    Runs a command and prints its output.

    Arguments:
        command (list[str]): The command to run.
        error_message (str | None, optional): An error message to print if the command fails. Defaults to None.
    """

    stderr = []

    def stream_reader(pipe: TextIO, file: TextIO) -> None:
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

    def print_exception(message: str) -> None:
        """
        Prints an error message to sys.stderr, with optional colorization.

        If errorMessage is provided, it is prefixed to the error message.

        Arguments:
            message (str): The error message to print.
        """

        if err_msg:
            error = ColoredString(f"[!] {err_msg}: {message}").color(Color.Red)
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

        stdout_thread = threading.Thread(target=stream_reader, args=(pid.stdout, sys.stdout))
        stderr_thread = threading.Thread(target=stream_reader, args=(pid.stderr, sys.stderr))

        stdout_thread.start()
        stderr_thread.start()

        pid.wait()

        stdout_thread.join()
        stderr_thread.join()

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

        print_exception(str(ex))

        for line in ex.stderr.splitlines():
            error = ColoredString(f"[!] {line}").color(Color.Red)
            print(error, file=sys.stderr)

        sys.exit(ex.returncode)


def run_py_installer() -> None:
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
        f"--workpath={work_path}",
        f"--distpath={dist_path}",
        f"--specpath={generated_path}",
        f"--icon={icon_path}",
        f"--version-file={version_path}",
        "--name=pidcat",
        main_script,
    ]

    run_command(command=command, err_msg="Error occurred while building executable")


def run_build_installer(iscc_path: Optional[str] = None) -> None:
    """
    Builds the Inno Setup installer.

    This function runs the Inno Setup compiler command with the necessary arguments to build the installer.

    Arguments:
        iscc_path (str): path to the Inno Setup Compiler (iscc.exe).
    """

    iscc_path = "iscc" if not iscc_path else iscc_path
    command = [iscc_path, setup_script]

    try:
        run_command(command=command, err_msg="Error occurred while building installer")
    except FileNotFoundError as ex:
        erroneious_path = iscc_path

        err_msg = f"[!] Error occurred while building installer: {ex}: '{erroneious_path}'"
        print(ColoredString(err_msg).color(Color.Red), file=sys.stderr)

        err_msg = (
            f"[!] Inno Setup Compiler (iscc) not found at path: '{erroneious_path}'. "
            "Please install Inno Setup and ensure 'iscc' is in your system PATH, "
            "or provide the correct path using the --iscc-path argument."
        )

        print(ColoredString(err_msg).color(Color.Red), file=sys.stderr)

        sys.exit(ex.errno)


def run_installer() -> None:
    """
    Runs the Inno Setup installer executable.

    This function runs the Inno Setup installer executable generated by the buildInstaller function.
    It searches for the latest installer executable in the setup/Output directory.
    """

    installers_paths = glob.glob(f"{setup_output_path}/*.exe")

    if installers_paths:
        installer_path = str(max(installers_paths, key=os.path.getmtime))
        command = [installer_path]

        run_command(command=command, err_msg="Error occurred while running installer")
    else:
        error = ColoredString("[!] installer path not found!").color(Color.Red)
        print(error, file=sys.stderr)
        sys.exit(1)


def split_args(args: str) -> List[str]:
    return args.split(" ")


def main() -> None:
    """
    Main entry point for the build script.

    This function parses the command-line arguments, updates version information,
    and runs the necessary build steps.
    It will clean the generated files, run PyInstaller, build the installer,
    install the application, reinstall the application, or run the installer based on the arguments provided.
    """

    parser = get_arg_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == CommandName.Help:
        parser.parse_args(split_args(f"{args.helpCommand} --help") if args.helpCommand else split_args("--help"))
        sys.exit(0)

    command = Command.from_args(args)

    print(f"[*] Building PidCat v{VERSION}...")

    print("[*] Updating version information...")
    update_versions()

    match command:
        case Command.Clean():
            print("[*] Cleaning generated files...")
            clean()

        case Command.Build():
            print("[*] Running PyInstaller...")
            run_py_installer()

        case Command.Rebuild():
            print("[*] Cleaning generated files...")
            clean()

            print("[*] Rebuilding executable...")
            run_py_installer()

        case Command.BuildInstaller(iscc_path):
            print("[*] Building installer...")
            run_build_installer(iscc_path)

        case Command.BuildAll(iscc_path):
            print("[*] Running PyInstaller...")
            run_py_installer()

            print("[*] Building installer...")
            run_build_installer(iscc_path)

        case Command.Install():
            print("[*] Running installer...")
            run_installer()

        case Command.Reinstall(iscc_path):
            print("[*] Cleaning generated files...")
            clean()

            print("[*] Rebuilding executable...")
            run_py_installer()

            print("[*] Building installer...")
            run_build_installer(iscc_path)

            print("[*] Running installer...")
            run_installer()

    print("[✓] Build complete!")


if __name__ == "__main__":
    main()
