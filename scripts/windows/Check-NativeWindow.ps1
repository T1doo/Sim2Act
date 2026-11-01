param([Parameter(Mandatory=$true)][string]$Package,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$probeRoot=[IO.Path]::GetFullPath($Output)
if(Test-Path -LiteralPath $probeRoot){throw 'New probe output required; existing data preserved.'}
[void][IO.Directory]::CreateDirectory($probeRoot)
$payload=Join-Path $probeRoot 'payload';[void][IO.Directory]::CreateDirectory($payload)
"SIM2ACT_WINDOW_PAYLOAD=$payload" | Add-Content $env:GITHUB_ENV -Encoding UTF8
$report=[ordered]@{source_commit='042ab21c4fa9c7e5ba70c4e2877fb7060d962422';test_commit=$env:GITHUB_SHA;status='STARTED';model_requests=0;browser_launched=$false;starts=@()}
$desktopProcess=$null;$appRoot=$null;$clock=[Diagnostics.Stopwatch]::StartNew()
function Save-Report { $report | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $payload 'report.json') -Encoding UTF8 }
function Budget { if($clock.Elapsed.TotalSeconds -gt 115){throw 'Finite ordinary window probe budget exhausted.'} }
function Events([string]$Kind) {
    $log=Join-Path $appRoot 'desktop.log'
    if(-not(Test-Path -LiteralPath $log)){return}
    foreach($line in Get-Content -LiteralPath $log -Encoding UTF8){
        $offset=$line.IndexOf('{');if($offset -lt 0){continue}
        try{$item=$line.Substring($offset)|ConvertFrom-Json}catch{continue}
        if($null -ne $item.PSObject.Properties['event'] -and $item.event -ceq $Kind){$item}
    }
}
function Start-Window {
    Budget
    $before=@(Events 'SYNTHETIC_WORKSPACE_READY').Count
    $info=[Diagnostics.ProcessStartInfo]::new((Join-Path $appRoot 'Sim2Act.exe'))
    $info.UseShellExecute=$false;$info.WorkingDirectory=$appRoot
    foreach($name in @('GITHUB_TOKEN','GH_TOKEN','ACTIONS_RUNTIME_TOKEN','ACTIONS_ID_TOKEN_REQUEST_TOKEN')){$info.EnvironmentVariables.Remove($name)}
    $info.EnvironmentVariables['SIM2ACT_MODEL_MODE']='mock';$info.EnvironmentVariables['SIM2ACT_LIVE_ENABLED']='false'
    $info.EnvironmentVariables['INTERN_API_TOKEN']='';$info.EnvironmentVariables['SIM2ACT_INTERN_TOKEN']=''
    $script:desktopProcess=[Diagnostics.Process]::Start($info)
    $item=[ordered]@{pid=$desktopProcess.Id;session=$desktopProcess.SessionId};$script:report.starts+=@($item);Save-Report
    $until=[DateTime]::UtcNow.AddSeconds(30)
    do {
        Budget;$desktopProcess.Refresh()
        if($desktopProcess.HasExited){throw 'Native desktop exited before usable window; no restart.'}
        $ready=@(Events 'SYNTHETIC_WORKSPACE_READY')
        if($ready.Count -gt $before -and $desktopProcess.MainWindowHandle -ne [IntPtr]::Zero){
            if($desktopProcess.MainWindowTitle -cne 'Sim2Act 工作台'){throw 'Unexpected native window title.'}
            $item['ready']=$ready[-1];$item['hwnd']=$desktopProcess.MainWindowHandle.ToInt64();Save-Report
            return [Windows.Automation.AutomationElement]::FromHandle($desktopProcess.MainWindowHandle)
        }
        Start-Sleep -Milliseconds 200
    } while([DateTime]::UtcNow -lt $until)
    throw 'Native window/actual READY unavailable; no runtime or security fallback.'
}
function Find-Control($Window,[string]$Name,$Type,[int]$Seconds=8) {
    $until=[DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        Budget
        $condition=[Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::NameProperty,$Name)
        if($null -ne $Type){$condition=[Windows.Automation.AndCondition]::new($condition,
            [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,$Type))}
        $item=$Window.FindFirst([Windows.Automation.TreeScope]::Descendants,$condition)
        if($null -ne $item -and -not $item.Current.IsOffscreen -and $item.Current.IsEnabled){return $item}
        Start-Sleep -Milliseconds 150
    } while([DateTime]::UtcNow -lt $until)
    throw "Required actual UIA control unavailable: $Name"
}
function Invoke-Control($Control) {([Windows.Automation.InvokePattern]$Control.GetCurrentPattern([Windows.Automation.InvokePattern]::Pattern)).Invoke()}
function Login($Window) {
    $token=Find-Control $Window '本机访问令牌' ([Windows.Automation.ControlType]::Edit)
    ([Windows.Automation.ValuePattern]$token.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern)).SetValue('public-synthetic-blank-workspace')
    Invoke-Control (Find-Control $Window '连接' ([Windows.Automation.ControlType]::Button))
    [void](Find-Control $Window '切换身份' ([Windows.Automation.ControlType]::Button))
    [void](Find-Control $Window '研究工作台' $null)
}
function Capture([string]$Name) {
    Budget;$desktopProcess.Refresh();$handle=$desktopProcess.MainWindowHandle
    if(-not [NativeWindowProbe]::SetForegroundWindow($handle)){throw 'Foreground capture unavailable; no focus bypass.'}
    Start-Sleep -Milliseconds 300
    if([NativeWindowProbe]::GetForegroundWindow() -ne $handle){throw 'Own native window is not foreground.'}
    $rect=[NativeWindowProbe+Rect]::new();if(-not[NativeWindowProbe]::GetWindowRect($handle,[ref]$rect)){throw 'Window rectangle unavailable.'}
    $bounds=[Windows.Forms.SystemInformation]::VirtualScreen
    if($rect.Left -lt $bounds.Left -or $rect.Top -lt $bounds.Top -or $rect.Right -gt $bounds.Right -or $rect.Bottom -gt $bounds.Bottom){throw 'Own window extends outside actual desktop; no clipped screenshot acceptance.'}
    $width=$rect.Right-$rect.Left;$height=$rect.Bottom-$rect.Top
    if($width -lt 900 -or $height -lt 600){throw 'Actual window viewport too small.'}
    $bitmap=[Drawing.Bitmap]::new($width,$height);$graphics=[Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen($rect.Left,$rect.Top,0,0,$bitmap.Size)
        $colors=[Collections.Generic.HashSet[int]]::new()
        for($x=20;$x -lt $width;$x+=50){for($y=20;$y -lt $height;$y+=50){[void]$colors.Add($bitmap.GetPixel($x,$y).ToArgb())}}
        if($colors.Count -lt 8){throw 'Captured pixels are blank/unusable; not a page proof.'}
        $bitmap.Save((Join-Path $payload $Name),[Drawing.Imaging.ImageFormat]::Png)
        $script:report[$Name]=@{width=$width;height=$height;left=$rect.Left;top=$rect.Top;distinct_sample_colors=$colors.Count}
    } finally {$graphics.Dispose();$bitmap.Dispose()}
}
function Close-Window {
    Budget
    $item=$report.starts[-1]
    if(-not $desktopProcess.CloseMainWindow()){throw 'Normal own-window close unavailable; no kill.'}
    if(-not $desktopProcess.WaitForExit(20000)){throw 'Native exit unconfirmed; lock preserved, no restart.'}
    $exit=@(Events 'DESKTOP_EXIT');$stop=@(Events 'SYNTHETIC_WORKSPACE_STOPPED')
    if($desktopProcess.ExitCode -ne 0 -or $exit.Count -lt $report.starts.Count -or $stop.Count -lt $report.starts.Count){throw 'Missing real native/backend exit confirmation.'}
    if($exit[-1].exitcode -ne 0 -or -not$exit[-1].receipt_verified -or -not$exit[-1].ready_seen -or
       -not$stop[-1].clean -or -not$stop[-1].data_preserved -or -not$stop[-1].worker_stopped -or $stop[-1].worker_id -cne $item.ready.worker_id -or
       (Test-Path -LiteralPath (Join-Path $appRoot 'desktop-running.lock'))){throw 'Native STOPPED/exit/lock mismatch.'}
    $item['exitcode']=$desktopProcess.ExitCode;$item['receipt']=$stop[-1];$item['native_exit']=$exit[-1];Save-Report
    $script:desktopProcess=$null
}
try {
    Save-Report
    if((Get-FileHash -LiteralPath $Package -Algorithm SHA256).Hash.ToLowerInvariant() -cne 'cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027'){throw 'Exact accepted full package required.'}
    Add-Type -AssemblyName System.Windows.Forms,System.Drawing,UIAutomationClient,UIAutomationTypes
    $report['session']=[Diagnostics.Process]::GetCurrentProcess().SessionId
    $report['user_interactive']=[Environment]::UserInteractive
    $report['screen']=@{width=[Windows.Forms.Screen]::PrimaryScreen.Bounds.Width;height=[Windows.Forms.Screen]::PrimaryScreen.Bounds.Height}
    if(-not$report.user_interactive -or $report.session -eq 0 -or $report.screen.width -lt 1024 -or $report.screen.height -lt 700){throw 'Existing interactive Windows desktop unavailable; no session/display setter.'}
    # Read the same installed stable-runtime registry/path boundary as the original host.
    # Missing runtime stops before EXE launch; no installer, environment override or modal fallback.
    $runtimeFound=$null
    foreach($name in @('WEBVIEW2_BROWSER_EXECUTABLE_FOLDER','WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS','WEBVIEW2_USER_DATA_FOLDER')){if(-not[string]::IsNullOrEmpty([Environment]::GetEnvironmentVariable($name))){throw 'Existing WebView2 override detected; untouched, no launch.'}}
    foreach($hive in @([Microsoft.Win32.RegistryHive]::LocalMachine,[Microsoft.Win32.RegistryHive]::CurrentUser)){
      foreach($view in @([Microsoft.Win32.RegistryView]::Registry32,[Microsoft.Win32.RegistryView]::Registry64)){
        $basis=[Microsoft.Win32.RegistryKey]::OpenBaseKey($hive,$view)
        try{$key=$basis.OpenSubKey('SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}')
          if($null -ne $key){try{$version=$key.GetValue('pv')}finally{$key.Dispose()}
            if($version -is [string] -and $version -match '^[0-9]+(\.[0-9]+){3}$' -and $version -ne '0.0.0.0'){
              foreach($basePath in @(${env:ProgramFiles(x86)},$env:ProgramFiles,$env:LOCALAPPDATA)){if($basePath){$folder=Join-Path $basePath "Microsoft/EdgeWebView/Application/$version";if(Test-Path -LiteralPath (Join-Path $folder 'msedgewebview2.exe')){$runtimeFound=$folder}}}
            }
          }
        }finally{$basis.Dispose()}
      }
    }
    if($null -eq $runtimeFound){throw 'Existing stable WebView2 runtime unavailable; no install or browser fallback.'}
    $report['runtime_folder']=$runtimeFound;Save-Report
    Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public static class NativeWindowProbe {
 [StructLayout(LayoutKind.Sequential)]public struct Rect{public int Left,Top,Right,Bottom;}
 [DllImport("user32.dll")]public static extern bool GetWindowRect(IntPtr h,out Rect r);
 [DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32.dll")]public static extern IntPtr GetForegroundWindow();
}
'@
    Expand-Archive -LiteralPath $Package -DestinationPath (Join-Path $probeRoot 'app')
    $appRoot=Join-Path $probeRoot 'app/Sim2Act'
    $manifest=Get-Content -LiteralPath (Join-Path $appRoot 'full-package-manifest.json') -Raw -Encoding UTF8|ConvertFrom-Json
    if($manifest.source_commit -cne $report.source_commit){throw 'Application revision mismatch.'}
    foreach($entry in $manifest.files.PSObject.Properties){
        $path=Join-Path $appRoot $entry.Name
        if((Get-Item -LiteralPath $path).Length -ne $entry.Value.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $entry.Value.sha256){throw "Package member changed: $($entry.Name)"}
    }
    $window=Start-Window;Login $window
    $first=$report.starts[0].ready
    Capture 'window-first.png';Close-Window
    $window=Start-Window;Login $window
    $second=$report.starts[1].ready
    if($first.url -cne $second.url -or $first.principal_id -cne $second.principal_id -or $first.data_dir -cne $second.data_dir){throw 'Actual native reopen changed origin/workspace identity.'}
    Capture 'window-reopen.png';Close-Window
    $report.status='PASS_NATIVE_WINDOW_LOGIN_CLOSE_REOPEN_ONLY'
} catch {
    $report.status='FAILED_NOT_ACCEPTED';$report['error_type']=$_.Exception.GetType().FullName;$report['error']=$_.Exception.Message
    throw
} finally {
    try {
        if($null -ne $desktopProcess -and -not $desktopProcess.HasExited){
            try{if($desktopProcess.MainWindowHandle -ne [IntPtr]::Zero){Capture 'window-failure.png'}}catch{$report['failure_capture_error']=$_.Exception.GetType().FullName}
            $report['cleanup']='Normal close requested for own process only; unconfirmed state is retained.'
            [void]$desktopProcess.CloseMainWindow()
            $report['cleanup_exit_confirmed']=$desktopProcess.WaitForExit(15000)
        }
    } catch {$report['cleanup_error']=$_.Exception.GetType().FullName}
    if($null -ne $appRoot -and (Test-Path -LiteralPath (Join-Path $appRoot 'desktop.log'))){Copy-Item -LiteralPath (Join-Path $appRoot 'desktop.log') -Destination (Join-Path $payload 'desktop.log')}
    Save-Report
    $report|ConvertTo-Json -Depth 12
}
