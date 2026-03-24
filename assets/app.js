
function svgWrap(w,h,content){return `<svg class="chart" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">${content}</svg>`;}
function makeBarChart(elId, labels, values, options={}){
  const el=document.getElementById(elId); if(!el) return;
  const w=options.w||720, h=options.h||300, pad=options.pad||{t:20,r:16,b:56,l:52};
  const max=Math.max(...values)*1.15;
  const cw=w-pad.l-pad.r, ch=h-pad.t-pad.b;
  let parts=[`<rect x="0" y="0" width="${w}" height="${h}" rx="18" fill="transparent"/>`];
  for(let i=0;i<5;i++){
    const y=pad.t+ch*i/4;
    parts.push(`<line x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}" stroke="rgba(255,255,255,.08)"/>`);
    const v=(max*(1-i/4));
    parts.push(`<text x="${pad.l-10}" y="${y+4}" text-anchor="end" fill="#8fa0cc" font-size="12">${options.yFormatter?options.yFormatter(v):v.toFixed(0)}</text>`);
  }
  const gap=12, bw=(cw - gap*(values.length-1))/values.length;
  values.forEach((v,i)=>{
    const bh=ch*(v/max);
    const x=pad.l+i*(bw+gap), y=pad.t+ch-bh;
    parts.push(`<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="10" fill="${options.color||'#7ab7ff'}"/>`);
    parts.push(`<text x="${x+bw/2}" y="${y-8}" text-anchor="middle" fill="#dfe8ff" font-size="12">${options.valueFormatter?options.valueFormatter(v):v}</text>`);
    parts.push(`<text x="${x+bw/2}" y="${h-20}" text-anchor="middle" fill="#9eb0d7" font-size="12">${labels[i]}</text>`);
  });
  el.innerHTML = svgWrap(w,h,parts.join(''));
}
function makeDualLineChart(elId, labels, s1, s2, options={}){
  const el=document.getElementById(elId); if(!el) return;
  const w=options.w||720, h=options.h||300, pad=options.pad||{t:20,r:20,b:56,l:46};
  const all=s1.concat(s2), min=Math.min(...all)*0.95, max=Math.max(...all)*1.05;
  const cw=w-pad.l-pad.r, ch=h-pad.t-pad.b;
  const x=i=>pad.l + cw*(i/(labels.length-1));
  const y=v=>pad.t + ch*(1-(v-min)/(max-min || 1));
  let parts=[];
  for(let i=0;i<5;i++){
    const yy=pad.t+ch*i/4;
    const v=max-(max-min)*i/4;
    parts.push(`<line x1="${pad.l}" y1="${yy}" x2="${w-pad.r}" y2="${yy}" stroke="rgba(255,255,255,.08)"/>`);
    parts.push(`<text x="${pad.l-8}" y="${yy+4}" text-anchor="end" fill="#8fa0cc" font-size="12">${options.yFormatter?options.yFormatter(v):v.toFixed(0)}</text>`);
  }
  labels.forEach((lab,i)=>{
    const xx=x(i);
    parts.push(`<text x="${xx}" y="${h-20}" text-anchor="middle" fill="#9eb0d7" font-size="12">${lab}</text>`);
  });
  function path(vals){return vals.map((v,i)=>`${i?'L':'M'} ${x(i)} ${y(v)}`).join(' ');}
  parts.push(`<path d="${path(s1)}" fill="none" stroke="#7ab7ff" stroke-width="3"/>`);
  parts.push(`<path d="${path(s2)}" fill="none" stroke="#7ef0c3" stroke-width="3"/>`);
  s1.forEach((v,i)=>parts.push(`<circle cx="${x(i)}" cy="${y(v)}" r="4.5" fill="#7ab7ff"/>`));
  s2.forEach((v,i)=>parts.push(`<circle cx="${x(i)}" cy="${y(v)}" r="4.5" fill="#7ef0c3"/>`));
  el.innerHTML = svgWrap(w,h,parts.join(''));
}
document.addEventListener('DOMContentLoaded',()=>{
  makeBarChart('funnelChart',
    ['注册','首发','2周活跃','4周活跃','变现开通','稳定经营'],
    [100,80.6,69.7,45.7,31.6,15.0],
    {yFormatter:v=>`${Math.round(v)}%`, valueFormatter:v=>`${v.toFixed(1)}%`}
  );
  makeDualLineChart('cohortChart',
    ['04','05','06','07','08','09','10','11','12','01','02','03'],
    [45.5,46.2,45.4,45.7,45.1,45.0,44.9,45.7,44.5,44.8,45.7,47.1],
    [57.7,58.4,58.1,56.5,60.4,58.4,57.5,58.8,56.6,58.0,60.1,63.2],
    {yFormatter:v=>`${v.toFixed(0)}%`}
  );
  makeBarChart('topNChart', ['3000','3600','4200','5000','6000'], [14.9,12.2,9.4,7.0,4.9], {valueFormatter:v=>`${v.toFixed(1)}ppt`, yFormatter:v=>`${v.toFixed(0)}ppt`, color:'#7ef0c3'});
  makeBarChart('verticalChart',
    ['搞笑娱乐','数码科技','本地生活','生活方式','游戏','知识教育','美妆护肤','母婴'],
    [10.5,10.0,9.8,9.4,9.4,8.9,8.8,8.4],
    {w:900, valueFormatter:v=>`${v.toFixed(1)}ppt`, yFormatter:v=>`${v.toFixed(0)}ppt`}
  );
});
