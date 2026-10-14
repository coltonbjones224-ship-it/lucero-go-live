// Lucero GO iPhone widget — Scriptable
// Set FEED_URL to a public HTTPS URL hosting your exported JSON.
const FEED_URL = '';
const fallback = [{id:'Red',views:3250,color:'#e53935'},{id:'Green',views:2780,color:'#16a34a'},{id:'Orange',views:2290,color:'#f28c28'},{id:'Yellow',views:1950,color:'#e7c72b'},{id:'Purple',views:1760,color:'#9b59d0'}];
let lines=fallback,day='Day 1',source='Sample Day 1';
if(FEED_URL){try{let json=await new Request(FEED_URL).loadJSON();let last=json.days[json.days.length-1];lines=[...last.lines].sort((a,b)=>b.views-a.views).slice(0,5);day=last.date;source='Published feed'}catch(e){source='Offline sample'}}
let w=new ListWidget();w.backgroundColor=new Color('#14201c');w.setPadding(14,14,14,14);let t=w.addText('🚇  LUCERO GO');t.font=Font.boldSystemFont(15);t.textColor=new Color('#b1f2cf');w.addSpacer(4);let sub=w.addText(day+'  ·  '+source);sub.font=Font.systemFont(10);sub.textColor=new Color('#a4b9b0');w.addSpacer(9);
for(let [i,r] of lines.entries()){let row=w.addStack();row.centerAlignContent();let a=row.addText((i+1)+'.  '+r.id);a.font=Font.mediumSystemFont(12);a.textColor=new Color(r.color||'#ffffff');row.addSpacer();let v=row.addText(Number(r.views).toLocaleString()+' views');v.font=Font.semiboldSystemFont(12);v.textColor=Color.white();if(i<lines.length-1)w.addSpacer(7)}w.addSpacer();let foot=w.addText('Simulated data • Not live vehicle tracking');foot.font=Font.systemFont(9);foot.textColor=new Color('#a4b9b0');Script.setWidget(w);Script.complete();
