// Standalone WinForms/WebView2 host. No browser/shell fallback or system installer.
using System;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Threading;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

static class Program {
    [DllImport("shell32.dll", CharSet=CharSet.Unicode)] static extern int SetCurrentProcessExplicitAppUserModelID(string id);
    [STAThread] static int Main(string[] args) {
        try {
            if(args.Length>1 || (args.Length==1 && args[0]!="--exact-read-live")) throw new Exception("未知启动参数");
            bool exactReadLive=args.Length==1;
            string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            Paths.Check(root);
            foreach (string name in new [] { "runtime\\python.exe", "Microsoft.Web.WebView2.Core.dll", "Microsoft.Web.WebView2.WinForms.dll", "WebView2Loader.dll" })
                if (!File.Exists(Path.Combine(root,name))) throw new Exception("缺少应用文件：" + name);
            string runtime = Paths.RuntimeFolder(); // Read only; never installs or starts Edge.
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            SetCurrentProcessExplicitAppUserModelID("Sim2Act.Desktop");
            using (Host host = new Host(root,runtime,exactReadLive)) { Application.Run(host); return host.ExitCode; }
        } catch (Exception error) {
            MessageBox.Show("Sim2Act 无法启动：" + error.Message, "Sim2Act", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}

static class Paths {
    public static void Check(string path) {
        DirectoryInfo current = new DirectoryInfo(Path.GetFullPath(path));
        while (current != null) {
            if (current.Exists && (current.Attributes & FileAttributes.ReparsePoint) != 0) throw new Exception("程序和数据目录不能是链接或 junction。");
            current = current.Parent;
        }
    }
    public static string Directory(string root,string name) {
        string path=Path.Combine(root,name); Check(path); System.IO.Directory.CreateDirectory(path); return path;
    }
    public static string RuntimeFolder() {
        if (IntPtr.Size != 8) throw new Exception("需要 Windows x64 应用。");
        foreach (string variable in new [] { "WEBVIEW2_BROWSER_EXECUTABLE_FOLDER", "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "WEBVIEW2_USER_DATA_FOLDER" })
            if (!String.IsNullOrEmpty(Environment.GetEnvironmentVariable(variable))) throw new Exception("检测到外部 WebView2 覆盖配置；请使用无覆盖配置的应用环境。");
        string id="{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}";
        foreach (RegistryHive hive in new [] { RegistryHive.LocalMachine, RegistryHive.CurrentUser })
        foreach (RegistryView view in new [] { RegistryView.Registry32, RegistryView.Registry64 }) {
            using (RegistryKey basis=RegistryKey.OpenBaseKey(hive,view))
            using (RegistryKey key=basis.OpenSubKey("SOFTWARE\\Microsoft\\EdgeUpdate\\Clients\\"+id)) {
                string version=key == null ? null : key.GetValue("pv") as string;
                if (String.IsNullOrEmpty(version) || !Regex.IsMatch(version,"^[0-9]+(\\.[0-9]+){3}$") || version=="0.0.0.0") continue;
                foreach (string basePath in new [] { Environment.GetEnvironmentVariable("ProgramFiles(x86)"), Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) }) {
                    if (String.IsNullOrEmpty(basePath)) continue;
                    string folder=Path.Combine(basePath,"Microsoft","EdgeWebView","Application",version);
                    if (File.Exists(Path.Combine(folder,"msedgewebview2.exe"))) return folder;
                }
            }
        }
        throw new Exception("未找到已有 Microsoft WebView2 Runtime；本程序不会安装运行时或回退到浏览器。");
    }
}

sealed class Host : Form {
    readonly string root,runtime;
    readonly WebView2 view = new WebView2();
    readonly Label status = new Label();
    readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
    readonly ConcurrentQueue<string> output = new ConcurrentQueue<string>();
    int queued, overflow;
    volatile bool stdoutEnded,stderrEnded;
    readonly Stopwatch clock = Stopwatch.StartNew();
    readonly object logGate = new object();
    Process child; FileStream claim; StreamWriter log;
    string worker,origin,boundReadyUrl; Dictionary<string,object> receipt;
    bool initialized,stopping,stopSent,childStarted,stdoutEof,stderrEof,finished,closingAllowed,failed,timeoutShown;
    double startAt,stopAt,exitAt=-1,eofAt=-1;
    public int ExitCode = 1;
    readonly bool exactReadLive;
    public Host(string root,string runtime,bool exactReadLive) {
        this.root=root; this.runtime=runtime;
        this.exactReadLive=exactReadLive;
        Text="Sim2Act 工作台"; StartPosition=FormStartPosition.CenterScreen; ShowInTaskbar=true;
        BackColor=ColorTranslator.FromHtml("#FAF9F5"); MinimumSize=new Size(1024,680);
        Rectangle work=Screen.PrimaryScreen.WorkingArea;
        Size=new Size(Math.Min(1440,work.Width-30),Math.Min(900,work.Height-30));
        status.Dock=DockStyle.Bottom; status.Height=26; status.Padding=new Padding(8,5,0,0); status.Text="正在启动工作台…";
        view.Dock=DockStyle.Fill; Controls.Add(view); Controls.Add(status);
        Shown += async delegate { await Start(); };
        FormClosing += delegate(object sender,FormClosingEventArgs args) {
            if (!closingAllowed) { args.Cancel=true; Stop("正在保存状态并停止后台…"); }
        };
        timer.Interval=100; timer.Tick += Tick; timer.Start();
    }
    void Write(string text) { lock(logGate) { if(log != null) { log.WriteLine(DateTime.UtcNow.ToString("o")+" "+text); log.Flush(); } } }
    async Task Start() {
        try {
            string profile=Paths.Directory(root,"webview-profile"); Paths.Directory(root,"temp"); Paths.Directory(root,"exports");
            claim=new FileStream(Path.Combine(root,"desktop-running.lock"),FileMode.CreateNew,FileAccess.Write,FileShare.Read);
            byte[] claimBytes=Encoding.ASCII.GetBytes(Process.GetCurrentProcess().Id.ToString()); claim.Write(claimBytes,0,claimBytes.Length); claim.Flush();
            log=new StreamWriter(Path.Combine(root,"desktop.log"),true,new UTF8Encoding(false));
            Write("HOST_START native WinForms WebView2; no browser fallback");
            // Stable WebView2 only, explicit existing runtime folder and owned profile.
            CoreWebView2EnvironmentOptions options=new CoreWebView2EnvironmentOptions();
            options.ReleaseChannels=CoreWebView2ReleaseChannels.Stable;
            CoreWebView2Environment environment=await CoreWebView2Environment.CreateAsync(runtime,profile,options);
            if(finished || IsDisposed) return;
            await view.EnsureCoreWebView2Async(environment);
            if(finished || IsDisposed) return;
            view.CoreWebView2.Settings.AreDevToolsEnabled=false;
            view.CoreWebView2.Settings.AreDefaultContextMenusEnabled=false;
            view.CoreWebView2.Settings.IsStatusBarEnabled=false;
            view.CoreWebView2.NavigationStarting += Navigate;
            view.CoreWebView2.FrameNavigationStarting += Navigate;
            view.CoreWebView2.NewWindowRequested += delegate(object sender,CoreWebView2NewWindowRequestedEventArgs args) { args.Handled=true; };
            view.CoreWebView2.PermissionRequested += delegate(object sender,CoreWebView2PermissionRequestedEventArgs args) { args.State=CoreWebView2PermissionState.Deny; };
            view.CoreWebView2.DownloadStarting += Download;
            initialized=true;
            if (stopping) { FinishBeforeChild(); return; }
            StartBackend();
        } catch (Exception error) { if(finished || IsDisposed) return; failed=true; Write("HOST_START_FAILED "+error.GetType().Name); status.Text="启动失败："+error.Message; if(childStarted) Stop("启动失败，正在确认后台退出…"); if(!childStarted) { timer.Stop(); MessageBox.Show(this,"启动失败："+error.Message,"Sim2Act",MessageBoxButtons.OK,MessageBoxIcon.Error); FinishBeforeChild(); } }
    }
    void StartBackend() {
        string data=Path.Combine(root,"workspace data"); Paths.Check(data);
        ProcessStartInfo info=new ProcessStartInfo(Path.Combine(root,"runtime","python.exe"));
        info.Arguments="-I -B -u -m sim2act.cli synthetic-workspace --data-dir \""+data+"\" --control-stdin"+(System.IO.Directory.Exists(data)?"":" --new");
        if(exactReadLive) info.Arguments+=" --exact-read-live";
        info.WorkingDirectory=root; info.UseShellExecute=false; info.CreateNoWindow=true;
        info.RedirectStandardInput=true; info.RedirectStandardOutput=true; info.RedirectStandardError=true;
        info.StandardOutputEncoding=Encoding.UTF8; info.StandardErrorEncoding=Encoding.UTF8;
        info.EnvironmentVariables["TEMP"]=Path.Combine(root,"temp"); info.EnvironmentVariables["TMP"]=Path.Combine(root,"temp");
        info.EnvironmentVariables["PYTHONPATH"]=""; info.EnvironmentVariables["PYTHONNOUSERSITE"]="1";
        info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1"; info.EnvironmentVariables["SIM2ACT_LIVE_ENABLED"]="false";
        child=new Process(); child.StartInfo=info; child.EnableRaisingEvents=true;
        child.OutputDataReceived += delegate(object sender,DataReceivedEventArgs args) {
            if(args.Data==null) { stdoutEnded=true; return; }
            string line=args.Data;
            if(line.Length>8192) { Interlocked.Exchange(ref overflow,1); Write("OVERSIZED_BACKEND_LINE"); return; }
            Write(line);
            if(Interlocked.Increment(ref queued)>256) { Interlocked.Decrement(ref queued); Interlocked.Exchange(ref overflow,1); return; }
            output.Enqueue(line);
        };
        child.ErrorDataReceived += delegate(object sender,DataReceivedEventArgs args) {
            if(args.Data==null) { stderrEnded=true; return; }
            Write(args.Data.Length<=65536 ? args.Data : "OVERSIZED_BACKEND_ERROR");
        };
        if(!child.Start()) throw new Exception("无法启动包内后台。");
        childStarted=true;
        startAt=clock.Elapsed.TotalSeconds; child.BeginOutputReadLine(); child.BeginErrorReadLine();
        Write("BACKEND_STARTED owned PID "+child.Id);
    }
    static string TextValue(Dictionary<string,object> value,string key) { object item; return value.TryGetValue(key,out item) ? item as string : null; }
    static bool True(Dictionary<string,object> value,string key) { object item; return value.TryGetValue(key,out item) && item is bool && (bool)item; }
    void Line(string line) {
        Dictionary<string,object> value;
        try { value=new JavaScriptSerializer().DeserializeObject(line) as Dictionary<string,object>; } catch {return;}
        if(value==null) return;
        string kind=TextValue(value,"event"), id=TextValue(value,"worker_id");
        if(kind=="SYNTHETIC_WORKSPACE_STARTING" || kind=="SYNTHETIC_WORKSPACE_READY") {
            if(TextValue(value,"mode")!="SYNTHETIC_TEST_ONLY" || !True(value,"control_stdin") || id==null || !Regex.IsMatch(id,"^worker_[0-9a-f]{32}$")) return;
            if(worker!=null && worker!=id) {failed=true; Stop("后台身份发生变化，正在停止…"); return;} worker=id;
        }
        if(kind=="SYNTHETIC_WORKSPACE_READY") {
            string url=TextValue(value,"url"); Uri address;
            if(url==null || !Regex.IsMatch(url,"^http://127\\.0\\.0\\.1:[1-9][0-9]{0,4}$") || !Uri.TryCreate(url,UriKind.Absolute,out address) || address.Port>65535) return;
            if(boundReadyUrl!=null && boundReadyUrl!=url) {failed=true; Stop("后台地址发生变化，正在停止…"); return;}
            if(stopping) return;
            if(clock.Elapsed.TotalSeconds-startAt>=30) {failed=true; Stop("启动超时，正在停止…"); return;}
            if(origin==null) {boundReadyUrl=url; origin=address.GetLeftPart(UriPartial.Authority); if(initialized) {view.CoreWebView2.Navigate(boundReadyUrl); status.Text="已连接 · 本地数据自动保存";}}
        }
        if(kind=="SYNTHETIC_WORKSPACE_STOPPED" && worker!=null && id==worker) receipt=value;
    }
    bool Allowed(string url) { Uri value; return origin!=null && Uri.TryCreate(url,UriKind.Absolute,out value) && value.Scheme=="http" && value.Host=="127.0.0.1" && value.UserInfo=="" && value.GetLeftPart(UriPartial.Authority)==origin; }
    void Navigate(object sender,CoreWebView2NavigationStartingEventArgs args) { if(!Allowed(args.Uri)) args.Cancel=true; }
    void Download(object sender,CoreWebView2DownloadStartingEventArgs args) {
        string url=args.DownloadOperation.Uri;
        if(!(Allowed(url) || (origin!=null && url.StartsWith("blob:"+origin+"/",StringComparison.Ordinal)))) {args.Cancel=true;return;}
        string name=Path.GetFileName(args.ResultFilePath); if(!Regex.IsMatch(name,"^[A-Za-z0-9._-]{1,100}$")) name="export.json";
        args.ResultFilePath=Path.Combine(Paths.Directory(root,"exports"),DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-")+Guid.NewGuid().ToString("N").Substring(0,8)+"-"+name);
        args.Handled=true; status.Text="导出文件保存到程序目录 exports";
    }
    void Stop(string message) {
        if(finished) return; status.Text=message; stopping=true;
        if(!childStarted) {FinishBeforeChild();return;}
        if(stopSent) return; stopSent=true; stopAt=clock.Elapsed.TotalSeconds; view.Enabled=false;
        try {
            if(!child.HasExited) {
                if(worker!=null) {child.StandardInput.WriteLine(new JavaScriptSerializer().Serialize(new Dictionary<string,object>{{"command","stop"},{"worker_id",worker}})); child.StandardInput.Flush();}
                child.StandardInput.Close(); // EOF also stops before READY or when parent disappears.
            }
        } catch(Exception error) {Write("STOP_PIPE "+error.GetType().Name);}
    }
    void Tick(object sender,EventArgs args) {
        if(finished) return;
        double now=clock.Elapsed.TotalSeconds;
        if(!childStarted) {
            if(!initialized && now>=30) {
                failed=true; finished=true; timer.Stop(); Write("WEBVIEW_INITIALIZATION_TIMEOUT");
                MessageBox.Show(this,"桌面窗口初始化超时；后台尚未启动。请保留 desktop.log。","Sim2Act",MessageBoxButtons.OK,MessageBoxIcon.Error);
                FinishBeforeChild();
            }
            return;
        }
        Stopwatch batch=Stopwatch.StartNew(); string line;
        for(int i=0;i<64 && batch.ElapsedMilliseconds<5 && output.TryDequeue(out line);i++) { Interlocked.Decrement(ref queued); Line(line); }
        // EOF becomes authoritative only after all preceding stdout records were handled.
        stdoutEof=stdoutEnded && output.IsEmpty && Volatile.Read(ref queued)==0;
        stderrEof=stderrEnded;
        if(Volatile.Read(ref overflow)!=0 && !failed) {failed=true; Stop("后台输出超过安全边界，正在停止…");}
        bool exited; try {exited=child.HasExited;} catch {return;}
        if(origin==null && !stopping && now-startAt>=30) {failed=true; Stop("启动超时，正在停止后台…");}
        if(exited && exitAt<0) exitAt=now;
        if(stdoutEof && !exited && eofAt<0) eofAt=now;
        if(exited && stdoutEof && stderrEof) {
            bool clean=receipt!=null && True(receipt,"worker_stopped") && True(receipt,"clean") && True(receipt,"data_preserved");
            ExitCode=child.ExitCode==0 && clean && !failed ? 0 : 1;
            Write(new JavaScriptSerializer().Serialize(new Dictionary<string,object>{{"event","DESKTOP_EXIT"},{"child_returncode",child.ExitCode},{"receipt_verified",clean},{"ready_seen",origin!=null},{"exitcode",ExitCode}}));
            finished=true;
            if(ExitCode==0) ReleaseClaim();
            else {
                if(claim!=null) {claim.Dispose();claim=null;}
                MessageBox.Show(this,"后台已退出，但未通过完整退出确认。数据、运行锁和 desktop.log 已保留。","Sim2Act",MessageBoxButtons.OK,MessageBoxIcon.Error);
            }
            closingAllowed=true; Close(); return;
        }
        if(!timeoutShown && ((stopping && stopSent && now-stopAt>=20) || (exited && now-exitAt>=5) || (eofAt>=0 && now-eofAt>=5))) {
            timeoutShown=true; failed=true;
            status.Text="后台退出未确认：保留数据、运行锁和日志；未强制终止进程。"; Write("EXIT_UNKNOWN claim preserved; no kill or restart");
        }
    }
    void FinishBeforeChild() {finished=true; ExitCode=failed?1:0; ReleaseClaim(); closingAllowed=true; Close();}
    void ReleaseClaim() {if(claim!=null) {claim.Dispose();claim=null; File.Delete(Path.Combine(root,"desktop-running.lock"));}}
    protected override void Dispose(bool disposing) {
        if(disposing) {timer.Dispose(); lock(logGate) {if(log!=null) {log.Dispose();log=null;}} if(claim!=null) claim.Dispose(); if(child!=null) child.Dispose();}
        base.Dispose(disposing);
    }
}
