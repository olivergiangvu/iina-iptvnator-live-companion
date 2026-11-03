"use strict";
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(__dirname + '/../main.js', 'utf8');
const events = {};
const requests = [];
let status = {
  matched:true, isLiveView:true, channelName:'US: A&E East',
  epgTitle:'Storage Wars', epgStart:'2026-11-02T15:30:00.000Z',
  epgEnd:'2026-11-02T16:00:00.000Z', hasLogo:true, logoTag:'aaa'
};
const changes = [];
const mpv = {
  getString: n => n === 'force-media-title' ? 'US: A&E East' : n === 'vid' ? '1' : '',
  getNative: () => [],
  set:(n,v)=>changes.push([n,v]),
  command:(n,args)=>changes.push([n,...args])
};
let interval;
const vars = {
  iina:{
    core:{status:{url:'http://meteor.invalid/live/USER/SECRET/120.ts',title:'US: A&E East'}},
    mpv,
    event:{on:(n,f)=>events[n]=f},
    http:{get:async url=>{ requests.push(url); return {statusCode:200,data:status}; },download:async()=>true},
    file:{exists:()=>true},
    utils:{resolvePath:()=>'/tmp/channel.png'},
    menu:{item:(t,f,o)=>({title:t,action:f,selected:o.selected}),addItem:()=>{},forceUpdate:()=>{}},
    console:{log:()=>{}}
  },
  setInterval:fn=>{interval=fn;return 1;},
  setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,20)),
  clearTimeout,
  Date, Promise,
};
vm.runInNewContext(source,vars,{filename:'main.js'});
const sleep = ms => new Promise(r=>setTimeout(r,ms));
(async()=>{
  events['mpv.file-loaded']();
  await sleep(80);
  assert(changes.some(x=>x[0]==='file-local-options/force-media-title' && x[1].includes('Storage Wars')));
  assert(requests.some(url => url.includes('title_hint=US%3A%20A%26E%20East')),
         'plugin must send initial title hint with the stream ID');
  assert(changes.some(x=>x[0]==='video-add' && x[2]==='auto+attached-picture'));
  const first = changes.filter(x=>x[0]==='file-local-options/force-media-title').length;
  status = {...status,epgStart:'2026-11-02T16:00:00.000Z',epgEnd:'2026-11-02T16:30:00.000Z'};
  interval(); await sleep(70);
  assert.equal(changes.filter(x=>x[0]==='file-local-options/force-media-title').length,first+1,
               'same show name but new EPG start triggers update');
  const after=changes.length;
  status={...status,matched:false};
  interval(); await sleep(70);
  assert.equal(changes.length,after,'unmatched program must not update IINA');
  console.log('PASS: title refresh across same-name programme, artwork, unmatched safety');
})().catch(e=>{console.error(e);process.exitCode=1});
