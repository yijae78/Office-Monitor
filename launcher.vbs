Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
strPython = "C:\Users\Ω≈¿Ã¿Á\AppData\Local\Programs\Python\Python313\pythonw.exe"
WshShell.CurrentDirectory = strDir
WshShell.Run """" & strPython & """ """ & strDir & "\main.py""", 0, False
