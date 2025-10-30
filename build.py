import os
import subprocess

# Get the directory where this script is located
scriptDir = os.path.dirname(os.path.abspath(__file__))

# Define all paths relative to the script's directory
projectRoot = scriptDir
iconPath = os.path.join(projectRoot, "resources", "icon.png")
versionPath = os.path.join(projectRoot, "resources", "version_info.py")
workPath = os.path.join(projectRoot, "generated", "build")
distPath = os.path.join(projectRoot, "generated", "dist")
specPath = os.path.join(projectRoot, "generated")
mainScript = os.path.join(projectRoot, "pidcat.py")

# Construct the PyInstaller command with absolute paths
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

# Run the PyInstaller command
subprocess.run(command, check=True)
