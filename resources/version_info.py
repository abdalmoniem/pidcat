# type: ignore
# ruff: noqa: F821

# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
    ffi=FixedFileInfo(
        # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
        # Set not needed items to zero
    filevers=(2, 5, 4, 0),
    prodvers=(2, 5, 4, 0),
        # Contains a bitmask that specifies the valid bits 'flags'r
        mask=0x3F,
        # Contains a bitmask that specifies the Boolean attributes of the file.
        flags=0x0,
        # The operating system for which this file was designed.
        OS=0x4,
        # The general type of file.
        fileType=0x1,
        # The function of the file.
        subtype=0x0,
        # The date and time that the file was created.
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "040904b0",
                    [
                        StringStruct("CompanyName", "The PidCat Project"),
                        StringStruct("FileDescription", "ADB Logcat Console Viewer"),  # Matches "File description"
                        StringStruct("FileVersion", "2.5.4"),  # Matches "File version"
                        StringStruct("InternalName", "pidcat"),
                        StringStruct("LegalCopyright", "Copyright 2025, The PidCat Project"),  # Matches "Copyright"
                        StringStruct("OriginalFilename", "pidcat.exe"),
                        StringStruct("ProductName", "PidCat"),  # Matches "Product name"
                        StringStruct("ProductVersion", "2.5.4"),  # Matches "Product version"
                        StringStruct("Comments", "https://github.com/abdalmoniem/pidcat"),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)
