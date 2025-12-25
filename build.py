import os
import subprocess


__version__ = "2.5.3"

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


def updateMainScriptVersion():
    with open(mainScript, "r+") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if line.strip().startswith("__version__"):
                fileDescriptor.write(f'__version__ = "{__version__}"\n')
            else:
                fileDescriptor.write(line)


def updateSetupScriptVersion():
    with open(setupScript, "r+") as fileDescriptor:
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
    versionTuple = tuple(int(v) for v in versionParts) + (0,) * (4 - len(versionParts))
    with open(versionInfoScript, "r+") as fileDescriptor:
        lines = fileDescriptor.readlines()

        fileDescriptor.seek(0)
        fileDescriptor.truncate()

        for line in lines:
            if "filevers=" in line:
                fileDescriptor.write(f'{TAB_CHAR}filevers={versionTuple},\n')
            elif "prodvers=" in line:
                fileDescriptor.write(f'{TAB_CHAR}prodvers={versionTuple},\n')
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

    subprocess.run(command, check=True)


def main():
    updateMainScriptVersion()
    updateSetupScriptVersion()
    updateVersionInfoScriptVersion()

    runPyInstaller()

    print("Build complete.")


if __name__ == "__main__":
    main()
