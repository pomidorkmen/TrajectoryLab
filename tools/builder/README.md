# TrajectoryLab Builder bootstrap executable

`main_windows.go` is the Windows x64 native bootstrapper. On first launch it installs a private CPython 3.14.10 runtime under `%LOCALAPPDATA%`, after verifying the official python.org installer SHA-256. It does not request administrator privileges and does not modify the system PATH.

After the Tk Builder main window has been fully created, the native setup window hands off and closes. If the Python UI fails before readiness, the setup window remains visible for diagnostics. The setup journal is stored at `%LOCALAPPDATA%\TrajectoryLabBuilder\bootstrap.log`; the Python UI log is stored beside it as `builder-ui.log`.

Build on a machine with Go 1.21+:

```powershell
$env:GOOS = "windows"
$env:GOARCH = "amd64"
$env:GO111MODULE = "off"
go build -trimpath -ldflags="-H windowsgui -s -w" -o build.exe ./tools/builder
```

Ordinary users do not need Go or a system-wide Python installation. First launch requires internet access to download the verified runtime.
