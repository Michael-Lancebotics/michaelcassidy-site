// Minimal port of the Python belt calculator math and simple UI binding
(() => {
    const MCMASTER = {
        50: {part: "7947K711", length_mm:100},56:{part:"7947K712",length_mm:112},62:{part:"7947K713",length_mm:124},63:{part:"7947K714",length_mm:126},67:{part:"7947K715",length_mm:134},68:{part:"7947K716",length_mm:136},70:{part:"7947K717",length_mm:140},76:{part:"7947K718",length_mm:152},79:{part:"7947K719",length_mm:158},80:{part:"7947K721",length_mm:160},82:{part:"7947K722",length_mm:164},86:{part:"7947K725",length_mm:172},90:{part:"7947K726",length_mm:180},93:{part:"7947K727",length_mm:186},96:{part:"7947K728",length_mm:192},100:{part:"7947K729",length_mm:200},101:{part:"7947K731",length_mm:202},106:{part:"7947K732",length_mm:212},110:{part:"7947K733",length_mm:220},116:{part:"7947K734",length_mm:232},118:{part:"7947K735",length_mm:236},120:{part:"7947K736",length_mm:240},125:{part:"7947K737",length_mm:250},126:{part:"7947K738",length_mm:252},129:{part:"7947K739",length_mm:258},140:{part:"7947K741",length_mm:280},150:{part:"7947K742",length_mm:300},160:{part:"7947K743",length_mm:320},166:{part:"7947K744",length_mm:332},175:{part:"7947K745",length_mm:350},185:{part:"7947K746",length_mm:370},190:{part:"7947K747",length_mm:380},200:{part:"7947K748",length_mm:400},210:{part:"7947K749",length_mm:420},228:{part:"7947K751",length_mm:456},244:{part:"7947K753",length_mm:488},252:{part:"7947K754",length_mm:504},264:{part:"7947K755",length_mm:528},276:{part:"7947K756",length_mm:552},288:{part:"7947K757",length_mm:576},300:{part:"7947K758",length_mm:600},320:{part:"7947K759",length_mm:640},348:{part:"7947K761",length_mm:696},372:{part:"7947K762",length_mm:744},424:{part:"7947K763",length_mm:848},582:{part:"7947K764",length_mm:1164}
    };

    function mcmaster_part(belt_teeth, pitch, width){
        if (Math.abs(pitch-2.0)<1e-9 && Math.abs(width-6.0)<1e-9){
            const item = MCMASTER[belt_teeth];
            if (item) return {part:item.part, url:`https://www.mcmaster.com/${item.part}/`, note: 'McMaster 2MGT, 6 mm'};
        }
        return {part:'',url:'',note:'No match'};
    }

    function pitch_diameter(teeth,pitch){return teeth*pitch/Math.PI}
    function check_diameter(teeth,pitch,allow){return pitch_diameter(teeth,pitch)+allow}
    function parse_ratio(text){text=text.trim(); if (text.includes(':')){const [l,r]=text.split(':'); return parseFloat(l)/parseFloat(r);} return parseFloat(text)}
    function wrap_angles_rad(z1,z2,center,pitch){
        const d1=pitch_diameter(z1,pitch), d2=pitch_diameter(z2,pitch);
        const delta=Math.abs(d2-d1);
        if (center<=delta/2) throw new Error('Center too small');
        const beta=Math.asin(delta/(2*center));
        const small_wrap=Math.PI-2*beta, large_wrap=Math.PI+2*beta;
        return d1<=d2?[small_wrap,large_wrap]:[large_wrap,small_wrap];
    }
    function teeth_in_mesh(z,wrap){return z*wrap/(2*Math.PI)}

    function geometry_check(z1,z2,center,pitch,max1,max2,allow1,allow2,min_clear,min_mesh1,min_mesh2){
        if (z1<=0||z2<=0) return {ok:false,messages:['Pulley tooth counts must be positive.']};
        const pd1=pitch_diameter(z1,pitch), pd2=pitch_diameter(z2,pitch);
        const cd1=check_diameter(z1,pitch,allow1), cd2=check_diameter(z2,pitch,allow2);
        if (center<=Math.abs(pd2-pd1)/2) return {ok:false,messages:['No valid external tangent exists; center distance too small.'],pd1,pd2,cd1,cd2,clearance:center-(cd1+cd2)/2,mesh1:NaN,mesh2:NaN};
        const clearance=center-(cd1+cd2)/2;
        if (clearance<min_clear) return {ok:false,messages:[`Pulley checked diameters interfere: clearance=${clearance.toFixed(3)} mm`],pd1,pd2,cd1,cd2,clearance,mesh1:NaN,mesh2:NaN};
        if (max1!=null && cd1>max1) return {ok:false,messages:[`Pulley1 checked dia ${cd1.toFixed(3)} exceeds limit ${max1.toFixed(3)}`],pd1,pd2,cd1,cd2,clearance,mesh1:NaN,mesh2:NaN};
        if (max2!=null && cd2>max2) return {ok:false,messages:[`Pulley2 checked dia ${cd2.toFixed(3)} exceeds limit ${max2.toFixed(3)}`],pd1,pd2,cd1,cd2,clearance,mesh1:NaN,mesh2:NaN};
        const [wrap1,wrap2]=wrap_angles_rad(z1,z2,center,pitch);
        const mesh1=teeth_in_mesh(z1,wrap1), mesh2=teeth_in_mesh(z2,wrap2);
        if (mesh1<min_mesh1) return {ok:false,messages:[`Pulley1 has too few teeth in mesh: ${mesh1.toFixed(2)}`],pd1,pd2,cd1,cd2,clearance,mesh1,mesh2};
        if (mesh2<min_mesh2) return {ok:false,messages:[`Pulley2 has too few teeth in mesh: ${mesh2.toFixed(2)}`],pd1,pd2,cd1,cd2,clearance,mesh1,mesh2};
        const messages=[]; if (clearance<1.0) messages.push('Very low pulley body clearance'); if (mesh1<8) messages.push('Pulley1 low teeth in mesh'); if (mesh2<8) messages.push('Pulley2 low teeth in mesh');
        return {ok:true,messages,pd1,pd2,cd1,cd2,clearance,mesh1,mesh2};
    }

    function belt_length_for_center_distance(z1,z2,center,pitch){
        const d1=pitch_diameter(z1,pitch), d2=pitch_diameter(z2,pitch);
        const big=Math.max(d1,d2), small=Math.min(d1,d2);
        if (center<=(big-small)/2) throw new Error('Center too small');
        const alpha=Math.asin((big-small)/(2*center));
        const straight=2*Math.sqrt(center*center-((big-small)/2)**2);
        const arcs=(Math.PI/2)*(big+small)+alpha*(big-small);
        const length=straight+arcs; return {length_mm:length, ideal_teeth:length/pitch, nearest_teeth:Math.round(length/pitch)};
    }

    function center_distance_for_belt(z1,z2,belt_teeth,pitch){
        const target=belt_teeth*pitch; const d1=pitch_diameter(z1,pitch), d2=pitch_diameter(z2,pitch); const big=Math.max(d1,d2), small=Math.min(d1,d2);
        let minc=(big-small)/2+0.001; let maxc=Math.max(target/2,minc+1);
        function length_at(c){ const alpha=Math.asin(Math.max(-1,Math.min(1,(big-small)/(2*c)))); const straight=2*Math.sqrt(Math.max(0,c*c-((big-small)/2)**2)); return straight+(Math.PI/2)*(big+small)+alpha*(big-small); }
        if (length_at(minc)>target) throw new Error('Belt too short for these pulleys');
        for (let i=0;i<120;i++){ const mid=(minc+maxc)/2; if (length_at(mid)<target) minc=mid; else maxc=mid; }
        return {center_mm:(minc+maxc)/2, length_mm:target};
    }

    // Helpers
    function $(id){return document.getElementById(id)}
    function val(id){return $(id).value}

    function make_option(z1,z2,belt_teeth,desired_center,pitch,width,desired_ratio,constraints,only_catalog){
        const center=center_distance_for_belt(z1,z2,belt_teeth,pitch).center_mm;
        const [max1,max2,allow1,allow2,min_clear,min_mesh1,min_mesh2]=constraints;
        const geom=geometry_check(z1,z2,center,pitch,max1,max2,allow1,allow2,min_clear,min_mesh1,min_mesh2);
        if (!geom.ok) return null;
        const catalog=mcmaster_part(belt_teeth,pitch,width);
        if (only_catalog && !catalog.part) return null;
        const actual_ratio=z2/z1; const ratio_err=desired_ratio==null?0:100*(actual_ratio-desired_ratio)/desired_ratio;
        return {p1:z1,p2:z2,ratio:actual_ratio,ratio_err:belt_teeth?ratio_err:0,belt_teeth:length=belt_teeth,length_mm:belt_teeth*pitch,mcmaster_part:catalog.part,mcmaster_url:catalog.url,center:center,center_err:center-desired_center,pd1:geom.pd1,pd2:geom.pd2,cd1:geom.cd1,cd2:geom.cd2,clearance:geom.clearance,mesh1:geom.mesh1,mesh2:geom.mesh2,warnings:geom.messages.join('; ')};
    }

    function belt_teeth_to_search(z1,z2,desired_center,pitch,search_range,width,only_catalog){
        if (only_catalog && Math.abs(pitch-2.0)<1e-9 && Math.abs(width-6.0)<1e-9) return Object.keys(MCMASTER).map(k=>parseInt(k,10));
        const ideal=belt_length_for_center_distance(z1,z2,desired_center,pitch).ideal_teeth;
        const low=Math.max(1,Math.floor(ideal)-search_range); const high=Math.ceil(ideal)+search_range; const arr=[]; for(let i=low;i<=high;i++) arr.push(i); return arr;
    }

    // UI wiring
    const tableBody=document.querySelector('#results tbody'); const summary=document.getElementById('summary');

    function update_table(results){ tableBody.innerHTML=''; results.forEach(r=>{ const tr=document.createElement('tr'); tr.innerHTML=`<td>${r.p1}</td><td>${r.p2}</td><td>${r.ratio.toFixed(4)}:1</td><td>${r.ratio_err? (r.ratio_err>0?'+':'')+r.ratio_err.toFixed(3):'0.000'}</td><td>${r.belt_teeth}</td><td>${(r.length_mm||r.belt_teeth*parseFloat(val('pitch'))).toFixed(3)}</td><td>${r.mcmaster_part||''}</td><td>${r.mcmaster_url?`<a class="link" href="${r.mcmaster_url}" target="_blank">link</a>`:''}</td><td>${r.center.toFixed(3)}</td><td>${r.center_err>0?'+':''}${r.center_err.toFixed(3)}</td><td>${r.warnings||''}</td>`; tableBody.appendChild(tr); }); }

    function calculate(){
        try{
            const mode=document.querySelector('input[name=mode]:checked').value;
            const desired_center=parseFloat(val('center'));
            const pitch=parseFloat(val('pitch'));
            const width=parseFloat(val('width'));
            const search_range=parseInt(val('search_range'));
            const allow1=parseFloat(val('allow1'))||0; const allow2=parseFloat(val('allow2'))||0;
            const minmesh1=parseFloat(val('minmesh1'))||6; const minmesh2=parseFloat(val('minmesh2'))||6; const minclear=parseFloat(val('minclear'))||0;
            const only_catalog=$('only_catalog').checked;
            let results=[];
            if (mode==='fixed'){
                const z1=parseInt(val('min_driver')); const z2=parseInt(val('min_driven'));
                for(const bt of belt_teeth_to_search(z1,z2,desired_center,pitch,search_range,width,only_catalog)){
                    try{ const opt=make_option(z1,z2,bt,desired_center,pitch,width,null,[null,null,allow1,allow2,minclear,minmesh1,minmesh2],only_catalog); if (opt) results.push(opt);}catch(e){}
                }
                results.sort((a,b)=>Math.abs(a.center_err)-Math.abs(b.center_err));
            } else {
                const desired_ratio=parse_ratio(val('ratio'));
                const min_driver=parseInt(val('min_driver')), max_driver=parseInt(val('max_driver')); const min_driven=parseInt(val('min_driven')), max_driven=parseInt(val('max_driven'));
                const max_ratio_err=parseFloat(val('max_ratio_err'));
                for(let z1=min_driver;z1<=max_driver;z1++){
                    for(let z2=min_driven;z2<=max_driven;z2++){
                        const ratio_err=100*((z2/z1)-desired_ratio)/desired_ratio; if (Math.abs(ratio_err)>max_ratio_err) continue;
                        // quick geometry pre-screen
                        const pre=geometry_check(z1,z2,desired_center,pitch,null,null,allow1,allow2,minclear,minmesh1,minmesh2); if (!pre.ok) continue;
                        for(const bt of belt_teeth_to_search(z1,z2,desired_center,pitch,search_range,width,only_catalog)){
                            try{ const opt=make_option(z1,z2,bt,desired_center,pitch,width,desired_ratio,[null,null,allow1,allow2,minclear,minmesh1,minmesh2],only_catalog); if (opt){ opt.score=Math.abs(opt.center_err)+0.25*Math.abs(opt.ratio_err); results.push(opt);} }catch(e){}
                        }
                    }
                }
                results.sort((a,b)=> ( (a.score||Math.abs(a.center_err)) - (b.score||Math.abs(b.center_err)) )); results=results.slice(0,250);
            }
            update_table(results);
            if (!results.length) summary.textContent='No valid results found.'; else { const best=results[0]; summary.textContent=`Best: ${best.p1}T -> ${best.p2}T, ratio ${best.ratio.toFixed(4)}:1, belt ${best.belt_teeth||''}T, center ${best.center.toFixed(3)} mm (${best.center_err>0?'+':''}${best.center_err.toFixed(3)} mm)`; }
        }catch(err){ alert('Error: '+err.message); }
    }

    function exportCSV(){ const rows=[]; const headers=['p1','p2','ratio','ratio_err','belt_teeth','length_mm','mcmaster_part','mcmaster_url','center','center_err','warnings']; document.querySelectorAll('#results tbody tr').forEach(tr=>{ const cells=tr.children; const row={}; headers.forEach((h,i)=>{ row[h]=cells[i]?.innerText || ''; }); rows.push(row); }); if (!rows.length){ alert('No results'); return;} const csv=[headers.join(',')].concat(rows.map(r=>headers.map(h=>`"${String(r[h]).replace(/"/g,'""')}"`).join(','))).join('\n'); const blob=new Blob([csv],{type:'text/csv'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='belt_results.csv'; a.click(); URL.revokeObjectURL(url);} 

    document.getElementById('calc').addEventListener('click', calculate);
    document.getElementById('export').addEventListener('click', exportCSV);
    // initial run
    calculate();
})();
