//go:build windows

// TrajectoryLab Builder bootstrapper.
// This small native Win32 GUI installs a private Python runtime (per-user),
// verifies the official installer SHA-256, and opens the Tk Builder GUI.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"
)

const (
	appTitle        = "TrajectoryLab Builder"
	appVersion      = "0.4.2"
	pythonVersion   = "3.14.10"
	installerURL    = "https://www.python.org/ftp/python/3.14.10/python-3.14.10-amd64.exe"
	installerSHA256 = "92480239264744fe0386a1bd8275786fefa126e3129e56a68e22b52c73329965"
	wmCreate        = 0x0001
	wmDestroy       = 0x0002
	wmClose         = 0x0010
	wmCommand       = 0x0111
	wmSetFont       = 0x0030
	wmUser          = 0x0400
	pbmSetRange32   = wmUser + 6
	pbmSetPos       = wmUser + 2
	pbmSetBarColor  = wmUser + 9
	pbmSetBkColor   = wmUser + 1
	swShow          = 5
	swHide          = 0
	wsOverlapped    = 0x00000000
	wsCaption       = 0x00C00000
	wsSysMenu       = 0x00080000
	wsMinimizeBox   = 0x00020000
	wsVisible       = 0x10000000
	wsChild         = 0x40000000
	wsTabStop       = 0x00010000
	wsBorder        = 0x00800000
	wsVScroll       = 0x00200000
	wsHScroll       = 0x00100000
	esMultiline     = 0x0004
	esReadOnly      = 0x0800
	esAutoVScroll   = 0x0040
	bsPushButton    = 0x00000000
	idStart         = 101
	colorBtnFace    = 15
	defaultGUIFont  = 17
	iccProgress     = 0x00000020
	wmAppUpdate     = 0x8001
	wmAppStart      = 0x8002
)

type wndClassEx struct {
	Size       uint32
	Style      uint32
	WndProc    uintptr
	ClsExtra   int32
	WndExtra   int32
	Instance   syscall.Handle
	Icon       syscall.Handle
	Cursor     syscall.Handle
	Background syscall.Handle
	MenuName   *uint16
	ClassName  *uint16
	IconSmall  syscall.Handle
}

type point struct{ X, Y int32 }
type msg struct {
	Hwnd    syscall.Handle
	Message uint32
	WParam  uintptr
	LParam  uintptr
	Time    uint32
	Pt      point
}
type initCommonControlsEx struct {
	Size uint32
	ICC  uint32
}

var (
	kernel32           = syscall.NewLazyDLL("kernel32.dll")
	user32             = syscall.NewLazyDLL("user32.dll")
	comctl32           = syscall.NewLazyDLL("comctl32.dll")
	gdi32              = syscall.NewLazyDLL("gdi32.dll")
	pGetModuleHandle   = kernel32.NewProc("GetModuleHandleW")
	pRegisterClassEx   = user32.NewProc("RegisterClassExW")
	pCreateWindowEx    = user32.NewProc("CreateWindowExW")
	pDefWindowProc     = user32.NewProc("DefWindowProcW")
	pGetMessage        = user32.NewProc("GetMessageW")
	pTranslateMsg      = user32.NewProc("TranslateMessage")
	pDispatchMsg       = user32.NewProc("DispatchMessageW")
	pPostQuit          = user32.NewProc("PostQuitMessage")
	pPostMessage       = user32.NewProc("PostMessageW")
	pShowWindow        = user32.NewProc("ShowWindow")
	pUpdateWindow      = user32.NewProc("UpdateWindow")
	pSetWindowText     = user32.NewProc("SetWindowTextW")
	pSendMessage       = user32.NewProc("SendMessageW")
	pEnableWindow      = user32.NewProc("EnableWindow")
	pLoadCursor        = user32.NewProc("LoadCursorW")
	pGetStockObject    = gdi32.NewProc("GetStockObject")
	pLoadImage         = user32.NewProc("LoadImageW")
	pInitCommon        = comctl32.NewProc("InitCommonControlsEx")
	mainWindow         syscall.Handle
	bootstrapping      atomic.Bool
	statusControl      syscall.Handle
	progressControl    syscall.Handle
	logControl         syscall.Handle
	startControl       syscall.Handle
	instanceHandle     syscall.Handle
	className          = syscall.StringToUTF16Ptr("TrajectoryLabBuilderBootstrapWindow")
	windowCallback     = syscall.NewCallback(windowProc)
	uiLaunched         atomic.Bool
	bootstrapHandedOff atomic.Bool
	logMutex           sync.Mutex
	bootstrapLogPath   string
)

