param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][string]$OutBase
)
# Capture only the given process's main window (PNG) and dump its UI Automation texts.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
if (-not ('WinCap' -as [type])) {
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class WinCap {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
}
'@
}
$process = Get-Process -Id $ProcessId
$process.Refresh()
$handle = $process.MainWindowHandle
if ($handle -eq [IntPtr]::Zero) { throw "Process $ProcessId has no main window yet." }
$rect = New-Object WinCap+RECT
[void][WinCap]::GetWindowRect($handle, [ref]$rect)
$width = $rect.Right - $rect.Left; $height = $rect.Bottom - $rect.Top
$bitmap = New-Object System.Drawing.Bitmap $width, $height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
[void][WinCap]::PrintWindow($handle, $hdc, 2)  # PW_RENDERFULLCONTENT
$graphics.ReleaseHdc($hdc); $graphics.Dispose()
$bitmap.Save("$OutBase.png", [System.Drawing.Imaging.ImageFormat]::Png); $bitmap.Dispose()

$root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$lines = @("WINDOW: " + $root.Current.Name + " (" + $width + "x" + $height + ")")
foreach ($element in $all) {
    $current = $element.Current
    $value = ''
    try {
        $pattern = $element.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
        $value = $pattern.Current.Value
    } catch {}
    if ($current.Name -or $value) {
        $lines += ($current.ControlType.ProgrammaticName -replace 'ControlType\.', '') + " | " + $current.AutomationId + " | " + $current.Name + $(if ($value) { " | value=" + $value } else { '' })
    }
}
$lines | Out-File -FilePath "$OutBase.txt" -Encoding utf8
$lines
