<div align="center">
   <img width="200" src="resources/icon.png" alt="PidCat Icon"/>
   <h1>📃 PidCat</h1>
   <p>A colorized Android logcat viewer for Windows with advanced filtering capabilities</p>

[![GPLv3 License](https://img.shields.io/badge/License-GPL%20v3-yellow.svg)](https://img.shields.io/badge/License-GPL%20v3-yellow.svg)
[![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)](https://www.python.org/)

[![Views](https://views.whatilearened.today/views/github/abdalmoniem/pidcat.svg)](https://github.com/abdalmoniem/pidcat)
[![GitHub Release](https://img.shields.io/github/v/release/abdalmoniem/pidcat)](https://github.com/abdalmoniem/pidcat/releases/latest)
[![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/abdalmoniem/pidcat/total?logo=github&logoSize=auto&label=GitHub%20Downloads)](https://github.com/abdalmoniem/pidcat/releases/latest)

</div>

## 🎯 Overview

PidCat is an enhanced Android logcat viewer originally created by Jake Wharton for the Android Open Source Project. This Windows-optimized fork adds modern features including VT100 color support, advanced tag filtering with substring matching, and improved column formatting.

PidCat filters logcat output by application package name, colorizes the output for better readability, and provides powerful filtering options to help you focus on the logs that matter.

---

## 📸 Screenshots

<div align=center>
    <img
        src="assets/screenshot_1.png"
        alt="PidCat Screenshot 01"
        width="800"/>
    <br/>
    <br/>
    <br/>
    <img 
        src="assets/screenshot_2.png"
        alt="PidCat Screenshot 02"
        width="800"/>
</div>

---

## ✨ Features

### Core Features

- 🎨 **Colorized Output** - Different colors for log levels, tags, and packages
- 📦 **Package Filtering** - Show logs only from specific app packages
- 🏷️ **Tag Filtering** - Filter by log tags with substring matching support
- 🔍 **Regex Support** - Use regular expressions for advanced tag filtering
- 📊 **Process Tracking** - Automatically tracks process starts and deaths
- 💻 **Windows VT100 Support** - Native color support on Windows 10/11

### Advanced Filtering

- **Multiple Tag Support** - Filter by multiple tags simultaneously
- **Substring Matching** - Match tags containing specific strings (e.g., `-t Timeout` matches `TimeoutJob$update`)
- **Regex Patterns** - Use regex special characters for complex filtering
- **Comma-Separated Tags** - Specify multiple tags in a single argument: `-t Tag1,Tag2,Tag3`
- **Tag Ignoring** - Exclude specific tags from output with `-i`
- **Log Level Filtering** - Show only logs at or above a specific level

### Display Options

- **Customizable Column Widths** - Adjust package name and tag column widths
- **Smart Tag Display** - Automatically shows tags when filtering
- **Truncation** - Long tags are truncated to fit column width
- **Process Notifications** - Visual indicators for process lifecycle events

### Output Options

- **File Output** - Save logs to a file with `-o`
- **Color Disable** - Remove colors for piping or parsing with `-n`
- **Current App Mode** - Automatically filter by the currently running app

---

## 📥 Installation

### Windows Installer

1. Download the latest installer from [Releases](https://github.com/abdalmoniem/pidcat/releases)
2. Run `PidCat_<datetime>.exe`
3. Follow the installation wizard
4. The installer will automatically add PidCat to your system PATH

### From Source

**Prerequisites:**

- Python 3.8 or higher
- Android SDK with ADB in PATH
- uv
- Git (optional)

**Installation Steps:**

```bash
# Clone the repository
git clone https://github.com/abdalmoniem/pidcat.git
cd pidcat

# Install dependencies (if any)
uv sync

# Run directly
uv run pidcat.py com.example.app
```

---

## 🚀 Usage

### Basic Usage

```bash
# Filter logs by package name
pidcat com.example.myapp

# Filter by multiple packages
pidcat com.example.app1 com.example.app2

# Show all logs (no package filtering)
pidcat -a

# Filter by currently running app
pidcat --current
```

### Advanced Filtering

```bash
# Filter by specific tags
pidcat com.example.app -t MyTag -t AnotherTag

# Filter by tags with substring matching
pidcat com.example.app -t Timeout
# Matches: TimeoutJob, TimeoutJob$update, NetworkTimeout, etc.

# Use comma-separated tags
pidcat com.example.app -t MyTag,AnotherTag,ThirdTag

# Combine with log level filtering
pidcat com.example.app -t MyTag -l D
# Shows only Debug level and above

# Ignore specific tags
pidcat com.example.app -i ChattyCrap -i Noisy

# Use regex for complex patterns
pidcat com.example.app -t "^Network.*"
# Matches: NetworkManager, NetworkClient, etc.
```

### Command Line Options

```
positional arguments:
  package               Application package name(s)

optional arguments:
  -h, --help            Show this help message and exit
  -v, --version         Print the version number and exit

Filtering Options:
  -a, --all             Print all log messages (disables package filter)
  --current             Filter logcat by current running app
  -t TAG, --tag TAG     Filter output by specified tag(s)
  -i TAG, --ignore-tag TAG
                        Filter output by ignoring specified tag(s)
  -l LEVEL, --min-level LEVEL
                        Minimum level to be displayed (V/D/I/W/E/F)
  -r REGEX, --regex REGEX
                        Print only when matches REGEX

Display Options:
  -m M, --tag-width N   Width of log tag column (default: 20)
  -n N, --package-width N
                        Width of package/process name column (default: 20)
  -p, --show-package    Show package/process name (default: True)
  --always-display-tags Always display the tag name
  --color-gc            Color garbage collection messages
  -n, --no-color        Disable colors

Device Options:
  -s SERIAL, --serial SERIAL
                        Device serial number (adb -s option)
  -d, --device          Use first device for log input (adb -d option)
  -e, --emulator        Use first emulator for log input (adb -e option)

Output Options:
  -o FILE, --output FILE
                        Output filename
  -k, --keep            Keep the entire log before running
```

---

## 📚 Examples

### Example 1: Basic Package Filtering

```bash
pidcat com.example.myapp
```

Shows all logs from `com.example.myapp` with colorized output.

### Example 2: Multiple Tags with Custom Width

```bash
pidcat com.example.myapp -t Network -t Database -m 25 -n 30
```

Shows logs with `Network` or `Database` tags, with 30-char package column and 25-char tag column.

### Example 3: Debug Level Only

```bash
pidcat com.example.myapp -l D
```

Shows only Debug, Info, Warning, Error, and Fatal logs (filters out Verbose).

### Example 4: Save to File Without Colors

```bash
pidcat com.example.myapp -o logs.txt -n
```

Saves logs to `logs.txt` without color codes.

### Example 5: Current App with Specific Tags

```bash
pidcat --current -t MainActivity -t ServiceManager --always-display-tags
```

Monitors the currently running app, showing only MainActivity and ServiceManager tags.

### Example 6: Complex Regex Filtering

```bash
pidcat com.example.myapp -t "^(Network|Http).*Client$"
```

Matches tags like `NetworkClient`, `HttpClient`, `NetworkSocketClient`, etc.

### Example 7: Ignore Verbose Tags

```bash
pidcat com.example.myapp -i Chatty -i Verbose -l I
```

Shows Info level and above, ignoring tags containing "Chatty" or "Verbose".

---

## 🔨 Building from Source

### Prerequisites

- uv
- Python 3.8+
- PyInstaller
- Inno Setup (for Windows installer)

### Build Steps

1. **Update Version** - Edit `build.py` and set the `VERSION` variable

2. **Run Build Script**

   ```bash
   uv run build.py
   ```

3. **Output Locations**
   - Executable: `generated/dist/PidCat.exe`
   - Installer: `setup/Output/PidCat_<datetime>.exe`

### Build Script Features

- Automatically updates version in all files
- Generates PyInstaller executable
- Creates Inno Setup installer with datetime stamp
- Updates version_info.py for Windows file properties

---

## ⚙️ Configuration

### Tag Filtering Behavior

By default, tag filters use **substring matching**:

```bash
-t Timeout
```

Matches any tag containing "Timeout": `TimeoutJob`, `NetworkTimeout`, `TimeoutManager`, etc.

To use **exact matching** or **regex patterns**, include regex special characters:

```bash
-t "^TimeoutJob$"  # Exact match only
-t "Timeout.*Job"  # Regex pattern
```

### Column Width Adjustment

Adjust column widths to fit your terminal:

```bash
pidcat com.example.app -m 25 -n 30
```

- Package column: 25 characters
- Tag column: 30 characters
- Packages/Tags longer than width are truncated

### Color Customization

Colors are automatically allocated to tags and packages using an LRU cache. Predefined colors exist for common Android tags like `ActivityManager`, `DEBUG`, etc.

---

## 🐛 Troubleshooting

### Colors Not Showing on Windows

**Problem:** No colors appear in the output.

**Solution:**

- Ensure you're on Windows 10/11
- Run from Windows Terminal or PowerShell
- Check that `-n` (no-color) flag is not set

### ADB Not Found

**Problem:** `adb: command not found` or similar error.

**Solution:**

- Add Android SDK platform-tools to your PATH
- Or specify full path to adb in environment

### No Logs Appearing

**Problem:** PidCat runs but shows no output.

**Solution:**

1. Verify your app is running: `adb shell ps | grep your.package.name`
2. Check package name is correct (case-sensitive)
3. Try with `-a` flag to see all logs
4. Ensure device is connected: `adb devices`

### Tag Filter Not Working

**Problem:** Using `-t` but not seeing expected logs.

**Solution:**

- Tags use substring matching by default
- Check tag names in logcat: `adb logcat -v brief`
- Tags are case-sensitive
- Use `--always-display-tags` to verify which tags are shown

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. **Fork the Repository**
2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Commit Your Changes**
   ```bash
   git commit -m 'Add some amazing feature'
   ```
4. **Push to the Branch**
   ```bash
   git push origin feature/amazing-feature
   ```
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guide
- Use type hints where appropriate
- Add comments for complex logic
- Test on Windows 10/11
- Update documentation for new features

---

## 📄 License

This project is licensed under the GNU General Public License 3.0 - see the [LICENSE](LICENSE.md) file for details.

```
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.
```

---

## 🙏 Credits

### Original Author

- **[Jake Wharton](https://github.com/JakeWharton)** - Original [PidCat](https://github.com/JakeWharton/pidcat) creator

### Windows Fork Maintainer

- **AbdElMoniem ElHifnawy** - Windows optimizations and enhancements
- GitHub: [@abdalmoniem](https://github.com/abdalmoniem)
- Website: [abdalmoniem.github.io](https://abdalmoniem.github.io)

### Contributors

Thanks to all contributors who have helped improve PidCat!

---

## 🔗 Links

- **GitHub Repository:** [github.com/abdalmoniem/pidcat](https://github.com/abdalmoniem/pidcat)
- **Issue Tracker:** [github.com/abdalmoniem/pidcat/issues](https://github.com/abdalmoniem/pidcat/issues)
- **Original PidCat:** [github.com/JakeWharton/pidcat](https://github.com/JakeWharton/pidcat)

---

<div align="center">

**Made with ❤️ for Android Developers**

If you find PidCat useful, please ⭐ star the repository!

</div>
