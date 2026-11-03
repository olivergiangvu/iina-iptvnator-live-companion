"use strict";
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/../main.js','utf8');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function check(url,shouldPoll=true) {
  const requests=[],actions=[],downloads=[],events=[];
  const title='US: MeTV Toons - The Jetsons';
  const ev={};
  const c={iina:{
    core:{status:{url,title}},
    mpv:{getString:k=>k==='force-media-title'?title:k==='vid'?'1':'',getNative:()=>[],
      set:(...a)=>actions.push(a),command:(...a)=>actions.push(a)},
    event:{on:(n,f)=>ev[n]=f},
    http:{get:async u=>{requests.push(u);return{statusCode:200,data:{
      matched:true,isLiveView:true,channelName:'US: MeTV Toons',epgTitle:'The Jetsons',
      epgStart:'',epgEnd:'',hasLogo:true,logoTag:'verified',logoExt:'.png'
    }}},download:async u=>{downloads.push(u);return true}},
    file:{exists:()=>true},utils:{resolvePath:()=>'/tmp/logo.png'},
    menu:{item:(n,f,o)=>({action:f,selected:o.selected}),addItem:()=>{},forceUpdate:()=>{}},
    console:{log:()=>{}}
  },Date,Promise,setInterval:()=>1,setTimeout:(f,n)=>setTimeout(f,Math.min(n,20)),clearTimeout};
  vm.runInNewContext(source,c);
  ev['mpv.file-loaded']();await wait(85);
  if(!shouldPoll){assert.equal(requests.length,0);return;}
  assert(requests.length>0);
  const u=new URL(requests[0]);
  assert.equal(u.searchParams.get('playback'),'catchup');
  assert.equal(u.searchParams.get('stream_id'),'120');
  assert.equal(u.searchParams.get('title_hint'),title);
  assert(!requests.join('').includes('PASSWORD'));
  assert(actions.some(a=>a[0]==='file-local-options/force-media-title'&&a[1]==='US: MeTV Toons · The Jetsons'));
  assert(actions.some(a=>a[0]==='video-add'&&a[1][1]==='auto+attached-picture'));
  assert(downloads.length>0);
  assert.equal(new URL(downloads[0]).searchParams.get('playback'),'catchup');
}
(async()=>{
  await check('http://example.invalid/timeshift/USERNAME/PASSWORD/30/2026-11-02:22-30/120.ts');
  await check('http://example.invalid/streaming/timeshift.php?username=USERNAME&password=PASSWORD&stream=120&start=2026-11-02&duration=30');
  await check('http://example.invalid/movie/USERNAME/PASSWORD/120.mp4',false);
  await check('http://example.invalid/series/USERNAME/PASSWORD/120.mp4',false);
  await check('http://example.invalid/timeshift/USERNAME/PASSWORD/30/start/120.ts?token=xx');
  await check('http://example.invalid/streaming/timeshift.php?username=USERNAME&stream=120&password=PASSWORD');
  await check('http://example.invalid/streaming/timeshift.php?stream=bad',false);
  console.log('PASS: Catch-up REST + legacy, archive title, logo, VOD isolation');
})().catch(e=>{console.error(e);process.exitCode=1});
