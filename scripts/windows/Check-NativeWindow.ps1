param([Parameter(Mandatory=$true)][string]$Package,[Parameter(Mandatory=$true)][string]$Output,[switch]$ExerciseMaterial)
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
function Budget { if($clock.Elapsed.TotalSeconds -gt $(if($ExerciseMaterial){40}else{115})){throw 'Finite ordinary window probe budget exhausted.'} }
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
function Form-Control($Window,[string]$Name,$Type) {
    Budget
    $condition=[Windows.Automation.AndCondition]::new(
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::NameProperty,$Name),
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,$Type))
    $control=$Window.FindFirst([Windows.Automation.TreeScope]::Descendants,$condition)
    if($null -eq $control -or -not$control.Current.IsEnabled){throw "Actual form control unavailable: $Name"}
    if($control.Current.IsOffscreen){
        $pattern=$null
        if($control.TryGetCurrentPattern([Windows.Automation.ScrollItemPattern]::Pattern,[ref]$pattern)){([Windows.Automation.ScrollItemPattern]$pattern).ScrollIntoView()}
        else{$control.SetFocus()}
        Start-Sleep -Milliseconds 150
        if($control.Current.IsOffscreen){throw "Actual form control remains offscreen: $Name"}
    }
    return $control
}
function Set-FormValue($Window,[string]$Name,[string]$Value){
    $control=Form-Control $Window $Name ([Windows.Automation.ControlType]::Edit)
    ([Windows.Automation.ValuePattern]$control.GetCurrentPattern([Windows.Automation.ValuePattern]::Pattern)).SetValue($Value)
}
function Open-Summary($Window,[string]$Prefix){
    $buttons=$Window.FindAll([Windows.Automation.TreeScope]::Descendants,
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Button))
    foreach($control in $buttons){
        if($control.Current.Name.StartsWith($Prefix,[StringComparison]::Ordinal) -and $control.Current.IsEnabled -and -not$control.Current.IsOffscreen){
            $pattern=$null
            if($control.TryGetCurrentPattern([Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$pattern)){
                $expand=[Windows.Automation.ExpandCollapsePattern]$pattern
                if($expand.Current.ExpandCollapseState -eq [Windows.Automation.ExpandCollapseState]::Collapsed){$expand.Expand()}
                elseif($expand.Current.ExpandCollapseState -ne [Windows.Automation.ExpandCollapseState]::Expanded){throw 'Summary cannot expand using ordinary UIA.'}
            }else{Invoke-Control $control}
            return $control
        }
    }
    throw "Actual summary unavailable: $Prefix"
}
function Submit-Control($Window,[string]$Name,$Summary){
    $summaryId=$Summary.GetRuntimeId() -join ':'
    $condition=[Windows.Automation.AndCondition]::new(
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::NameProperty,$Name),
        [Windows.Automation.PropertyCondition]::new([Windows.Automation.AutomationElement]::ControlTypeProperty,[Windows.Automation.ControlType]::Button))
    $submitCandidates=@(foreach($control in $Window.FindAll([Windows.Automation.TreeScope]::Descendants,$condition)){
        if($control.Current.IsEnabled -and -not$control.Current.IsOffscreen -and ($control.GetRuntimeId() -join ':') -cne $summaryId){$control}
    })
    if($submitCandidates.Count -ne 1){throw 'Unique visible form submit required; summary identity excluded.'}
    return $submitCandidates[0]
}
function Read-Local([string]$Path){
    Budget
    $url=$report.starts[-1].ready.url
    if($url -notmatch '^http://127[.]0[.]0[.]1:[1-9][0-9]{0,4}$' -or $Path -notmatch '^/api/(projects|resources)(/|$)'){throw 'Read restricted to actual owned loopback API.'}
    $data=Invoke-RestMethod -Uri ($url+$Path) -Headers @{Authorization='Bearer public-synthetic-blank-workspace'} -TimeoutSec 4
    foreach($row in $data){Write-Output $row}
}
function Selected-Value($Control){
    # WebView2 providers expose HTML select through different ordinary read-only
    # UIA patterns. Keep exact value equality; never infer selection from a GET.
    $pattern=$null
    if($Control.TryGetCurrentPattern([Windows.Automation.SelectionPattern]::Pattern,[ref]$pattern)){
        $items=@(([Windows.Automation.SelectionPattern]$pattern).GetCurrentSelection())
        if($items.Count -ne 1){throw 'Single UI selection required.'}
        return $items[0].Current.Name
    }
    $pattern=$null
    if($Control.TryGetCurrentPattern([Windows.Automation.ValuePattern]::Pattern,[ref]$pattern)){
        return ([Windows.Automation.ValuePattern]$pattern).Current.Value
    }
    $pattern=$null
    if($Control.TryGetCurrentPattern([Windows.Automation.LegacyIAccessiblePattern]::Pattern,[ref]$pattern)){
        return ([Windows.Automation.LegacyIAccessiblePattern]$pattern).Current.Value
    }
    throw 'No ordinary UIA selection/value reader; unchanged submit gate rejects.'
}
function Check-Material {
    $projects=@(Read-Local '/api/projects'|Where-Object {$_.name -ceq 'native-window-synthetic'})
    if($projects.Count -ne 1){throw 'Exact UI-created project not unique.'}
    $resources=@(Read-Local ("/api/projects/"+$projects[0].id+"/resources")|Where-Object {$_.name -ceq 'native-window.csv'})
    if($resources.Count -ne 1 -or $resources[0].format -cne 'csv'){throw 'Exact UI-created CSV not unique/current.'}
    $resource=Read-Local ("/api/resources/"+$resources[0].id)
    if($resource.content -cne "item,amount,quantity`nA,10,7`nB,20,8"){throw 'Actual saved content mismatch.'}
    return @{project_id=$projects[0].id;resource_id=$resources[0].id;format=$resources[0].format;content=$resource.content}
}
function Save-Material($Window){
    $projectSummary=Open-Summary $Window '创建项目'
    Set-FormValue $Window '项目名称' 'native-window-synthetic'
    Invoke-Control (Submit-Control $Window '创建项目' $projectSummary)
    $until=[DateTime]::UtcNow.AddSeconds(6)
    do{$projects=@(Read-Local '/api/projects'|Where-Object {$_.name -ceq 'native-window-synthetic'});if($projects.Count -eq 1){break};Start-Sleep -Milliseconds 150}while([DateTime]::UtcNow -lt $until)
    if($projects.Count -ne 1){throw 'UI project creation not confirmed; no repeat submit.'}
    $report['ui_project_id']=$projects[0].id;Save-Report
    $until=[DateTime]::UtcNow.AddSeconds(6);$selected=$false
    do{
        Budget;$selector=Find-Control $Window '当前项目' ([Windows.Automation.ControlType]::ComboBox)
        $selected=(Selected-Value $selector) -ceq 'native-window-synthetic'
        if(-not$selected){Start-Sleep -Milliseconds 150}
    }while(-not$selected -and [DateTime]::UtcNow -lt $until)
    if(-not$selected){throw 'UI project selection not confirmed; no material submit.'}
    Invoke-Control (Find-Control $Window '资源' ([Windows.Automation.ControlType]::Button))
    [void](Open-Summary $Window '添加材料')
    Set-FormValue $Window '名称' 'native-window.csv'
    $format=Form-Control $Window '类型' ([Windows.Automation.ControlType]::ComboBox)
    $desktopProcess.Refresh()
    if(-not[NativeWindowProbe]::SetForegroundWindow($desktopProcess.MainWindowHandle)){throw 'Own foreground unavailable; no keyboard fallback.'}
    $format.SetFocus()
    if([NativeWindowProbe]::GetForegroundWindow() -ne $desktopProcess.MainWindowHandle){throw 'Own foreground changed; no keys sent.'}
    [Windows.Forms.SendKeys]::SendWait('{HOME}c')
    if((Selected-Value $format) -cne 'csv'){throw 'CSV UI selection not confirmed; no material submit.'}
    Set-FormValue $Window '授权给当前项目的文本' "item,amount,quantity`nA,10,7`nB,20,8"
    Invoke-Control (Form-Control $Window '保存并授权项目内使用（24小时）' ([Windows.Automation.ControlType]::Button))
    $until=[DateTime]::UtcNow.AddSeconds(6)
    $proof=$null;$lastError=$null
    do{try{$proof=Check-Material;break}catch{$lastError=$_;Start-Sleep -Milliseconds 150}}while([DateTime]::UtcNow -lt $until)
    if($null -eq $proof){throw $lastError}
    $report['ui_saved_material']=$proof;Save-Report
}
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
    if($ExerciseMaterial){Save-Material $window}
    Capture 'window-first.png';Close-Window
    $window=Start-Window;Login $window
    $second=$report.starts[1].ready
    if($first.url -cne $second.url -or $first.principal_id -cne $second.principal_id -or $first.data_dir -cne $second.data_dir){throw 'Actual native reopen changed origin/workspace identity.'}
    if($ExerciseMaterial){
        $proof=Check-Material
        if($proof.project_id -cne $report.ui_saved_material.project_id -or $proof.resource_id -cne $report.ui_saved_material.resource_id){throw 'Reopen changed UI-created record identity.'}
        Invoke-Control (Find-Control $window '资源' ([Windows.Automation.ControlType]::Button))
        $report['ui_reopened_material']=$proof;Save-Report
    }
    Capture 'window-reopen.png';Close-Window
    $report.status=if($ExerciseMaterial){'PASS_NATIVE_UI_PROJECT_CSV_SAVE_CLOSE_REOPEN_ONLY'}else{'PASS_NATIVE_WINDOW_LOGIN_CLOSE_REOPEN_ONLY'}
} catch {
    $report.status='FAILED_NOT_ACCEPTED';$report['error_type']=$_.Exception.GetType().FullName;$report['error']=$_.Exception.Message
    throw
} finally {
    try {
        if($null -ne $desktopProcess -and -not $desktopProcess.HasExited){
            try{if($desktopProcess.MainWindowHandle -ne [IntPtr]::Zero){Capture 'window-failure.png'}}catch{$report['failure_capture_error']=$_.Exception.GetType().FullName}
            $report['cleanup']='Normal close requested for own process only; unconfirmed state is retained.'
            [void]$desktopProcess.CloseMainWindow()
            $report['cleanup_exit_confirmed']=$desktopProcess.WaitForExit($(if($ExerciseMaterial){5000}else{15000}))
        }
    } catch {$report['cleanup_error']=$_.Exception.GetType().FullName}
    if($null -ne $appRoot -and (Test-Path -LiteralPath (Join-Path $appRoot 'desktop.log'))){Copy-Item -LiteralPath (Join-Path $appRoot 'desktop.log') -Destination (Join-Path $payload 'desktop.log')}
    Save-Report
    $report|ConvertTo-Json -Depth 12
}
