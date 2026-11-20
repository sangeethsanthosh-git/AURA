' AURA Desktop Assistant Launcher (Native Normal Window Visibility)
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

exePath = currentDir & "\AURA.exe"

If fso.FileExists(exePath) Then
    WshShell.Run """" & exePath & """", 1, False
Else
    batPath = currentDir & "\Launch_AURA_Desktop.bat"
    WshShell.Run """" & batPath & """", 1, False
End If
