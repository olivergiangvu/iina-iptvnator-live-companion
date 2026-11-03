"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync(__dirname+"/../main.js","utf8");
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const data=(name,show,logo=false)=>({matched:true,isLiveView:true,
  channelName:name,epgTitle:show,epgStart:"",epgEnd:"",
  hasLogo:logo,logoTag:"logo",logoExt:".png"});
function setup(getHandler, downloadHandler, initial) {
  const calls=[],actions=[],events={}; let interval,now=1000000;
  const current={url:initial.url,title:initial.title};
  class Clock extends Date { static now() { return now; } }
  const ctx={iina:{
    core:{status:current},
    mpv:{getString:k=>k==="force-media-title"?current.title:k==="vid"?"1":"",getNative:()=>[],
      set:(...a)=>actions.push(a),command:(...a)=>actions.push(a)},
    event:{on:(name,cb)=>events[name]=cb},
    http:{get:u=>{calls.push(u);return getHandler(u);},
      download:(u,path)=>downloadHandler(u,path)},
    file:{exists:()=>true},utils:{resolvePath:()=>"/tmp/logo-test.png"},
    menu:{item:(name,cb,opt)=>({action:cb,selected:opt.selected}),addItem:()=>{},forceUpdate:()=>{}},
    console:{log:()=>{}}
  },Date:Clock,Promise,
  setInterval:cb=>{interval=cb;return 1;},
  setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,25)),clearTimeout};
  vm.runInNewContext(source,ctx);
  return {calls,actions,events,current,interval:()=>interval(),advance:n=>now+=n};
}
async function testQueuedChannel() {
  let finishOld;
  let count=0;
  const t=setup(u=>{
    count++;
    if(count===1) return new Promise(resolve=>finishOld=resolve);
    return Promise.resolve({statusCode:200,data:data("US: New","New Show")});
  },async()=>true,{url:"http://example.invalid/live/U/P/120.ts",title:"US: Old"});
  t.events["mpv.file-loaded"]();
  await sleep(5);
  t.current.url="http://example.invalid/live/U/P/121.ts";
  t.current.title="US: New";
  t.events["mpv.file-loaded"]();
  assert.equal(t.calls.length,1,"second channel queues during in-flight request");
  finishOld({statusCode:200,data:data("US: Old","Stale Show")});
  await sleep(90);
  assert.equal(t.calls.length,2,"queued channel sync must start without 10s polling wait");
  assert(t.actions.some(a=>a[0]==="file-local-options/force-media-title"&&a[1]==="US: New · New Show"));
  assert(!t.actions.some(a=>a[0]==="file-local-options/force-media-title"&&a[1].includes("Stale Show")));
}
async function testRetryArtwork() {
  let attempts=0;
  const t=setup(async()=>({statusCode:200,data:data("US: A&E","Program",true)}),
    async()=>{attempts++;if(attempts===1)throw Error("transient");return true;},
    {url:"http://example.invalid/live/U/P/120.ts",title:"US: A&E"});
  t.events["mpv.file-loaded"]();
  await sleep(70);
  assert.equal(attempts,1);
  t.advance(1000);t.interval();await sleep(40);
  assert.equal(attempts,1,"do not busy-loop after image failure");
  t.advance(7500);t.interval();await sleep(65);
  assert.equal(attempts,2,"retry logo on the next polling slot, not after 60 seconds");
  assert(t.actions.some(a=>a[0]==="video-add"),"successful retry must attach artwork");
}
(async()=>{
 await testQueuedChannel();
 await testRetryArtwork();
 console.log("PASS: new Live channel not delayed behind stale request; logo retry <10s");
})().catch(e=>{console.error(e);process.exitCode=1});
