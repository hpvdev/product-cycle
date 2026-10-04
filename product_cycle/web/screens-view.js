// Screen images, transitions and comparisons are projections of registered evidence.
let screenDiagram,screenSelection=null,lastScreenKey=null;
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
      if(to)edges.push({from:from.id,to:to.id,dependency:true,label:edge.action,caption:edge.action});
    }
  }
  return {groups,nodes,edges,width:1550,height:y,focus:nodes[0]?.id};
}
function imageEvidence(id,label){return id?'<a class="screen-image-link" href="/?evidence='+encodeURIComponent(id)+'" data-evidence="'+escape(id)+'"><img loading="lazy" src="/evidence/'+encodeURIComponent(id)+'" alt="'+escape(label)+'"><span>'+escape(label)+'</span></a>':'<div class="screen-empty-image">Chưa có ảnh để xem</div>'}
function renderScreenDetail(baseline,screen,reference){
  const matching=state.tasks.filter(task=>task.status!=='superseded').flatMap(task=>(task.screen_comparisons?.comparisons||[]).filter(row=>row.screen_id===screen.id&&row.state===reference.state&&row.viewport.width===reference.viewport.width&&row.viewport.height===reference.viewport.height).map(row=>({task,row,report:task.screen_comparisons})));
  const referenceRecord=state.tasks.find(task=>task.id==='design')?.evidence.find(record=>record.id===reference.evidence_id);
  const valid=matching.filter(item=>item.row.reference_sha256===referenceRecord?.sha256&&item.report.baseline_version===baseline.version);
  const observed=valid.find(item=>item.task.stage==='verify'&&item.report.current_source)||valid.find(item=>item.report.current_source)||valid.at(-1);
  const reviewed=observed&&observed.task.review?.decision==='approve'&&observed.task.status==='done';
  const visualStatus=!observed?'Chưa có ảnh giao diện thật':!observed.report.current_source?'Ảnh của phiên bản trước':observed.row.status==='needs_changes'?'Cần sửa sai lệch':reviewed?'Đã đối chiếu và review':'AI đã đối chiếu · Chờ review';
  const targetTasks=state.tasks.filter(task=>task.stage==='build'&&task.status!=='superseded'&&(task.screen_targets||[]).some(target=>target.screen_id===screen.id&&target.state===reference.state&&target.viewport.width===reference.viewport.width&&target.viewport.height===reference.viewport.height));
  $('#screen-detail').innerHTML='<div class="row"><h2>'+escape(screen.name)+'</h2>'+badge(baseline.approval==='approved'?'done':'awaiting_approval')+'</div><p class="muted">'+(baseline.approval==='approved'?'Bộ thiết kế đã được bạn duyệt.':'Bộ thiết kế đang chờ bạn chốt trong Codex.')+'</p><label for="screen-reference">Trạng thái và kích thước</label><select id="screen-reference">'+screen.references.map(ref=>'<option value="'+escape(screenNodeId(screen,ref))+'" '+(screenNodeId(screen,ref)===screenSelection?'selected':'')+'>'+escape(screen.states.find(state=>state.id===ref.state)?.name||ref.state)+' · '+ref.viewport.width+' × '+ref.viewport.height+'</option>').join('')+'</select><p>'+escape(screen.states.find(state=>state.id===reference.state)?.description||'')+'</p><h3>Thiết kế và giao diện thật</h3><p class="small">'+escape(visualStatus)+'. Kiểm chứng chức năng được ghi riêng trong công việc.</p><div class="screen-pair">'+imageEvidence(reference.evidence_id,'Mẫu thiết kế')+imageEvidence(observed?.row.evidence_id,'Giao diện thật')+'</div>'+(observed?'<ul class="small">'+observed.row.observations.map(note=>'<li>'+escape(note)+'</li>').join('')+'</ul>':'')+'<h3>Thao tác và đường chuyển</h3>'+(screen.transitions.filter(edge=>edge.from_state===reference.state).map(edge=>'<button class="screen-transition" data-screen-target="'+escape(edge.to_screen)+'" data-screen-state="'+escape(edge.to_state)+'"><strong>'+escape(edge.action)+'</strong><span>'+escape(baseline.screens.find(item=>item.id===edge.to_screen)?.name||'Màn hình tiếp theo')+' · '+escape(baseline.screens.find(item=>item.id===edge.to_screen)?.states.find(state=>state.id===edge.to_state)?.name||'')+'</span></button>').join('')||'<p class="muted">Không có đường chuyển được thiết kế cho trạng thái này.</p>')+'<h3>Công việc liên quan</h3>'+(targetTasks.map(task=>'<button class="screen-transition" data-screen-task="'+escape(task.id)+'"><strong>'+escape(task.title)+'</strong>'+badge(task.status)+'</button>').join('')||'<p class="muted">Chưa có công việc gắn với mẫu này.</p>')+'<h3>Tài nguyên dùng trong màn hình</h3>'+(screen.assets.map(asset=>'<article class="item"><a href="/?evidence='+encodeURIComponent(asset.evidence_id)+'" data-evidence="'+escape(asset.evidence_id)+'">'+escape(asset.name)+'</a><p class="small">'+escape(asset.usage)+'</p></article>').join('')||'<p class="muted">Màn hình này không yêu cầu hình ảnh riêng.</p>');
  $('#screen-reference').onchange=event=>{screenSelection=event.target.value;renderScreens();screenDiagram.center(screenSelection)};
  document.querySelectorAll('[data-screen-target]').forEach(button=>button.onclick=()=>{const target=baseline.screens.find(screen=>screen.id===button.dataset.screenTarget),ref=target?.references.find(ref=>ref.state===button.dataset.screenState);if(target&&ref){screenSelection=screenNodeId(target,ref);renderScreens();screenDiagram.center(screenSelection)}});
  document.querySelectorAll('[data-screen-task]').forEach(button=>button.onclick=()=>chooseTask(button.dataset.screenTask));
}
function renderScreens(){
  const design=state.tasks.find(task=>task.id==='design'),baseline=design?.design_baseline;
  const key=JSON.stringify([baseline,state.tasks.map(task=>[task.id,task.status,task.screen_targets,task.screen_comparisons,task.review]),screenSelection]);if(key===lastScreenKey)return;lastScreenKey=key;
  if(!baseline?.screens?.length){
    $('#screen-layout').hidden=true;
    $('#screen-empty').hidden=false;
    $('#screen-empty').innerHTML='<h2>'+(!baseline?'Chưa có bộ thiết kế màn hình':baseline.has_ui?'Chưa có bộ ảnh theo từng màn hình':'Sản phẩm này không có giao diện')+'</h2><p>'+(!baseline?'Danh sách màn hình, trạng thái, ảnh thiết kế và đường chuyển sẽ xuất hiện khi bước UI/UX có đầu ra.':baseline.has_ui?'Bộ thiết kế hiện tại chỉ có mẫu tham chiếu chung. Chưa thể xác nhận ảnh của từng màn hình hoặc các đường chuyển từ dữ liệu này.':'Quy trình sẽ kiểm chứng hợp đồng tương tác của sản phẩm thay cho ảnh giao diện.')+'</p>'+(baseline?.has_ui?'<button id="open-existing-design">Xem thiết kế hiện có</button>':'')+'<p class="muted">Thiết kế và quyết định được trao đổi trong Codex; dashboard hiển thị kết quả đã ghi nhận.</p>';
    if($('#open-existing-design'))$('#open-existing-design').onclick=()=>chooseTask('design');return;
  }
  $('#screen-layout').hidden=false;$('#screen-empty').hidden=true;
  if(!screenDiagram)screenDiagram=new DiagramCanvas($('#screen-map'),node=>{document.body.classList.remove('panels-right-hidden');updatePanelButtons();const baseline=state.tasks.find(task=>task.id==='design').design_baseline;const screen=baseline.screens.find(screen=>screen.id===node.screenId),reference=node.reference||screen?.references[0];if(screen&&reference){screenSelection=screenNodeId(screen,reference);renderScreens()}});
  const graph=screenGraph(baseline);if(!graph.nodes.some(node=>node.id===screenSelection))screenSelection=graph.nodes[0].id;
  screenDiagram.setData(graph,screenSelection);
  const node=graph.nodes.find(node=>node.id===screenSelection),screen=baseline.screens.find(screen=>screen.id===node.screenId);renderScreenDetail(baseline,screen,node.reference);
  $('#screen-summary').textContent=baseline.screens.length+' màn hình · '+graph.nodes.length+' mẫu trạng thái · '+graph.edges.length+' đường chuyển · '+(baseline.approval==='approved'?'Bạn đã duyệt bộ thiết kế':'Chờ bạn duyệt bộ thiết kế');
}
