Set WshShell = CreateObject("WScript.Shell")
strStartup = WshShell.SpecialFolders("Startup")
strLinkPath = strStartup & "\WisperAutoStart.lnk"
strTarget = "C:\Wisper\Frontend\WisperGUI.bat"
strWorkDir = "C:\Wisper\Frontend"

Set oLink = WshShell.CreateShortcut(strLinkPath)
oLink.TargetPath = strTarget
oLink.WorkingDirectory = strWorkDir
oLink.WindowStyle = 7 ' Minimized (though the bat file handles hiding itself)
oLink.Description = "Start Wisper GUI on login"
oLink.IconLocation = "C:\Wisper\Frontend\assets\asteroid.ico"
oLink.Save

WScript.Echo "Wisper successfully added to Startup!" & vbCrLf & "Location: " & strLinkPath
