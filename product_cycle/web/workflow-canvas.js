// Read-only diagrams share viewport controls; all status comes from recorded cycle data.
class DiagramCanvas {
  constructor(host, select) {
    this.host=host; this.fullscreenTarget=host.closest('.columns,.graph-layout')||host; this.select=select; this.x=24; this.y=24; this.zoom=1; this.initialized=false; this.key=null;
    host.innerHTML='<div class="diagram-toolbar"><span class="diagram-help">Kéo nền để di chuyển · Chọn nút để xem</span><div class="actions"><button data-map="fit">Vừa khung</button><button data-map="focus">Đến phần đang xem</button><button data-map="minus" aria-label="Thu nhỏ">−</button><output class="diagram-zoom" aria-label="Mức thu phóng">100%</output><button data-map="plus" aria-label="Phóng to">+</button><button data-map="details" aria-expanded="true">Ẩn chi tiết</button><button data-map="full">Toàn màn hình</button></div></div><div class="diagram-viewport" tabindex="0" aria-label="Sơ đồ có thể di chuyển và thu phóng"><div class="diagram-world"></div><button class="diagram-minimap" aria-label="Xem toàn bộ sơ đồ"></button></div>';
    this.viewport=host.querySelector('.diagram-viewport'); this.world=host.querySelector('.diagram-world');
    host.querySelector('[data-map="fit"]').onclick=()=>this.fit();
    host.querySelector('[data-map="focus"]').onclick=()=>this.focus();
    host.querySelector('[data-map="minus"]').onclick=()=>this.scale(this.zoom/1.2);
    host.querySelector('[data-map="plus"]').onclick=()=>this.scale(this.zoom*1.2);
    document.addEventListener('fullscreenchange',()=>{host.querySelector('[data-map="full"]').textContent=document.fullscreenElement===this.fullscreenTarget?'Thoát toàn màn hình':'Toàn màn hình'});
    host.querySelector('[data-map="full"]').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await this.fullscreenTarget.requestFullscreen()}catch{host.querySelector('.diagram-help').textContent='Có thể mở rộng vùng xem bằng cách thu nhỏ sơ đồ.'}};
    host.querySelector('[data-map="details"]').onclick=()=>{document.body.classList.toggle('panels-right-hidden');updatePanelButtons()};
    updatePanelButtons();
    host.querySelector('.diagram-minimap').onclick=()=>this.fit();
    this.viewport.addEventListener('pointerdown',event=>{
      if(event.button!==0||event.target.closest('button'))return;
      this.drag={startX:event.clientX,startY:event.clientY,x:this.x,y:this.y};this.viewport.setPointerCapture(event.pointerId);this.viewport.classList.add('dragging');
    });
    this.viewport.addEventListener('pointermove',event=>{if(this.drag){this.x=this.drag.x+event.clientX-this.drag.startX;this.y=this.drag.y+event.clientY-this.drag.startY;this.apply()}});
    const release=()=>{this.drag=null;this.viewport.classList.remove('dragging')};
    this.viewport.addEventListener('pointerup',release);this.viewport.addEventListener('pointercancel',release);
    this.viewport.addEventListener('wheel',event=>{event.preventDefault();if(event.ctrlKey||event.metaKey)this.scale(this.zoom*Math.exp(-event.deltaY*.003),event.offsetX,event.offsetY);else{this.x-=event.deltaX;this.y-=event.deltaY;this.apply()}},{passive:false});
    this.viewport.addEventListener('keydown',event=>{
      if(event.target!==this.viewport)return;
      if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','-','0'].includes(event.key))event.preventDefault();
      if(event.key==='+')this.scale(this.zoom*1.2);if(event.key==='-')this.scale(this.zoom/1.2);if(event.key==='0')this.fit();
      if(event.key==='ArrowLeft')this.x+=80;if(event.key==='ArrowRight')this.x-=80;if(event.key==='ArrowUp')this.y+=80;if(event.key==='ArrowDown')this.y-=80;this.apply();
    });
    this.world.addEventListener('click',event=>{const button=event.target.closest('[data-node]');if(button){const node=this.graph.nodes.find(node=>node.id===button.dataset.node)||this.graph.groups.find(group=>group.id===button.dataset.node);if(node)this.select(node)}});
    this.world.addEventListener('focusin',event=>{const button=event.target.closest('[data-node]');if(button&&button.matches(':focus-visible'))this.center(button.dataset.node,false)});
    this.observer=new ResizeObserver(()=>{this.resize();if(this.graph&&!this.initialized&&this.viewport.clientWidth)this.focus();else this.apply()});this.observer.observe(this.viewport);
    window.addEventListener('resize',()=>this.resize());
  }
  resize(){if(!this.viewport.clientWidth)return;const height=Math.max(320,window.innerHeight-this.viewport.getBoundingClientRect().top-20);if(this.viewport.style.height!==height+'px')this.viewport.style.height=height+'px';this.host.closest('.columns,.graph-layout')?.style.setProperty('--diagram-height',(height+this.host.querySelector('.diagram-toolbar').offsetHeight)+'px')}
  setData(graph, selected) {
    this.graph=graph;this.selected=selected;const key=JSON.stringify(graph);
    if(key!==this.key){
      this.key=key;
      const byId=new Map([...graph.groups,...graph.nodes].map(node=>[node.id,node]));
      const paths=graph.edges.map(edge=>{const from=byId.get(edge.from),to=byId.get(edge.to);if(!from||!to)return '';
        let d;const fy=from.y+from.h/2,ty=to.y+to.h/2;
        if(from.id===to.id){const ax=from.x+from.w,ay=fy-18;d=`M${ax},${ay} C${ax+85},${ay-75} ${ax+85},${ay+75} ${ax},${fy+18}`}
        else if(Math.abs(fy-ty)<25){const right=to.x>from.x,ax=right?from.x+from.w:from.x,bx=right?to.x:to.x+to.w;d=`M${ax},${fy} C${(ax+bx)/2},${fy} ${(ax+bx)/2},${ty} ${bx},${ty}`}
        else{const ax=from.x+from.w/2,ay=to.y>from.y?from.y+from.h:from.y,bx=to.x+to.w/2,by=to.y>from.y?to.y:to.y+to.h;d=`M${ax},${ay} C${ax},${(ay+by)/2} ${bx},${(ay+by)/2} ${bx},${by}`}
        return (edge.caption?'<text x="'+((from.x+to.x+from.w)/2)+'" y="'+((fy+ty)/2-12)+'" text-anchor="middle">'+escape(edge.caption)+'</text>':'')+'<path d="'+d+'" class="'+(edge.dependency?'dependency':'sequence')+'" marker-end="url(#'+hostId(this.host)+'-arrow)"/><title>'+escape(edge.label||'')+'</title>';
      }).join('');
      this.world.style.width=graph.width+'px';this.world.style.height=graph.height+'px';
      this.world.innerHTML='<svg class="diagram-lines" width="'+graph.width+'" height="'+graph.height+'" aria-hidden="true"><defs><marker id="'+hostId(this.host)+'-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z"/></marker></defs>'+paths+'</svg>'+graph.groups.map(group=>'<section class="diagram-group" style="left:'+group.x+'px;top:'+group.y+'px;width:'+group.w+'px;height:'+group.h+'px"><button class="diagram-group-title" data-node="'+escape(group.id)+'"><strong>'+escape(group.title)+'</strong>'+badge(group.status)+'</button></section>').join('')+graph.nodes.map(node=>'<button class="diagram-node '+escape(node.kind||'step')+'" data-node="'+escape(node.id)+'" style="left:'+node.x+'px;top:'+node.y+'px;width:'+node.w+'px;height:'+node.h+'px"><span class="node-type">'+escape(node.typeLabel||'Bước nhỏ')+'</span><strong>'+escape(node.title)+'</strong>'+(node.image?'<img loading="lazy" draggable="false" src="/evidence/'+encodeURIComponent(node.image)+'" alt="'+escape(node.title)+'">':'')+'<span class="node-bottom">'+badge(node.status)+'<span>'+escape(node.subtitle||'')+'</span></span></button>').join('');
    }
    this.world.querySelectorAll('[data-node]').forEach(button=>{button.classList.toggle('selected',button.dataset.node===selected);button.setAttribute('aria-pressed',String(button.dataset.node===selected))});
    if(!this.initialized&&this.viewport.clientWidth)this.focus();else this.apply();
  }
  center(id, reset=true) {
    const node=[...this.graph.nodes,...this.graph.groups].find(node=>node.id===id)||this.graph.groups[0]||this.graph.nodes[0];if(!node)return;
    if(reset)this.zoom=Math.max(.85,Math.min(1,(this.viewport.clientWidth-60)/node.w,(this.viewport.clientHeight-60)/node.h));
    this.x=node.w*this.zoom>this.viewport.clientWidth-60?30-node.x*this.zoom:this.viewport.clientWidth/2-(node.x+node.w/2)*this.zoom;this.y=node.h*this.zoom>this.viewport.clientHeight-60?30-node.y*this.zoom:this.viewport.clientHeight/2-(node.y+node.h/2)*this.zoom;this.initialized=true;this.apply();
  }
  focus(){if(this.graph)this.center(this.selected||this.graph.focus)}
  fit(){if(!this.graph)return;this.zoom=Math.max(.02,Math.min(1,(this.viewport.clientWidth-48)/this.graph.width,(this.viewport.clientHeight-48)/this.graph.height));this.x=(this.viewport.clientWidth-this.graph.width*this.zoom)/2;this.y=(this.viewport.clientHeight-this.graph.height*this.zoom)/2;this.initialized=true;this.apply()}
  scale(value,anchorX=this.viewport.clientWidth/2,anchorY=this.viewport.clientHeight/2){const next=Math.max(.02,Math.min(2,value)),ratio=next/this.zoom;this.x=anchorX-(anchorX-this.x)*ratio;this.y=anchorY-(anchorY-this.y)*ratio;this.zoom=next;this.apply()}
  apply(){this.world.style.transform=`translate(${this.x}px,${this.y}px) scale(${this.zoom})`;this.host.querySelector('.diagram-zoom').textContent=Math.round(this.zoom*100)+'%';if(!this.graph)return;const g=this.graph;this.host.querySelector('.diagram-minimap').innerHTML='<svg viewBox="0 0 '+g.width+' '+g.height+'" aria-hidden="true">'+g.groups.map(node=>'<rect x="'+node.x+'" y="'+node.y+'" width="'+node.w+'" height="'+node.h+'"/>').join('')+'<rect class="map-position" x="'+(-this.x/this.zoom)+'" y="'+(-this.y/this.zoom)+'" width="'+this.viewport.clientWidth/this.zoom+'" height="'+this.viewport.clientHeight/this.zoom+'"/></svg>'}
}
function hostId(host){return host.id.replace(/[^a-z0-9-]/gi,'')}

