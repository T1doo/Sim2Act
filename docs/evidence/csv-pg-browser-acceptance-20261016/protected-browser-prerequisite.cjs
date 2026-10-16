"use strict";
const fs = require("node:fs"), path = require("node:path");
const {chromium} = require("/workspace/Sim2Act/scripts/engineering-ci/node_modules/playwright-core");
const out = __dirname;
const removedSecurityDefaults = ['--enable-unsafe-swiftshader','--unsafely-disable-devtools-self-xss-warnings','--disable-ipc-flooding-protection','--disable-client-side-phishing-detection','--password-store=basic','--use-mock-keychain','--disable-features='+['AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose','DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter','PaintHolding','ThirdPartyStoragePartitioning','BlockOriginHeaderModificationOnRedirect','Translate','AutoDeElevate','OptimizationHints','msForceBrowserSignIn','msEdgeUpdateLaunchServicesPreferredVersion'].join(',')];
const proof = {kind:"actual installed Chromium prerequisite only", source:"f82869db2dbb53e1616f9c14b108696bb893662f", started_at:new Date().toISOString(), playwright_version:require("/workspace/Sim2Act/scripts/engineering-ci/node_modules/playwright-core/package.json").version, requested:{executablePath:"/usr/bin/chromium", chromiumSandbox:true, headless:true, timeout:20000, ignoreDefaultArgs:removedSecurityDefaults}, flow_status:"NOT_RUN", postgres_flow_status:"NOT_RUN", security_lowered:false, external_requests:0};
let browser;
(async()=>{
 try {
  browser=await chromium.launch(proof.requested);
  const cdp=await browser.newBrowserCDPSession();
  const args=(await cdp.send("Browser.getBrowserCommandLine")).arguments;
  proof.actual_command_line=args;
  if(args.some(a=>["--no-sandbox","--disable-setuid-sandbox","--disable-web-security","--ignore-certificate-errors","--single-process"].includes(a)))throw Error("Browser security arguments failed");
  proof.browser_version=browser.version();
  const context=await browser.newContext({bypassCSP:false});
  await context.route("**/*",r=>{proof.external_requests++;return r.abort();});
  const page=await context.newPage();
  await page.goto("about:blank");
  proof.status="PASS";
 }catch(error){proof.status="BLOCKED";proof.error=error.message;proof.error_type=error.name;process.exitCode=1;}
 finally{
  if(browser){await browser.close();proof.owned_browser_closed=true;}
  else proof.owned_browser_closed="launch did not return a browser handle; launcher cleanup recorded in original error";
  proof.finished_at=new Date().toISOString();
  fs.writeFileSync(path.join(out,"browser-prerequisite.json"),JSON.stringify(proof,null,2)+"\n");
  console.log(JSON.stringify(proof,null,2));
 }
})();