func utf16ptr(value string) *uint16 {
	ptr, _ := syscall.UTF16PtrFromString(value)
	return ptr
}

func createControl(class, text string, style uint32, x, y, width, height int, id uintptr) syscall.Handle {
	hwnd, _, _ := pCreateWindowEx.Call(
		0, uintptr(unsafe.Pointer(utf16ptr(class))), uintptr(unsafe.Pointer(utf16ptr(text))),
		uintptr(style|wsChild|wsVisible), uintptr(x), uintptr(y), uintptr(width), uintptr(height),
		uintptr(mainWindow), id, uintptr(instanceHandle), 0,
	)
	return syscall.Handle(hwnd)
}

func setText(hwnd syscall.Handle, text string) {
	if hwnd == 0 {
		return
	}
	pSetWindowText.Call(uintptr(hwnd), uintptr(unsafe.Pointer(utf16ptr(text))))
}

func redactLocalPaths(text string) string {
	roots := []string{os.Getenv("USERPROFILE"), os.Getenv("LOCALAPPDATA"), os.Getenv("APPDATA")}
	if home, err := os.UserHomeDir(); err == nil {
		roots = append(roots, home)
	}
	for _, root := range roots {
		if root == "" || root == string(os.PathSeparator) {
			continue
		}
		variants := []string{root, filepath.ToSlash(root), filepath.FromSlash(filepath.ToSlash(root))}
		for _, variant := range variants {
			if variant != "" {
				text = strings.ReplaceAll(text, variant, "<USER_LOCAL_PATH>")
				text = strings.ReplaceAll(text, strings.ToLower(variant), "<USER_LOCAL_PATH>")
				text = strings.ReplaceAll(text, strings.ToUpper(variant), "<USER_LOCAL_PATH>")
			}
		}
	}
	return text
}

func appendLog(text string) {
	text = redactLocalPaths(text)
	text = strings.ReplaceAll(text, "\r", "")
	text = strings.TrimRight(text, "\n")
	if bootstrapLogPath != "" {
		logMutex.Lock()
		if file, err := os.OpenFile(bootstrapLogPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600); err == nil {
			_, _ = fmt.Fprintf(file, "%s | %s\r\n", time.Now().Format(time.RFC3339), text)
			_ = file.Close()
		}
		logMutex.Unlock()
	}
	if logControl == 0 {
		return
	}
	uiText := text + "\r\n"
	pSendMessage.Call(uintptr(logControl), 0x00B1, ^uintptr(0), ^uintptr(0))                     // EM_SETSEL
	pSendMessage.Call(uintptr(logControl), 0x00C2, 0, uintptr(unsafe.Pointer(utf16ptr(uiText)))) // EM_REPLACESEL
}

func setProgress(percent int, status string) {
	if percent < 0 {
		percent = 0
	}
	if percent > 100 {
		percent = 100
	}
	if progressControl != 0 {
		pSendMessage.Call(uintptr(progressControl), pbmSetPos, uintptr(percent), 0)
	}
	setText(statusControl, status)
}