function workflowGraph() {
  const groups=[],nodes=[],edges=[],taskNodes=new Map();let y=30;const width=760,gap=100;
  const stages=Object.keys(phases).map(id=>state.stages.find(stage=>stage.id===id)||{id,title:phases[id],status:'not_required',steps:[]});
  for(let row=0;row<Math.ceil(stages.length/3);row++){
    let maxHeight=0;
    for(let col=0;col<3;col++){
      const index=row*3+col,stage=stages[index];if(!stage)continue;
      const x=30+col*(width+gap),groupId='stage:'+stage.id;
      const children=state.tasks.filter(task=>task.stage===stage.id&&task.status!=='superseded');let laneY=y+65;
      const lanes=children.length?children:[{id:null,title:stage.status==='not_required'?'Không yêu cầu trong kế hoạch':'Chờ xác định công việc',status:stage.status,steps:stage.steps}];
      for(const task of lanes){
        const taskId=groupId+':task:'+(task.id||'planned'),header={id:taskId,taskId:task.id,stageId:stage.id,title:task.title,status:task.status,kind:'work',typeLabel:'Công việc',x:x+250,y:laneY,w:240,h:112,subtitle:task.id||stage.status==='not_required'?'':'Sau khi chốt kế hoạch'};
        nodes.push(header);if(task.id)taskNodes.set(task.id,taskId);let previous=header.id;
        task.steps.forEach((step,i)=>{
          const r=Math.floor(i/3),c=r%2?2-i%3:i%3;
          const node={id:taskId+':step:'+step.id,taskId:task.id,stageId:stage.id,stepId:step.id,title:step.title,status:step.status,kind:'step',typeLabel:'Bước nhỏ '+String(i+1).padStart(2,'0'),x:x+30+c*240,y:laneY+150+r*160,w:220,h:132,subtitle:step.evidence?.length?step.evidence.length+' bằng chứng':''};
          nodes.push(node);edges.push({from:previous,to:node.id,label:'Thứ tự bước trong công việc'});previous=node.id;
        });
        laneY+=150+Math.ceil(task.steps.length/3)*160+30;
      }
      const height=laneY-y;groups.push({id:groupId,stageId:stage.id,title:String(index+1).padStart(2,'0')+' · '+stage.title,status:stage.status,x,y,w:width,h:height});maxHeight=Math.max(maxHeight,height);
    }
    y+=maxHeight+120;
  }
  for(const task of state.tasks.filter(task=>task.status!=='superseded'))for(const dep of task.deps){
    if(taskNodes.has(dep)&&taskNodes.has(task.id))edges.push({from:taskNodes.get(dep),to:taskNodes.get(task.id),dependency:true,label:'Phụ thuộc công việc'});
  }
  const current=state.tasks.find(task=>task.id===state.execution.task_id)||state.tasks.find(task=>['running','blocked','awaiting_approval','reviewing','rework'].includes(task.status));
  return {groups,nodes,edges,width:3*(width+gap)-gap+60,height:y,focus:'stage:'+(current?.stage||'analysis')};
}
let workflowDiagram,workflowSelection=null;
function renderWorkflowMap(){
  if(!workflowDiagram)workflowDiagram=new DiagramCanvas($('#workflow-map'),node=>{workflowSelection=node.id;document.body.classList.remove('panels-right-hidden');updatePanelButtons();selectedStage=node.stageId;selectedProposal=null;selected=node.taskId||state.tasks.find(task=>task.stage===node.stageId&&task.status!=='superseded')?.id||null;selectedStep=node.stepId||null;render()});
  const graph=workflowGraph(),taskPrefix='stage:'+selectedStage+':task:'+selected;
  const selection=selectedStep?taskPrefix+':step:'+selectedStep:selected?'stage:'+selectedStage:graph.focus;
  workflowDiagram.setData(graph,workflowSelection&&[...graph.nodes,...graph.groups].some(node=>node.id===workflowSelection)?workflowSelection:selection);
}
