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
            bool exactReadLive=false; string config=null,selection=null;
            for(int i=0;i<args.Length;i++) {
                if(args[i]=="--exact-read-live" && !exactReadLive) exactReadLive=true;
                else if(args[i]=="--config" && config==null && i+1<args.Length) config=Paths.ExistingFile(args[++i]);
                else if(args[i]=="--spec-selection" && selection==null && i+1<args.Length) selection=Paths.ExistingFile(args[++i]);
                else throw new Exception("未知或重复启动参数");
            }
            if((exactReadLive && config!=null) || (selection!=null && config==null)) throw new Exception("正式配置与合成预览参数不能混用");
            string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            Paths.Check(root);
            foreach (string name in new [] { "runtime\\python.exe", "Microsoft.Web.WebView2.Core.dll", "Microsoft.Web.WebView2.WinForms.dll", "WebView2Loader.dll" })
                if (!File.Exists(Path.Combine(root,name))) throw new Exception("缺少应用文件：" + name);
            string runtime = Paths.RuntimeFolder(); // Read only; never installs or starts Edge.
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            SetCurrentProcessExplicitAppUserModelID("Sim2Act.Desktop");
            using (Host host = new Host(root,runtime,exactReadLive,config,selection)) { Application.Run(host); return host.ExitCode; }
        } catch (Exception error) {
            MessageBox.Show("Sim2Act 无法启动：" + error.Message, "Sim2Act", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}

static class Paths {
    public static string ExistingFile(string path) {
        string full=Path.GetFullPath(path);
        if(full.IndexOf('"')>=0 || full.IndexOf('\n')>=0 || full.IndexOf('\r')>=0) throw new Exception("配置路径不合法");
        FileInfo file=new FileInfo(full);
        if(!file.Exists || (file.Attributes & FileAttributes.ReparsePoint)!=0 || file.Length>65536) throw new Exception("请选择已有普通私有配置文件");
        Check(file.DirectoryName); return full;
    }
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
    sealed class BackendLine {
        public readonly string Text;
        public readonly bool Error;
        public BackendLine(string text,bool error) {Text=text;Error=error;}
    }
    readonly string root,runtime;
    readonly WebView2 view = new WebView2();
    readonly Label status = new Label();
    readonly System.Windows.Forms.Timer timer = new System.Windows.Forms.Timer();
    readonly ConcurrentQueue<BackendLine> output = new ConcurrentQueue<BackendLine>();
    int queued, overflow, logFailed;
    volatile bool stdoutEnded,stderrEnded;
    readonly Stopwatch clock = Stopwatch.StartNew();
    readonly object logGate = new object();
    Process child; FileStream claim; StreamWriter log;
    string worker,origin,boundReadyUrl,expectedData,startupIssue,serviceSession; Dictionary<string,object> receipt;
    int apiPid,workerPid;
    bool logFailureHandled,userStopRequested;
    bool initialized,stopping,stopSent,childStarted,stdoutEof,stderrEof,finished,closingAllowed,failed,timeoutShown;
    double startAt,stopAt,exitAt=-1,eofAt=-1;
    public int ExitCode = 1;
    readonly bool exactReadLive;
    readonly string configuredFile,selectionFile;
    bool Configured {get {return configuredFile!=null;}}
    string ProfileIdentityPath {get {return Path.Combine(root,"configured-webview-profile.identity.json");}}
    public Host(string root,string runtime,bool exactReadLive,string configuredFile,string selectionFile) {
        this.root=root; this.runtime=runtime;
        this.exactReadLive=exactReadLive;
        this.configuredFile=configuredFile;this.selectionFile=selectionFile;
        Text="Sim2Act 工作台"; StartPosition=FormStartPosition.CenterScreen; ShowInTaskbar=true;
        BackColor=ColorTranslator.FromHtml("#FAF9F5"); MinimumSize=new Size(1024,680);
        Rectangle work=Screen.PrimaryScreen.WorkingArea;
        Size=new Size(Math.Min(1440,work.Width-30),Math.Min(900,work.Height-30));
        status.Dock=DockStyle.Bottom; status.Height=26; status.Padding=new Padding(8,5,0,0); status.Text="正在启动工作台…";
        view.Dock=DockStyle.Fill; Controls.Add(view); Controls.Add(status);
        Shown += async delegate { await Start(); };
        FormClosing += delegate(object sender,FormClosingEventArgs args) {
            if (!closingAllowed) { userStopRequested=true; args.Cancel=true; Stop("正在保存状态并停止后台…"); }
        };
        timer.Interval=100; timer.Tick += Tick; timer.Start();
    }
    void Write(string text) {
        lock(logGate) {
            if(log==null || Volatile.Read(ref logFailed)!=0) return;
            try {log.WriteLine(DateTime.UtcNow.ToString("o")+" "+text);log.Flush();}
            catch(Exception) {Interlocked.Exchange(ref logFailed,1);}
        }
    }
    void QueueLine(string line,bool error) {
        if(line.Length>8192) {Interlocked.Exchange(ref overflow,1);Write("OVERSIZED_BACKEND_LINE");return;}
        Write(line);
        if(Interlocked.Increment(ref queued)>256) {Interlocked.Decrement(ref queued);Interlocked.Exchange(ref overflow,1);return;}
        output.Enqueue(new BackendLine(line,error));
    }
    async Task Start() {
        try {
            claim=new FileStream(Path.Combine(root,"desktop-running.lock"),FileMode.CreateNew,FileAccess.Write,FileShare.Read);
            byte[] claimBytes=Encoding.ASCII.GetBytes(Process.GetCurrentProcess().Id.ToString()); claim.Write(claimBytes,0,claimBytes.Length); claim.Flush();
            string profile=Path.Combine(root,Configured?"configured-webview-profile":"webview-profile");
            if(Configured) PrepareConfiguredProfile(profile);
            profile=Paths.Directory(root,Configured?"configured-webview-profile":"webview-profile"); Paths.Directory(root,"temp"); Paths.Directory(root,"exports");
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
    Dictionary<string,object> ProfileIdentity() {
        FileInfo file=new FileInfo(ProfileIdentityPath);Paths.Check(file.DirectoryName);
        if(!file.Exists || (file.Attributes & FileAttributes.ReparsePoint)!=0 || file.Length>4096) throw new Exception("桌面配置绑定记录无法确认；已保留原目录");
        var value=new JavaScriptSerializer().DeserializeObject(File.ReadAllText(file.FullName,Encoding.UTF8)) as Dictionary<string,object>;
        if(value==null || TextValue(value,"version")!="sim2act-configured-profile.v1") throw new Exception("桌面配置绑定记录损坏；已保留原目录");
        string state=TextValue(value,"state");
        if(!((state=="UNBOUND_NO_NAVIGATION" && value.Count==2) || (state=="BOUND" && value.Count==5))) throw new Exception("桌面配置绑定状态未知；已保留原目录");
        return value;
    }
    void PrepareConfiguredProfile(string profile) {
        Paths.Check(profile);
        if(!File.Exists(ProfileIdentityPath)) {
            if(System.IO.Directory.Exists(profile)) throw new Exception("已有正式浏览状态缺少绑定记录；不接管或清空原状态");
            using(var stream=new FileStream(ProfileIdentityPath,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
                byte[] value=Encoding.UTF8.GetBytes("{\"version\":\"sim2act-configured-profile.v1\",\"state\":\"UNBOUND_NO_NAVIGATION\"}");
                stream.Write(value,0,value.Length);stream.Flush(true);
            }
        }
        ProfileIdentity();
    }
    bool BindConfiguredProfile(string data,string binding,Uri address) {
        try {
            var record=ProfileIdentity();
            string canonicalData=Path.GetFullPath(data).TrimEnd(Path.DirectorySeparatorChar).ToUpperInvariant();
            string url=address.GetLeftPart(UriPartial.Authority);
            if(TextValue(record,"state")=="BOUND") return TextValue(record,"binding")==binding
                && TextValue(record,"data_dir")==canonicalData && TextValue(record,"origin")==url;
            var bound=new Dictionary<string,object>{{"version","sim2act-configured-profile.v1"},{"state","BOUND"},
                {"binding",binding},{"data_dir",canonicalData},{"origin",url}};
            byte[] bytes=Encoding.UTF8.GetBytes(new JavaScriptSerializer().Serialize(bound));
            // The exclusive host claim serializes this transition. Never clear
            // localStorage or silently adopt a different database namespace.
            using(var stream=new FileStream(ProfileIdentityPath,FileMode.Open,FileAccess.ReadWrite,FileShare.None)) {
                stream.SetLength(0);stream.Write(bytes,0,bytes.Length);stream.Flush(true);
            }
            return true;
        } catch(Exception) {return false;}
    }
    void StartBackend() {
        string data=Path.Combine(root,"workspace data");
        if(!Configured) {Paths.Check(data);expectedData=Path.GetFullPath(data).TrimEnd(Path.DirectorySeparatorChar);}
        ProcessStartInfo info=new ProcessStartInfo(Path.Combine(root,"runtime","python.exe"));
        info.Arguments="-I -B -u -m sim2act.cli synthetic-workspace --data-dir \""+data+"\" --control-stdin"+(System.IO.Directory.Exists(data)?"":" --new");
        if(exactReadLive) info.Arguments+=" --exact-read-live";
        if(Configured) {
            info.Arguments="-I -B -u -m sim2act.desktop_service --supervise --control-stdin --config \""+configuredFile+"\"";
            if(selectionFile!=null) info.Arguments+=" --spec-selection \""+selectionFile+"\"";
        }
        info.WorkingDirectory=root; info.UseShellExecute=false; info.CreateNoWindow=true;
        info.RedirectStandardInput=true; info.RedirectStandardOutput=true; info.RedirectStandardError=true;
        info.StandardOutputEncoding=Encoding.UTF8; info.StandardErrorEncoding=Encoding.UTF8;
        info.EnvironmentVariables["TEMP"]=Path.Combine(root,"temp"); info.EnvironmentVariables["TMP"]=Path.Combine(root,"temp");
        info.EnvironmentVariables["PYTHONPATH"]=""; info.EnvironmentVariables["PYTHONNOUSERSITE"]="1";
        info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"]="1"; info.EnvironmentVariables["SIM2ACT_LIVE_ENABLED"]="false";
        child=new Process(); child.StartInfo=info; child.EnableRaisingEvents=true;
        child.OutputDataReceived += delegate(object sender,DataReceivedEventArgs args) {
            if(args.Data==null) { stdoutEnded=true; return; }
            QueueLine(args.Data,false);
        };
        child.ErrorDataReceived += delegate(object sender,DataReceivedEventArgs args) {
            if(args.Data==null) { stderrEnded=true; return; }
            QueueLine(args.Data,true);
        };
        if(!child.Start()) throw new Exception("无法启动包内后台。");
        childStarted=true;
        startAt=clock.Elapsed.TotalSeconds; child.BeginOutputReadLine(); child.BeginErrorReadLine();
        Write("BACKEND_STARTED owned PID "+child.Id);
    }
    static string TextValue(Dictionary<string,object> value,string key) { object item; return value.TryGetValue(key,out item) ? item as string : null; }
    static bool True(Dictionary<string,object> value,string key) { object item; return value.TryGetValue(key,out item) && item is bool && (bool)item; }
    string StartupMessage(string code) {
        switch(code) {
            case "PORT_UNAVAILABLE": return "原工作台端口仍被占用。请核对原窗口是否已退出；保留工程、origin记录和运行锁。";
            case "INVALID_DESKTOP_ORIGIN": case "DESKTOP_ORIGIN_CHANGED":
            case "DESKTOP_ORIGIN_PORT_MISMATCH": return "工作台地址记录损坏或身份变化；保留原工程与 desktop.log，未更换地址或重建数据。";
            case "SCHEMA_CHANGED": case "UNKNOWN_WORKSPACE": case "IDENTITY_CHANGED": return "工作区版本或身份不匹配；请保留原目录，不要覆盖数据库。";
            case "EXACT_READ_EXISTING_TOKEN_MISSING": return "当前程序环境没有既有模型配置。可用默认模式打开工程；程序不会创建凭据。";
            default: return "后台未能启动；请保留工程和 desktop.log 核对具体错误。";
        }
    }
    bool WorkspaceIdentity(Dictionary<string,object> value,Uri address) {
        try {
            string data=TextValue(value,"data_dir"),principal=TextValue(value,"principal_id");
            if(data==null || !String.Equals(Path.GetFullPath(data).TrimEnd(Path.DirectorySeparatorChar),expectedData,StringComparison.OrdinalIgnoreCase)
                || TextValue(value,"public_token")!="public-synthetic-blank-workspace"
                || principal==null || !Regex.IsMatch(principal,"^user_[0-9a-f]{32}$")) return false;
            Paths.Check(data);
            Dictionary<string,object>[] records=new Dictionary<string,object>[2];
            string[] names={"synthetic-workspace.json","desktop-origin.json"};
            for(int i=0;i<names.Length;i++) {
                FileInfo file=new FileInfo(Path.Combine(data,names[i]));
                if(!file.Exists || (file.Attributes & FileAttributes.ReparsePoint)!=0 || file.Length>4096) return false;
                records[i]=new JavaScriptSerializer().DeserializeObject(File.ReadAllText(file.FullName,Encoding.UTF8)) as Dictionary<string,object>;
                if(records[i]==null || TextValue(records[i],"principal_id")!=principal) return false;
            }
            string version=TextValue(records[0],"version"); object port;
            return (version=="sim2act-blank-synthetic-workspace.v1" || version=="sim2act-blank-synthetic-workspace.v2")
                && TextValue(records[0],"mode")=="SYNTHETIC_TEST_ONLY"
                && TextValue(records[1],"version")=="sim2act-desktop-origin.v1"
                && TextValue(records[1],"host")=="127.0.0.1"
                && records[1].TryGetValue("port",out port) && port is int && (int)port==address.Port;
        } catch(Exception) {return false;}
    }
    bool ConfiguredIdentity(Dictionary<string,object> value,Uri address) {
        try {
            string data=TextValue(value,"data_dir");object api,work;
            if(data==null || !Path.IsPathRooted(data) || !value.TryGetValue("api_pid",out api) || !(api is int)
                || !value.TryGetValue("worker_pid",out work) || !(work is int)
                || (int)api<=0 || (int)work<=0 || (int)api==(int)work || (int)api==child.Id || (int)work==child.Id) return false;
            Paths.Check(data);
            var records=new Dictionary<string,object>[2];
            string[] names={"desktop-service-origin.json","desktop-service-claim.json"};
            for(int i=0;i<2;i++) {
                FileInfo file=new FileInfo(Path.Combine(data,names[i]));
                if(!file.Exists || (file.Attributes & FileAttributes.ReparsePoint)!=0 || file.Length>8192) return false;
                records[i]=new JavaScriptSerializer().DeserializeObject(File.ReadAllText(file.FullName,Encoding.UTF8)) as Dictionary<string,object>;
                if(records[i]==null || TextValue(records[i],"protocol")!="sim2act.desktop-service.v1"
                    || TextValue(records[i],"backend")!="CONFIGURED_POSTGRESQL") return false;
            }
            object port,controller;string binding=TextValue(records[0],"binding");
            if(binding==null || !Regex.IsMatch(binding,"^[a-f0-9]{64}$")
                || !String.Equals(TextValue(records[0],"data_dir"),data,StringComparison.OrdinalIgnoreCase)
                || !records[0].TryGetValue("port",out port) || !(port is int) || (int)port!=address.Port
                || TextValue(records[1],"session")!=serviceSession
                || !records[1].TryGetValue("controller_pid",out controller) || !(controller is int) || (int)controller!=child.Id) return false;
            object rows;var seen=new HashSet<string>();
            if(!records[1].TryGetValue("children",out rows) || !(rows is object[]) || ((object[])rows).Length!=2) return false;
            foreach(object row in (object[])rows) {
                var item=row as Dictionary<string,object>;object pid;
                if(item==null || !item.TryGetValue("pid",out pid) || !(pid is int)) return false;
                string role=TextValue(item,"role");
                if((role!="api" && role!="worker") || !seen.Add(role) || (int)pid!=(role=="api"?(int)api:(int)work)) return false;
            }
            if(!BindConfiguredProfile(data,binding,address)) {
                startupIssue="当前数据库、目录或地址与桌面浏览状态绑定不一致；原请求、数据和浏览状态已保留。请使用独立应用目录。";
                return false;
            }
            expectedData=data;apiPid=(int)api;workerPid=(int)work;return true;
        } catch(Exception) {return false;}
    }
    bool ConfiguredStop(Dictionary<string,object> value) {
        if(!True(value,"clean")) return false;
        object number;
        if(!value.TryGetValue("children_started",out number) || !(number is int)) return false;
        if((int)number==0) return origin==null && !True(value,"ready_seen");
        object raw;var roles=value.TryGetValue("roles",out raw)?raw as Dictionary<string,object>:null;
        if((int)number<1 || (int)number>2 || roles==null || roles.Count!=(int)number || !True(value,"preflight_stopped")
            || (origin!=null && ((int)number!=2 || !True(value,"ready_seen")))) return false;
        foreach(string name in roles.Keys) {
            if(name!="api" && name!="worker") return false;
            object roleRaw;var role=roles.TryGetValue(name,out roleRaw)?roleRaw as Dictionary<string,object>:null;
            object pid,code,receiptRaw;
            if(role==null || !role.TryGetValue("pid",out pid) || !(pid is int)
                || !role.TryGetValue("exitcode",out code) || !(code is int) || (int)code!=0
                || !True(role,"stdout_eof") || !True(role,"stderr_eof") || !role.TryGetValue("receipt",out receiptRaw)) return false;
            var childReceipt=receiptRaw as Dictionary<string,object>;object receiptPid;
            if(childReceipt==null || !True(childReceipt,"clean") || TextValue(childReceipt,"event")!="ROLE_STOPPED"
                || TextValue(childReceipt,"role")!=name || TextValue(childReceipt,"session")!=serviceSession
                || TextValue(childReceipt,"protocol")!="sim2act.desktop-service.v1" || TextValue(childReceipt,"backend")!="CONFIGURED_POSTGRESQL"
                || !childReceipt.TryGetValue("pid",out receiptPid) || !(receiptPid is int) || (int)receiptPid!=(int)pid
                || (origin!=null && ((int)pid!=(name=="api"?apiPid:workerPid) || !True(childReceipt,"ready_seen")))) return false;
        }
        return true;
    }
    void ConfiguredLine(Dictionary<string,object> value) {
        string session=TextValue(value,"session"),kind=TextValue(value,"event");
        if(TextValue(value,"protocol")!="sim2act.desktop-service.v1" || TextValue(value,"backend")!="CONFIGURED_POSTGRESQL"
            || session==null || !Regex.IsMatch(session,"^[a-f0-9]{32}$") || (serviceSession!=null && serviceSession!=session)) {
            failed=true;Stop("受控后台协议或会话不匹配；保留运行记录。");return;
        }
        if(kind=="DESKTOP_SERVICE_STARTING" && serviceSession==null) {serviceSession=session;return;}
        if(serviceSession==null) {failed=true;Stop("后台未提供本次启动身份。");return;}
        if(kind=="DESKTOP_SERVICE_ERROR") {failed=true;Stop("配置、审批或后台生命周期未确认；保留数据和运行记录。");return;}
        if(kind=="DESKTOP_SERVICE_STOPPED") {receipt=value;return;}
        if(kind!="DESKTOP_SERVICE_READY") {failed=true;Stop("后台回执顺序异常。");return;}
        string url=TextValue(value,"url"),id=TextValue(value,"worker_id");Uri address;
        if(worker!=null || id==null || !Regex.IsMatch(id,"^worker_[0-9a-f]{32}$") || url==null
            || !Regex.IsMatch(url,"^http://127\\.0\\.0\\.1:[1-9][0-9]{0,4}$") || !Uri.TryCreate(url,UriKind.Absolute,out address)
            || address.Port>65535 || !ConfiguredIdentity(value,address)) {failed=true;Stop(startupIssue??"受控后台数据或进程身份不匹配。");return;}
        worker=id;
        if(stopping) return;
        if(clock.Elapsed.TotalSeconds-startAt>=30) {failed=true;Stop("配置后台启动超时，正在确认退出…");return;}
        boundReadyUrl=url;origin=address.GetLeftPart(UriPartial.Authority);
        if(initialized) {view.CoreWebView2.Navigate(boundReadyUrl);status.Text="已连接 · 使用已配置账户登录 · 数据保留在原数据库";}
    }
    void Line(BackendLine record) {
        string line=record.Text;
        const string prefix="Synthetic workspace stopped; existing data preserved: ";
        if(record.Error) {
            if(line.StartsWith(prefix,StringComparison.Ordinal)) {
                startupIssue=StartupMessage(line.Substring(prefix.Length).Trim());failed=true;Stop(startupIssue);
            }
            return; // stderr never supplies a READY/STOPPED protocol receipt.
        }
        Dictionary<string,object> value;
        try { value=new JavaScriptSerializer().DeserializeObject(line) as Dictionary<string,object>; } catch {return;}
        if(value==null) return;
        if(Configured) {ConfiguredLine(value);return;}
        string kind=TextValue(value,"event"), id=TextValue(value,"worker_id");
        if(kind=="SYNTHETIC_WORKSPACE_STARTING" || kind=="SYNTHETIC_WORKSPACE_READY") {
            if(TextValue(value,"mode")!="SYNTHETIC_TEST_ONLY" || !True(value,"control_stdin") || id==null || !Regex.IsMatch(id,"^worker_[0-9a-f]{32}$")) return;
            if(worker!=null && worker!=id) {failed=true; Stop("后台身份发生变化，正在停止…"); return;} worker=id;
        }
        if(kind=="SYNTHETIC_WORKSPACE_READY") {
            string url=TextValue(value,"url"); Uri address;
            if(url==null || !Regex.IsMatch(url,"^http://127\\.0\\.0\\.1:[1-9][0-9]{0,4}$") || !Uri.TryCreate(url,UriKind.Absolute,out address) || address.Port>65535) return;
            if(!WorkspaceIdentity(value,address)) {startupIssue="后台工作区身份与本窗口不匹配；未导航或重建数据。";failed=true;Stop(startupIssue);return;}
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
        try {
        string url=args.DownloadOperation.Uri;
        if(!(Allowed(url) || (origin!=null && url.StartsWith("blob:"+origin+"/",StringComparison.Ordinal)))) {args.Cancel=true;return;}
        string name=Path.GetFileName(args.ResultFilePath); if(!Regex.IsMatch(name,"^[A-Za-z0-9._-]{1,100}$")) name="export.json";
        string target=Path.Combine(Paths.Directory(root,"exports"),DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-")+Guid.NewGuid().ToString("N").Substring(0,8)+"-"+name);
        args.ResultFilePath=target;
        CoreWebView2DownloadOperation operation=args.DownloadOperation;
        EventHandler<object> changed=null;
        changed=delegate(object source,object changedArgs) {
            if(IsDisposed || finished) {
                try {operation.StateChanged-=changed;} catch(Exception) {}
                return;
            }
            try {
                CoreWebView2DownloadState state=operation.State;
                if(state==CoreWebView2DownloadState.InProgress) return;
                operation.StateChanged-=changed;
                status.Text=state==CoreWebView2DownloadState.Completed
                    ? "导出完成："+target : "导出未完成："+operation.InterruptReason.ToString()+"；原成果未更改。";
            } catch(Exception error) {
                try {operation.StateChanged-=changed;} catch(Exception) {}
                status.Text="导出状态未确认；请检查 exports 和 desktop.log，原成果未更改。";
                Write("DOWNLOAD_STATE_FAILED "+error.GetType().Name);
            }
        };
        operation.StateChanged+=changed;
        args.Handled=true; status.Text="正在导出到程序目录 exports…";
        changed(operation,EventArgs.Empty);
        } catch(Exception error) {
            args.Cancel=true;
            status.Text="导出失败；请检查 exports 目录空间/权限，原成果未更改。";
            Write("DOWNLOAD_START_FAILED "+error.GetType().Name);
        }
    }
    void Stop(string message) {
        if(finished) return; status.Text=message; stopping=true;
        if(!childStarted) {FinishBeforeChild();return;}
        if(stopSent) return; stopSent=true; stopAt=clock.Elapsed.TotalSeconds; view.Enabled=false;
        try {
            if(!child.HasExited) {
                if(Configured && serviceSession!=null) {child.StandardInput.WriteLine(new JavaScriptSerializer().Serialize(new Dictionary<string,object>{{"command","stop"},{"session",serviceSession}}));child.StandardInput.Flush();}
                else if(!Configured && worker!=null) {child.StandardInput.WriteLine(new JavaScriptSerializer().Serialize(new Dictionary<string,object>{{"command","stop"},{"worker_id",worker}})); child.StandardInput.Flush();}
                child.StandardInput.Close(); // EOF also stops before READY or when parent disappears.
            }
        } catch(Exception error) {Write("STOP_PIPE "+error.GetType().Name);}
    }
    void Tick(object sender,EventArgs args) {
        if(finished) return;
        double now=clock.Elapsed.TotalSeconds;
        if(Volatile.Read(ref logFailed)!=0 && !logFailureHandled) {
            logFailureHandled=true;failed=true;startupIssue="日志无法写入；请保留工程并检查目录空间/权限，后台正按原协议停止。";Stop(startupIssue);
            if(finished) return;
        }
        if(!childStarted) {
            if(!initialized && now>=30) {
                failed=true; finished=true; timer.Stop(); Write("WEBVIEW_INITIALIZATION_TIMEOUT");
                MessageBox.Show(this,"桌面窗口初始化超时；后台尚未启动。请保留 desktop.log。","Sim2Act",MessageBoxButtons.OK,MessageBoxIcon.Error);
                FinishBeforeChild();
            }
            return;
        }
        Stopwatch batch=Stopwatch.StartNew(); BackendLine line;
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
            if(origin==null && !userStopRequested) {
                failed=true;
                if(startupIssue==null) startupIssue="后台在工作台就绪前退出；请保留工程和 desktop.log。";
            }
            bool clean=receipt!=null && (Configured?ConfiguredStop(receipt):(True(receipt,"worker_stopped") && True(receipt,"clean") && True(receipt,"data_preserved")));
            ExitCode=child.ExitCode==0 && clean && !failed ? 0 : 1;
            Write(new JavaScriptSerializer().Serialize(new Dictionary<string,object>{{"event","DESKTOP_EXIT"},{"child_returncode",child.ExitCode},{"receipt_verified",clean},{"ready_seen",origin!=null},{"exitcode",ExitCode}}));
            if(Volatile.Read(ref logFailed)!=0) ExitCode=1;
            finished=true;
            if(ExitCode==0) ReleaseClaim();
            else {
                if(claim!=null) {claim.Dispose();claim=null;}
                MessageBox.Show(this,(startupIssue==null?"后台已退出，但未通过完整退出确认。":startupIssue)+"\n数据、运行锁和 desktop.log 已保留。","Sim2Act",MessageBoxButtons.OK,MessageBoxIcon.Error);
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
        if(disposing) {timer.Dispose(); lock(logGate) {if(log!=null) {try {log.Dispose();} catch(Exception) {Interlocked.Exchange(ref logFailed,1);} finally {log=null;}}} if(claim!=null) claim.Dispose(); if(child!=null) child.Dispose();}
        base.Dispose(disposing);
    }
}
