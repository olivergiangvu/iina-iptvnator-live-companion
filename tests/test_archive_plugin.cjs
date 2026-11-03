"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync(__dirname+"/../main.js","utf8");
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function verify(url,kind) {
  const urls=[],added=[],events={};
  const title="US: MeTV Toons";
  const ctx={iina:{
    core:{status:{url,title}},
    mpv:{getString:k=>k==="force-media-title"?title:k==="vid"?"1":"",getNative:()=>[],
      set:(...args)=>added.push(args),command:(n,args)=>added.push([n,args])},
    event:{on:(n,fn)=>events[n]=fn},
    http:{get:async u=>{urls.push(u);return{statusCode:200,data:{
      matched:true,isLiveView:true,source:"catchup-provider",channelName:title,
      epgTitle:"Wait Till Your Father Gets Home",epgStart:"2026-11-03T05:00:00Z",
      epgEnd:"2026-11-03T05:30:00Z",hasLogo:true,logoTag:"ok",logoExt:".png"
    }}},download:async u=>{urls.push(u);return true}},
    file:{exists:()=>true},utils:{resolvePath:()=>"/tmp/logo.png"},
    menu:{item:(name,action,opt)=>({selected:opt.selected,action}),addItem:()=>{},forceUpdate:()=>{}},
    console:{log:()=>{}}
  },Date,Promise,encodeURIComponent,
  setInterval:()=>1,setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,20)),clearTimeout};
  vm.runInNewContext(source,ctx);
  events["mpv.file-loaded"]();await pause(90);
  assert(urls.length>=2);
  for(const raw of urls){
    const parsed=new URL(raw);
    assert.equal(parsed.searchParams.get("playback"),"catchup");
    assert.equal(parsed.searchParams.get("stream_id"),"11590");
    assert.equal(parsed.searchParams.get("title_hint"),title);
    assert.equal(parsed.searchParams.get("archive_start"),"2026-11-03:05-00");
    assert(!raw.includes("SECRET"));
  }
  assert(added.some(x=>x[0]==="file-local-options/force-media-title"&&x[1].includes("Wait Till Your Father Gets Home")));
  assert(added.some(x=>x[0]==="file-local-options/force-media-title" &&
    /\(\d{1,2}:\d{2}–\d{1,2}:\d{2}\)/.test(x[1])),
    "archived show title must include scheduled broadcast hours");
  console.log("PASS:",kind,"channel-only title and sanitized archive time");
}
(async()=>{
 await verify("https://example.invalid/timeshift/USER/SECRET/30/2026-11-03:05-00/11590.ts","REST");
 await verify("https://example.invalid/streaming/timeshift.php?username=USER&password=SECRET&stream=11590&start=2026-11-03%3A05-00","Legacy");
})().catch(e=>{console.error(e);process.exitCode=1});