func windowProc(hwnd syscall.Handle, message uint32, wparam, lparam uintptr) uintptr {
	switch message {
	case wmCreate:
		mainWindow = hwnd
		font, _, _ := pGetStockObject.Call(defaultGUIFont)
		createControl("STATIC", "TrajectoryLab Builder", wsVisible, 22, 18, 450, 28, 0)
		createControl("STATIC", "v0.4.2  |  Preparing the private build environment", wsVisible, 22, 48, 500, 20, 0)
		createControl("STATIC", "INITIAL SETUP", wsVisible, 22, 86, 480, 20, 0)
		statusControl = createControl("STATIC", "Ready. The first run prepares the private Python runtime.", wsVisible, 22, 112, 650, 22, 0)
		progressControl = createControl("msctls_progress32", "", wsVisible, 22, 142, 650, 20, 0)
		pSendMessage.Call(uintptr(progressControl), pbmSetRange32, 0, 100)
		pSendMessage.Call(uintptr(progressControl), pbmSetBarColor, 0, 0x0098784B) // muted scientific blue, COLORREF BGR
		pSendMessage.Call(uintptr(progressControl), pbmSetBkColor, 0, 0x00F4F6F7)
		logControl = createControl("EDIT", "", wsVisible|wsBorder|wsVScroll|esMultiline|esReadOnly|esAutoVScroll, 22, 178, 650, 205, 0)
		startControl = createControl("BUTTON", "PREPARE AND OPEN BUILDER", wsVisible|wsTabStop|bsPushButton, 22, 405, 250, 34, idStart)
		createControl("STATIC", "Python installer is SHA-256 verified. Diagnostics: %LOCALAPPDATA%\\TrajectoryLabBuilder\\bootstrap.log", wsVisible, 22, 455, 650, 20, 0)
		for _, control := range []syscall.Handle{statusControl, progressControl, logControl, startControl} {
			if control != 0 {
				pSendMessage.Call(uintptr(control), wmSetFont, font, 1)
			}
		}
		return 0
	case wmCommand:
		if uint16(wparam) == idStart {
			if uiLaunched.Load() {
				pPostMessage.Call(uintptr(hwnd), wmClose, 0, 0)
				return 0
			}
			if !bootstrapping.Swap(true) {
				pEnableWindow.Call(uintptr(startControl), 0)
				go bootstrapRuntime()
			}
		}
		return 0
	case wmClose:
		if bootstrapping.Load() || (uiLaunched.Load() && !bootstrapHandedOff.Load()) {
			setText(statusControl, "Preparation is running. The setup window will close when the main Builder is ready.")
			return 0
		}
		pShowWindow.Call(uintptr(hwnd), swHide)
		pPostQuit.Call(0)
		return 0
	case wmDestroy:
		pPostQuit.Call(0)
		return 0
	case wmAppUpdate:
		return 0
	case wmAppStart:
		if !bootstrapping.Swap(true) {
			pEnableWindow.Call(uintptr(startControl), 0)
			setText(startControl, "PREPARING...")
			go bootstrapRuntime()
		}
		return 0
	}
	result, _, _ := pDefWindowProc.Call(uintptr(hwnd), uintptr(message), wparam, lparam)
	return result
}

