// Screen images, transitions and comparisons are projections of registered evidence.
let screenDiagram,screenSelection=null,lastScreenKey=null,screenMode="review",screenEdges="selected";
function screenNodeId(screen,reference){return 'screen:'+screen.id+':'+reference.state+':'+reference.viewport.width+'x'+reference.viewport.height}
function screenGraph(baseline){
  const groups=[],nodes=[],edges=[];let y=30;
  for(let row=0;row<Math.ceil(baseline.screens.length/2);row++){
    let height=0;
    for(let col=0;col<2;col++){
      const screen=baseline.screens[row*2+col];if(!screen)continue;const x=30+col*790,w=700,h=90+Math.ceil(screen.references.length/2)*310;
      groups.push({id:'screen:'+screen.id,title:screen.name,status:baseline.approval==='approved'?'done':'awaiting_approval',x,y,w,h,screenId:screen.id});
      screen.references.forEach((reference,index)=>{
        const stateName=screen.states.find(state=>state.id===reference.state)?.name||'Màn hình';
        nodes.push({id:screenNodeId(screen,reference),screenId:screen.id,reference,state:reference.state,title:stateName,typeLabel:reference.viewport.width+' × '+reference.viewport.height,kind:'screen',status:baseline.approval==='approved'?'done':'awaiting_approval',x:x+30+(index%2)*330,y:y+70+Math.floor(index/2)*310,w:310,h:285,image:reference.evidence_id});
      });height=Math.max(height,h);
    }y+=height+120;
  }
  for(const screen of baseline.screens)for(const edge of screen.transitions){
    for(const from of nodes.filter(node=>node.screenId===screen.id&&node.state===edge.from_state)){
      const to=nodes.find(node=>node.screenId===edge.to_screen&&node.state===edge.to_state&&node.reference.viewport.width===from.reference.viewport.width&&node.reference.viewport.height===from.reference.viewport.height)||nodes.find(node=>node.screenId===edge.to_screen&&node.state===edge.to_state);
      if(to)edges.push({from:from.id,to:to.id,dependency:true,label:screenActionLabel(edge.action),caption:screenActionLabel(edge.action)});
    }
  }
  return {groups,nodes,edges,width:1550,height:y,focus:nodes[0]?.id};
}
function imageEvidence(id,label){return id?'<a class="screen-image-link" href="/?evidence='+encodeURIComponent(id)+'" data-evidence="'+escape(id)+'"><img loading="lazy" src="/evidence/'+encodeURIComponent(id)+'" alt="'+escape(label)+'"><span>'+escape(label)+'</span></a>':'<div class="screen-empty-image">Chưa có ảnh để xem</div>'}
function setScreenMode(mode){
  screenMode=mode;$('#screen-layout').dataset.mode=mode;
  $('#screen-review-mode').setAttribute('aria-pressed',String(mode==='review'));$('#screen-flow-mode').setAttribute('aria-pressed',String(mode==='flow'));$('#screen-edge-control').hidden=mode!=='flow';
  lastScreenKey=null;if(state)renderScreens();
  if(mode==='flow')requestAnimationFrame(()=>screenDiagram?.focus());
}
function selectScreenReference(screen,reference){
  screenSelection=screenNodeId(screen,reference);renderScreens();if(screenMode==='flow')screenDiagram?.center(screenSelection);
}
function screenActionLabel(action){
  // Display provided natural labels; internal action codes are resolved in the spec.
  return /^[A-Z][A-Z0-9]*-[A-Z0-9]/.test(action)?'Chuyển trạng thái':action;
}
function renderScreenDetail(baseline,screen,reference){
  const design=state.tasks.find(task=>task.id==='design');
  const matching=state.tasks.filter(task=>task.status!=='superseded').flatMap(task=>(task.screen_comparisons?.comparisons||[]).filter(row=>row.screen_id===screen.id&&row.state===reference.state&&row.viewport.width===reference.viewport.width&&row.viewport.height===reference.viewport.height).map(row=>({task,row,report:task.screen_comparisons})));
  const referenceRecord=design?.evidence.find(record=>record.id===reference.evidence_id);
  const valid=matching.filter(item=>item.row.reference_sha256===referenceRecord?.sha256&&item.report.baseline_version===baseline.version);
  const observed=valid.find(item=>item.task.stage==='verify'&&item.report.current_source)||valid.find(item=>item.report.current_source)||valid.at(-1);
  const reviewed=observed&&observed.task.review?.decision==='approve'&&observed.task.status==='done';
  const visualStatus=!observed?'Chưa có giao diện thật để đối chiếu':!observed.report.current_source?'Ảnh giao diện thật thuộc phiên bản trước':observed.row.status==='needs_changes'?'Cần sửa sai lệch':reviewed?'Đã đối chiếu và review':'AI đã đối chiếu · Chờ review';
  const targetTasks=state.tasks.filter(task=>task.stage==='build'&&task.status!=='superseded'&&(task.screen_targets||[]).some(target=>target.screen_id===screen.id&&target.state===reference.state&&target.viewport.width===reference.viewport.width&&target.viewport.height===reference.viewport.height));
  const screenState=screen.states.find(item=>item.id===reference.state),specRecord=currentTaskRecords(design).find(item=>item.source.endsWith('/design.md'));
  const all=baseline.screens.flatMap(item=>item.references.map(ref=>({screen:item,reference:ref}))),index=all.findIndex(item=>screenNodeId(item.screen,item.reference)===screenSelection);
  $('#screen-navigation').innerHTML='<h3>Màn hình</h3>'+baseline.screens.map(item=>'<details '+(item.id===screen.id?'open':'')+'><summary>'+escape(item.name)+'<span class="muted">'+item.states.length+' trạng thái</span></summary>'+item.references.map(ref=>'<button class="screen-nav-item '+(screenNodeId(item,ref)===screenSelection?'selected':'')+'" aria-pressed="'+(screenNodeId(item,ref)===screenSelection)+'" data-reference="'+escape(screenNodeId(item,ref))+'"><strong>'+escape(item.states.find(state=>state.id===ref.state)?.name||'Ảnh thiết kế')+'</strong><span>'+ref.viewport.width+' × '+ref.viewport.height+'</span></button>').join('')+'</details>').join('');
  $('#screen-preview').innerHTML='<div class="row"><div><p class="muted">'+(index+1)+' / '+all.length+' ảnh tham chiếu</p><h2>'+escape(screen.name)+'</h2></div><div class="actions"><button id="screen-previous" '+(index===0?'disabled':'')+'>Trước</button><button id="screen-next" '+(index===all.length-1?'disabled':'')+'>Sau</button></div></div><label for="screen-reference">Trạng thái và kích thước</label><select id="screen-reference">'+screen.references.map(ref=>'<option value="'+escape(screenNodeId(screen,ref))+'" '+(screenNodeId(screen,ref)===screenSelection?'selected':'')+'>'+escape(screen.states.find(item=>item.id===ref.state)?.name||'Ảnh thiết kế')+' · '+ref.viewport.width+' × '+ref.viewport.height+'</option>').join('')+'</select><p class="small">'+escape(visualStatus)+(observed?'':' · Đây là mẫu thiết kế để bạn duyệt.')+'</p><div class="screen-pair '+(observed?'':'reference-only')+'">'+imageEvidence(reference.evidence_id,'Mẫu thiết kế')+(observed?imageEvidence(observed.row.evidence_id,'Giao diện thật'):'')+'</div>'+(observed?'<ul class="small">'+observed.row.observations.map(note=>'<li>'+escape(note)+'</li>').join(''):'');
  $('#screen-detail').innerHTML='<div class="row"><h2>Đặc tả & review</h2>'+badge(baseline.approval==='approved'?'done':'awaiting_approval')+'</div><p class="muted">'+(baseline.approval==='approved'?(baseline.approval_actor==='company'?'Bộ thiết kế đã được đội thiết kế chốt và review độc lập.':'Bộ thiết kế đã được bạn duyệt.'):'Xem đầu ra tại đây; chốt hoặc yêu cầu sửa trong Codex.')+'</p>'+(specRecord?'<a class="reader-link" href="/?evidence='+encodeURIComponent(specRecord.id)+'" data-evidence="'+escape(specRecord.id)+'">Đọc đặc tả màn hình và tương tác</a>':'')+'<h3>'+escape(screenState?.name||'Trạng thái đang xem')+'</h3><p>'+escape(screenState?.description||'Chưa có mô tả trạng thái.')+'</p><h3>Thao tác và đường chuyển</h3>'+(screen.transitions.filter(edge=>edge.from_state===reference.state).map(edge=>'<button class="screen-transition" data-screen-target="'+escape(edge.to_screen)+'" data-screen-state="'+escape(edge.to_state)+'"><strong>'+escape(screenActionLabel(edge.action))+'</strong><span>'+escape(baseline.screens.find(item=>item.id===edge.to_screen)?.name||'Màn hình tiếp theo')+' · '+escape(baseline.screens.find(item=>item.id===edge.to_screen)?.states.find(item=>item.id===edge.to_state)?.name||'')+'</span></button>').join('')||'<p class="muted">Không có đường chuyển được thiết kế cho trạng thái này.</p>')+'<details class="inspector-section"><summary>Tiêu chí và kết quả review</summary>'+design.criteria.map((criterion,i)=>'<p>'+escape(criterion)+' '+badge(design.review?.criteria?.find(row=>row.id==='C'+(i+1))?.passed?'done':'reported')+'</p>').join('')+'<p class="muted">'+(design.review?.decision==='approve'?'Bộ thiết kế đã qua review độc lập. Review này chưa chứng minh gameplay hoặc hiệu quả học tập.':'Chưa có kết luận review độc lập đạt.')+'</p></details><details class="inspector-section"><summary>Công việc và tài nguyên liên quan</summary>'+(targetTasks.map(task=>'<button class="screen-transition" data-screen-task="'+escape(task.id)+'"><strong>'+escape(task.title)+'</strong>'+badge(task.status)+'</button>').join('')||'<p class="muted">Công việc sẽ được liên kết khi có kế hoạch triển khai.</p>')+screen.assets.map(asset=>'<article class="item"><a href="/?evidence='+encodeURIComponent(asset.evidence_id)+'" data-evidence="'+escape(asset.evidence_id)+'">'+escape(asset.name)+'</a></article>').join('')+'</details>';
  $('#screen-reference').onchange=event=>{screenSelection=event.target.value;renderScreens();if(screenMode==='flow')screenDiagram?.center(screenSelection)};
  $('#screen-previous').onclick=()=>{const item=all[index-1];if(item)selectScreenReference(item.screen,item.reference)};$('#screen-next').onclick=()=>{const item=all[index+1];if(item)selectScreenReference(item.screen,item.reference)};
  document.querySelectorAll('[data-reference]').forEach(button=>button.onclick=()=>{screenSelection=button.dataset.reference;renderScreens()});
  document.querySelectorAll('[data-screen-target]').forEach(button=>button.onclick=()=>{const target=baseline.screens.find(item=>item.id===button.dataset.screenTarget),ref=target?.references.find(item=>item.state===button.dataset.screenState&&item.viewport.width===reference.viewport.width&&item.viewport.height===reference.viewport.height)||target?.references.find(item=>item.state===button.dataset.screenState);if(target&&ref)selectScreenReference(target,ref)});
  document.querySelectorAll('[data-screen-task]').forEach(button=>button.onclick=()=>chooseTask(button.dataset.screenTask));
}
function renderScreens(){
  const design=state.tasks.find(task=>task.id==='design'),baseline=design?.design_baseline;
  const key=JSON.stringify([baseline,state.tasks.map(task=>[task.id,task.status,task.screen_targets,task.screen_comparisons,task.review]),screenSelection,screenMode,screenEdges]);if(key===lastScreenKey)return;lastScreenKey=key;
  $('#screen-layout').dataset.mode=screenMode;
  if(!baseline?.screens?.length){
    $('#screen-layout').hidden=true;$('#screen-empty').hidden=false;$('#screen-summary').textContent='';
    $('#screen-empty').innerHTML='<h2>'+(!baseline?'Chưa có bộ thiết kế màn hình':baseline.has_ui?'Chưa có bộ ảnh theo từng màn hình':'Sản phẩm này không có giao diện')+'</h2><p>'+(!baseline?'Danh sách màn hình, trạng thái, ảnh thiết kế và đường chuyển sẽ xuất hiện khi bước UI/UX có đầu ra.':baseline.has_ui?'Bộ thiết kế hiện tại chỉ có mẫu tham chiếu chung.':'Quy trình sẽ kiểm chứng hợp đồng tương tác của sản phẩm thay cho ảnh giao diện.')+'</p>'+(baseline?.has_ui?'<button id="open-existing-design">Xem thiết kế hiện có</button>':'');
    if($('#open-existing-design'))$('#open-existing-design').onclick=()=>chooseTask('design');return;
  }
  $('#screen-layout').hidden=false;$('#screen-empty').hidden=true;
  const graph=screenGraph(baseline);if(!graph.nodes.some(node=>node.id===screenSelection))screenSelection=graph.nodes[0].id;
  const node=graph.nodes.find(item=>item.id===screenSelection),screen=baseline.screens.find(item=>item.id===node.screenId);
  if(screenMode==='flow'){
    if(!screenDiagram)screenDiagram=new DiagramCanvas($('#screen-map'),node=>{document.body.classList.remove('panels-right-hidden');updatePanelButtons();const baseline=state.tasks.find(task=>task.id==='design').design_baseline,screen=baseline.screens.find(item=>item.id===node.screenId),ref=node.reference||screen?.references[0];if(screen&&ref)selectScreenReference(screen,ref)});
    if(screenEdges==='selected')graph.edges=graph.edges.filter(edge=>edge.from===screenSelection||edge.to===screenSelection);
    screenDiagram.setData(graph,screenSelection);
  }
  renderScreenDetail(baseline,screen,node.reference);
  $('#screen-summary').textContent=baseline.screens.length+' màn hình · '+baseline.screens.reduce((count,item)=>count+item.states.length,0)+' trạng thái · '+graph.nodes.length+' ảnh tham chiếu · '+(baseline.approval==='approved'?(baseline.approval_actor==='company'?'Đội thiết kế đã chốt':'Đã duyệt'):'Chờ chốt thiết kế');
}
// View changes do not alter workflow decisions or recorded evidence.
document.addEventListener('DOMContentLoaded',()=>{
  $('#screen-review-mode').onclick=()=>setScreenMode('review');$('#screen-flow-mode').onclick=()=>setScreenMode('flow');$('#screen-edges').onchange=event=>{screenEdges=event.target.value;renderScreens()};
});