func createMainWindow() error {
	appendLog(fmt.Sprintf("Starting native GUI bootstrap; GOOS=%s GOARCH=%s", runtime.GOOS, runtime.GOARCH))
	init := initCommonControlsEx{Size: uint32(unsafe.Sizeof(initCommonControlsEx{})), ICC: iccProgress}
	initResult, _, initErr := pInitCommon.Call(uintptr(unsafe.Pointer(&init)))
	appendLog(fmt.Sprintf("InitCommonControlsEx result=%d err=%v", initResult, initErr))
	instance, _, instanceErr := pGetModuleHandle.Call(0)
	instanceHandle = syscall.Handle(instance)
	appendLog(fmt.Sprintf("GetModuleHandleW instance=%#x err=%v", instance, instanceErr))
	if instanceHandle == 0 {
		return fmt.Errorf("GetModuleHandleW failed: %v", instanceErr)
	}
	var appIcon syscall.Handle
	if executable, err := os.Executable(); err == nil {
		iconPath := filepath.Join(filepath.Dir(executable), "trajectory_lab", "ui", "resources", "trajectorylab.ico")
		icon, _, iconErr := pLoadImage.Call(0, uintptr(unsafe.Pointer(utf16ptr(iconPath))), 1, 0, 0, 0x0010) // IMAGE_ICON | LR_LOADFROMFILE
		appIcon = syscall.Handle(icon)
		if appIcon == 0 {
			appendLog(fmt.Sprintf("Optional application icon could not be loaded: %s (%v)", iconPath, iconErr))
		} else {
			appendLog("Application icon loaded.")
		}
	}
	// IDC_ARROW is a resource identifier, not an HCURSOR value. Resolve it
	// with LoadCursorW before passing it to RegisterClassExW; using 32512
	// directly as a handle causes ERROR_INVALID_PARAMETER (87) on Windows.
	cursor, _, cursorErr := pLoadCursor.Call(0, uintptr(32512))
	appendLog(fmt.Sprintf("LoadCursorW(IDC_ARROW) handle=%#x err=%v", cursor, cursorErr))
	if cursor == 0 {
		return fmt.Errorf("LoadCursorW(IDC_ARROW) failed: %v", cursorErr)
	}
	class := wndClassEx{Size: uint32(unsafe.Sizeof(wndClassEx{})), WndProc: windowCallback, Instance: instanceHandle,
		Icon: appIcon, IconSmall: appIcon, Cursor: syscall.Handle(cursor), Background: syscall.Handle(colorBtnFace + 1), ClassName: className}
	appendLog(fmt.Sprintf("WNDCLASSEXW size=%d nativeSize=%d instance=%#x cursor=%#x background=%#x wndProc=%#x", class.Size, unsafe.Sizeof(class), class.Instance, class.Cursor, class.Background, class.WndProc))
	atom, _, err := pRegisterClassEx.Call(uintptr(unsafe.Pointer(&class)))
	appendLog(fmt.Sprintf("RegisterClassExW atom=%#x err=%v", atom, err))
	if atom == 0 && err != syscall.Errno(1410) {
		return fmt.Errorf("RegisterClassExW failed: %v (see %s)", err, bootstrapLogPath)
	}
	hwnd, _, err := pCreateWindowEx.Call(0, uintptr(unsafe.Pointer(className)), uintptr(unsafe.Pointer(utf16ptr(appTitle))),
		wsOverlapped|wsCaption|wsSysMenu|wsMinimizeBox|wsVisible, 100, 100, 710, 540, 0, 0, instance, 0)
	appendLog(fmt.Sprintf("CreateWindowExW hwnd=%#x err=%v", hwnd, err))
	if hwnd == 0 {
		return fmt.Errorf("CreateWindowExW failed: %v (see %s)", err, bootstrapLogPath)
	}
	mainWindow = syscall.Handle(hwnd)
	pShowWindow.Call(hwnd, swShow)
	pUpdateWindow.Call(hwnd)
	return nil
}

func localRoot() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	root := filepath.Dir(exe)
	if _, err := os.Stat(filepath.Join(root, "build.py")); err != nil {
		return "", fmt.Errorf("build.py was not found next to build.exe. Extract the complete TrajectoryLab archive and run build.exe from its root folder")
	}
	return root, nil
}

func cachePaths() (string, string, string, error) {
	local := os.Getenv("LOCALAPPDATA")
	if local == "" {
		return "", "", "", fmt.Errorf("LOCALAPPDATA is not defined; cannot prepare a per-user runtime")
	}
	base := filepath.Join(local, "TrajectoryLabBuilder")
	cache := filepath.Join(base, "cache")
	pythonDir := filepath.Join(base, "Python-"+pythonVersion)
	if err := os.MkdirAll(cache, 0o700); err != nil {
		return "", "", "", err
	}
	if err := os.MkdirAll(pythonDir, 0o700); err != nil {
		return "", "", "", err
	}
	return cache, pythonDir, filepath.Join(pythonDir, "python.exe"), nil
}

func downloadVerified(url, destination, expectedHash string) error {
	client := &http.Client{Timeout: 20 * time.Minute}
	request, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return err
	}
	request.Header.Set("User-Agent", "TrajectoryLab-Builder/0.4.2")
	response, err := client.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("download failed: HTTP %s", response.Status)
	}
	tmp := destination + ".download"
	file, err := os.Create(tmp)
	if err != nil {
		return err
	}
	hash := sha256.New()
	written, copyErr := io.Copy(io.MultiWriter(file, hash), response.Body)
	closeErr := file.Close()
	if copyErr != nil {
		os.Remove(tmp)
		return copyErr
	}
	if closeErr != nil {
		os.Remove(tmp)
		return closeErr
	}
	actual := hex.EncodeToString(hash.Sum(nil))
	if actual != expectedHash {
		os.Remove(tmp)
		return fmt.Errorf("Python installer SHA-256 mismatch; expected %s, got %s", expectedHash, actual)
	}
	if written < 10*1024*1024 {
		os.Remove(tmp)
		return fmt.Errorf("downloaded installer is unexpectedly small (%d bytes)", written)
	}
	return os.Rename(tmp, destination)
}

func bootstrapRuntime() {
	defer func() {
		if recovered := recover(); recovered != nil {
			fail(fmt.Errorf("Unexpected bootstrap panic: %v (see %s)", recovered, bootstrapLogPath))
		}
	}()
	appendLog("Checking local TrajectoryLab source files...")
	root, err := localRoot()
	if err != nil {
		fail(err)
		return
	}
	cache, pythonDir, pythonExe, err := cachePaths()
	if err != nil {
		fail(err)
		return
	}
	pythonw := filepath.Join(pythonDir, "pythonw.exe")
	if _, err := os.Stat(pythonExe); err != nil {
		installer := filepath.Join(cache, "python-"+pythonVersion+"-amd64.exe")
		if _, err := os.Stat(installer); err != nil {
			setProgress(5, "Downloading official Python runtime...")
			appendLog("Downloading Python " + pythonVersion + " from python.org...")
			if err := downloadVerified(installerURL, installer, installerSHA256); err != nil {
				fail(err)
				return
			}
		} else {
			appendLog("Cached Python installer found; verifying SHA-256...")
			// Re-hash cached file before running; cached installers are not implicitly trusted.
			file, err := os.Open(installer)
			if err != nil {
				fail(err)
				return
			}
			h := sha256.New()
			_, err = io.Copy(h, file)
			file.Close()
			if err != nil || hex.EncodeToString(h.Sum(nil)) != installerSHA256 {
				os.Remove(installer)
				fail(fmt.Errorf("cached Python installer failed SHA-256 validation"))
				return
			}
		}
		setProgress(72, "Installing private Python runtime (current user only)...")
		appendLog("Installer verified. Installing into the current user's LocalAppData...")
		cmd := exec.Command(installer, "/quiet", "InstallAllUsers=0", "TargetDir="+pythonDir, "Include_exe=1", "Include_pip=1", "Include_tcltk=1", "Include_test=0", "Include_launcher=0", "PrependPath=0", "Shortcuts=0")
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
		output, err := cmd.CombinedOutput()
		if err != nil {
			fail(fmt.Errorf("Python installation failed: %w\n%s", err, strings.TrimSpace(string(output))))
			return
		}
		if _, err := os.Stat(pythonExe); err != nil {
			fail(fmt.Errorf("Python installer completed but python.exe is missing"))
			return
		}
		appendLog("Private Python runtime installed successfully.")
	} else {
		appendLog("Private Python runtime already exists; reusing it.")
		setProgress(82, "Checking Python runtime...")
	}
	setProgress(90, "Checking Tkinter GUI support...")
	check := exec.Command(pythonExe, "-c", "import sys, tkinter; print(sys.version)")
	check.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	if output, err := check.CombinedOutput(); err != nil {
		fail(fmt.Errorf("Python runtime validation failed: %w\n%s", err, strings.TrimSpace(string(output))))
		return
	}
	if _, err := os.Stat(pythonw); err != nil {
		fail(fmt.Errorf("pythonw.exe is missing from the private runtime: %w", err))
		return
	}
	setProgress(96, "Launching graphical build interface...")
	appendLog("Opening TrajectoryLab Builder UI...")
	readyMarker := filepath.Join(filepath.Dir(bootstrapLogPath), "builder-ui-ready")
	_ = os.Remove(readyMarker)
	uiLogPath := filepath.Join(filepath.Dir(bootstrapLogPath), "builder-ui.log")
	uiLog, logErr := os.OpenFile(uiLogPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if logErr != nil {
		fail(fmt.Errorf("could not open Builder UI log %s: %w", uiLogPath, logErr))
		return
	}
	cmd := exec.Command(pythonw, filepath.Join(root, "build.py"))
	cmd.Dir = root
	cmd.Env = append(os.Environ(), "PYTHONNOUSERSITE=1", "PYTHONFAULTHANDLER=1", "PYTHONUNBUFFERED=1")
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	cmd.Stdout = uiLog
	cmd.Stderr = uiLog
	if err := cmd.Start(); err != nil {
		_ = uiLog.Close()
		fail(fmt.Errorf("could not launch the graphical Builder: %w", err))
		return
	}
	_ = uiLog.Close()
	uiLaunched.Store(true)
	setProgress(98, "Opening the main Builder window...")
	appendLog(fmt.Sprintf("Builder UI process started (PID %d). UI log: %s", cmd.Process.Pid, uiLogPath))
	bootstrapping.Store(false)
	go func() {
		err := cmd.Wait()
		uiLaunched.Store(false)
		if err != nil {
			appendLog(fmt.Sprintf("Builder UI process exited with error: %v. See %s", err, uiLogPath))
			if !bootstrapHandedOff.Load() {
				setText(statusControl, "Builder UI failed to start. See builder-ui.log.")
				pEnableWindow.Call(uintptr(startControl), 1)
			}
		} else {
			appendLog("Builder UI process closed.")
		}
	}()
	// Keep the bootstrap window only while the private runtime is prepared.
	// Once Tk has created its main window, hand off and close this window.
	go func() {
		ticker := time.NewTicker(150 * time.Millisecond)
		defer ticker.Stop()
		timeout := time.NewTimer(45 * time.Second)
		defer timeout.Stop()
		for {
			select {
			case <-ticker.C:
				if _, statErr := os.Stat(readyMarker); statErr == nil {
					appendLog("Main Builder window is ready; handing off the setup window.")
					bootstrapHandedOff.Store(true)
					pPostMessage.Call(uintptr(mainWindow), wmClose, 0, 0)
					return
				}
			case <-timeout.C:
				appendLog("Main Builder window did not signal readiness within 45 seconds; keeping diagnostics visible.")
				setText(statusControl, "Builder is still starting. Diagnostics remain available.")
				return
			}
		}
	}()
}

func fail(err error) {
	bootstrapping.Store(false)
	appendLog("ERROR: " + err.Error())
	setText(statusControl, "Setup failed. See the journal above.")
	setText(startControl, "TRY AGAIN")
	pEnableWindow.Call(uintptr(startControl), 1)
}

func initializeDiagnosticLog() {
	local := os.Getenv("LOCALAPPDATA")
	if local == "" {
		local = os.TempDir()
	}
	dir := filepath.Join(local, "TrajectoryLabBuilder")
	_ = os.MkdirAll(dir, 0o700)
	bootstrapLogPath = filepath.Join(dir, "bootstrap.log")
	appendLog("--- New Builder bootstrap session ---")
}

func mustExecutable() string {
	path, err := os.Executable()
	if err != nil {
		return "<unknown: " + err.Error() + ">"
	}
	return path
}

func main() {
	defer func() {
		if recovered := recover(); recovered != nil {
			appendLog(fmt.Sprintf("FATAL PANIC: %v", recovered))
		}
	}()
	initializeDiagnosticLog()
	appendLog(fmt.Sprintf("Process started. executable=%s args=%q", mustExecutable(), os.Args))
	if err := createMainWindow(); err != nil {
		appendLog("FATAL GUI STARTUP ERROR: " + err.Error())
		return
	}
	appendLog("Native bootstrap window created; starting runtime preparation automatically.")
	pPostMessage.Call(uintptr(mainWindow), wmAppStart, 0, 0)
	var message msg
	for {
		result, _, _ := pGetMessage.Call(uintptr(unsafe.Pointer(&message)), 0, 0, 0)
		if int32(result) <= 0 {
			break
		}
		pTranslateMsg.Call(uintptr(unsafe.Pointer(&message)))
		pDispatchMsg.Call(uintptr(unsafe.Pointer(&message)))
	}
}

// Compile with: GOOS=windows GOARCH=amd64 go build -ldflags="-H windowsgui" -o build.exe ./tools/builder
