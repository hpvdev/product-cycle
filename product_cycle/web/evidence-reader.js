// The reader displays registered evidence; it never changes or approves it.
function setView(next, scroll=true) {
  view=next;
  document.body.dataset.view=next;
  const pages={overview:['Tổng quan phát triển','Theo dõi tiến độ, kế hoạch và bằng chứng của sản phẩm.'],plan:['Kế hoạch phát triển','Từng đầu việc, điều kiện hoàn tất và các phụ thuộc cần xử lý.'],workflow:['Quy trình và công việc','Từ giai đoạn lớn đến công việc và từng bước thực hiện.'],documents:['Tài liệu & bằng chứng','Đọc đặc tả, thiết kế và đầu ra thực tế ngay trong không gian làm việc.'],services:['Dịch vụ & nền tảng','Theo dõi chuẩn bị dự án và cấu hình đã xác định trong thiết kế.'],history:['Nhật ký phát triển','Các mốc thực hiện, kiểm chứng và quyết định trong quá trình phát triển.']};
  $('#view-title').textContent=pages[next][0];
  $('#view-description').textContent=pages[next][1];
  document.querySelectorAll('.nav-link').forEach(button=>{const active=button.dataset.view===next;button.classList.toggle('active',active);if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current')});
  if(scroll)window.scrollTo({top:0,behavior:'smooth'});
}

function evidenceRecords() {
  return state.tasks.filter(task=>task.status!=='superseded').flatMap(task=>task.evidence.map(record=>({...record,taskTitle:task.title,stage:task.stage,current:record.revision===task.revision,taskStatus:task.status})));
}
function evidenceKind(record) {
  const source=record.source.toLowerCase();
  if(/\.(png|jpe?g|webp)$/.test(source))return 'Hình ảnh';
  if(/\.html?$/.test(source))return 'Mô hình giao diện';
  if(/\.json$/.test(source))return 'Tài liệu có cấu trúc';
  if(/\.md$/.test(source))return 'Tài liệu';
  if(/\.pdf$/.test(source))return 'Tài liệu PDF';
  if(record.kind==='check')return 'Kết quả kiểm tra';
  return 'Đầu ra';
}
function documentCard(record, title) {
  const isImage=/\.(png|jpe?g|webp)$/i.test(record.source);
  return '<button class="document-card" data-evidence="'+escape(record.id)+'"><span class="doc-kind">'+escape(evidenceKind(record))+'</span><strong>'+escape(title||record.description)+'</strong>'+(isImage?'<img loading="lazy" src="/evidence/'+encodeURIComponent(record.id)+'" alt="'+escape(record.description)+'">':title?'<div class="doc-excerpt">'+escape(record.description)+'</div>':'')+'<p>'+escape(phases[record.stage])+' · Phiên bản '+record.revision+(record.current?' · Hiện tại':' · Lần trước')+'</p><span class="muted">Mở để xem</span></button>';
}
let lastDocumentKey=null;
function renderDocuments() {
  const records=evidenceRecords();
  const key=JSON.stringify([evidenceFilter,records.map(record=>[record.id,record.sha256,record.current]),state.stages.map(stage=>stage.id)]);
  if(key===lastDocumentKey)return;
  lastDocumentKey=key;
  const picks=['analysis','design','plan'].map(stage=>stage==='design'?(records.find(e=>e.stage===stage&&e.current&&/\.(png|jpe?g|webp)$/i.test(e.source))||records.find(e=>e.stage===stage&&e.current&&/\.html$/i.test(e.source))):records.find(e=>e.stage===stage&&e.current&&e.kind==='artifact'&&e.source.endsWith(stage==='analysis'?'requirements.json':'plan.json'))).filter(Boolean);
  const titles={analysis:'Yêu cầu sản phẩm',design:'Thiết kế UX/UI',plan:'Kế hoạch triển khai'};
  $('#document-summary').innerHTML=picks.map(e=>documentCard(e,titles[e.stage])).join('')||'<p class="muted">Tài liệu sẽ xuất hiện khi các giai đoạn có đầu ra.</p>';
  $('#evidence-filter').innerHTML='<option value="all">Tất cả giai đoạn</option>'+state.stages.map(s=>'<option value="'+escape(s.id)+'">'+escape(s.title)+'</option>').join('');
  $('#evidence-filter').value=evidenceFilter;
  const visible=records.filter(record=>evidenceFilter==='all'||record.stage===evidenceFilter).sort((a,b)=>Number(b.current)-Number(a.current));
  $('#document-library').innerHTML=visible.map(e=>documentCard(e)).join('')||'<p class="muted">Chưa có bằng chứng ở giai đoạn này.</p>';
}

const readerLabels={product:'Sản phẩm',name:'Tên',title:'Tên',summary:'Tóm tắt',description:'Mô tả',requirements:'Yêu cầu sản phẩm',acceptance:'Tiêu chí nghiệm thu',criteria:'Điều kiện hoàn tất',scope:'Phạm vi',out_of_scope:'Ngoài phạm vi',non_goals:'Phần để sau',assumptions:'Giả định',risks:'Rủi ro',questions:'Câu hỏi cần làm rõ',open_questions:'Câu hỏi còn mở',users:'Người sử dụng',target_users:'Người sử dụng',goals:'Mục tiêu',flows:'Luồng sử dụng',states:'Trạng thái',rules:'Quy tắc thiết kế',reference:'Mốc tham khảo',reference_type:'Loại mốc tham khảo',reference_source:'Nguồn tham khảo',reference_evidence:'Bằng chứng tham khảo',approved:'Đã duyệt',owner_approval:'Quyết định của chủ sản phẩm',tasks:'Danh sách công việc',instructions:'Phạm vi thực hiện',deps:'Phụ thuộc',dependencies:'Phụ thuộc',checks:'Cách kiểm tra',services:'Dịch vụ',provider:'Nhà cung cấp',purpose:'Mục đích',inputs:'Đầu vào cần cấp',verification:'Cách kiểm chứng',delivery:'Bàn giao',access:'Cách sử dụng',limitations:'Hạn chế',findings:'Nhận xét',steps:'Các bước thực hiện',status:'Trạng thái',evidence:'Bằng chứng liên quan',notes:'Ghi chú',note:'Ghi chú',reason:'Lý do',id:'Mã tham chiếu',version:'Phiên bản',source:'Nguồn',decision:'Quyết định',rationale:'Cơ sở lựa chọn',components:'Các thành phần',data:'Dữ liệu',model:'Model',effort:'Mức suy luận',architecture:'Thiết kế kỹ thuật',technology:'Công nghệ',stack:'Công nghệ',environment:'Môi trường',owner:'Người phụ trách',cost:'Chi phí',typography:'Kiểu chữ',colors:'Màu sắc',spacing:'Khoảng cách',responsive:'Bố cục thích ứng',motion:'Chuyển động',input:'Cách điều khiển',feedback:'Phản hồi',accessibility:'Khả năng tiếp cận',content:'Nội dung',final_browser_checks:'Kiểm chứng trải nghiệm cuối cùng',browser_checks:'Kiểm chứng trải nghiệm',local:'Bản local',limits:'Giới hạn thực thi',recommendations:'Đề xuất',evaluation:'Đánh giá',success_criteria:'Điều kiện thành công'};
function readerLabel(key){return readerLabels[key]||key.replace(/_/g,' ')}
function structuredContent(value, depth=0, key='') {
  if(value===null)return '<span class="muted">Chưa có thông tin</span>';
  if(typeof value==='boolean')return value?'Có':'Không';
  if(typeof value!=='object')return '<p>'+escape(key==='status'?(labels[value]||value):value)+'</p>';
  if(Array.isArray(value)) {
    if(!value.length)return '<p class="muted">Không có mục nào.</p>';
    if(value.every(item=>item===null||typeof item!=='object'))return '<ul>'+value.map(item=>'<li>'+escape(item??'Chưa có thông tin')+'</li>').join('')+'</ul>';
    return value.map((item,index)=>{
      const headingKey=['title','description','name'].find(field=>item?.[field]);
      const fields=item&&typeof item==='object'?Object.fromEntries(Object.entries(item).filter(([field])=>field!==headingKey)):item;
      return '<section class="record"><h3>'+escape(headingKey?item[headingKey]:'Mục '+(index+1))+'</h3>'+structuredContent(fields,depth+1)+'</section>';
    }).join('');
  }
  return '<dl>'+Object.entries(value).map(([field,item])=>{
    const nested=typeof item==='object'&&item!==null&&depth>1&&!(Array.isArray(item)&&item.every(entry=>entry===null||typeof entry!=='object'));
    return '<dt>'+escape(readerLabel(field))+'</dt><dd>'+(nested?'<details><summary>Xem '+escape(readerLabel(field).toLowerCase())+'</summary>'+structuredContent(item,depth+1,field)+'</details>':structuredContent(item,depth+1,field))+'</dd>';
  }).join('')+'</dl>';
}
function markdownInline(text) {
  return escape(text).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,'<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
}
function markdownContent(text) {
  const lines=text.split(/\r?\n/),parts=[];
  let code=null,list=null,table=[];
  function closeList(){if(list){parts.push('</'+list+'>');list=null}}
  function closeTable(){if(table.length){const rows=table.filter(line=>!/^\s*\|?\s*:?-{3}/.test(line));parts.push('<div class="table-scroll"><table>'+rows.map((line,index)=>'<tr>'+line.trim().replace(/^\||\|$/g,'').split('|').map(cell=>'<'+(index?'td':'th')+'>'+markdownInline(cell.trim())+'</'+(index?'td':'th')+'>').join('')+'</tr>').join('')+'</table></div>');table=[]}}
  for(const line of lines){
    if(/^\s*```/.test(line)){closeList();closeTable();if(code===null)code=[];else{parts.push('<pre><code>'+escape(code.join('\n'))+'</code></pre>');code=null}continue}
    if(code!==null){code.push(line);continue}
    if(/^\s*\|.+\|\s*$/.test(line)){closeList();table.push(line);continue}closeTable();
    const heading=line.match(/^(#{1,6})\s+(.+)$/),bullet=line.match(/^\s*([-*]|\d+\.)\s+(.+)$/);
    if(bullet){const tag=/\d/.test(bullet[1])?'ol':'ul';if(list!==tag){closeList();parts.push('<'+tag+'>');list=tag}parts.push('<li>'+markdownInline(bullet[2])+'</li>');continue}
    closeList();if(heading)parts.push('<h'+heading[1].length+'>'+markdownInline(heading[2])+'</h'+heading[1].length+'>');else if(line.trim())parts.push('<p>'+markdownInline(line)+'</p>');
  }
  closeList();closeTable();if(code!==null)parts.push('<pre><code>'+escape(code.join('\n'))+'</code></pre>');return parts.join('');
}
function previewDocument(text) {
  const doc=new DOMParser().parseFromString(text,'text/html');
  doc.querySelectorAll('script[src],iframe,object,embed,base,link,meta[http-equiv],form').forEach(element=>element.remove());
  doc.querySelectorAll('*').forEach(element=>{
    [...element.attributes].forEach(attribute=>{if(['href','action','formaction','srcset','srcdoc'].includes(attribute.name))element.removeAttribute(attribute.name)});
    if(element.hasAttribute('src')&&!element.getAttribute('src').startsWith('data:image/'))element.removeAttribute('src');
  });
  return '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; form-action \'none\'; base-uri \'none\'">'+doc.documentElement.outerHTML;
}
async function openEvidence(id) {
  const record=evidenceRecords().find(e=>e.id===id);
  const request=++viewerRequest;
  openedEvidence=id;
  const modal=$('#evidence-viewer');
  $('#evidence-title').textContent=record?.description||'Bằng chứng không còn trong danh sách hiện tại';
  $('#evidence-kind').textContent=record?record.taskTitle+' · '+evidenceKind(record)+' · Phiên bản '+record.revision:'Đọc bằng chứng';
  const original=$('#evidence-original');original.hidden=!record;if(record)original.href='/evidence/'+encodeURIComponent(id);
  $('#evidence-content').innerHTML='<p class="muted">Đang mở tài liệu…</p>';
  if(!modal.open)modal.showModal();
  $('.viewer-body').scrollTop=0;
  const url=new URL(location.href);url.searchParams.set('evidence',id);history.replaceState(null,'',url);
  if(!record){$('#evidence-content').textContent='Không tìm thấy bằng chứng này. Hãy chọn một tài liệu trong thư viện.';return}
  try {
    const response=await fetch('/evidence/'+encodeURIComponent(id));
    if(!response.ok)throw Error();
    const data=await response.arrayBuffer();
    if(request!==viewerRequest)return;
    const source=record.source.toLowerCase(),text=new TextDecoder().decode(data);
    let content;
    if(/\.(png|jpe?g|webp)$/.test(source))content='<img src="/evidence/'+encodeURIComponent(id)+'" alt="'+escape(record.description)+'">';
    else if(/\.json$/.test(source))content=structuredContent(JSON.parse(text));
    else if(/\.md$/.test(source))content=markdownContent(text);
    else if(/\.html?$/.test(source))content='<p class="muted">Mô hình chạy trong khung xem riêng. Đây là thiết kế tham khảo, chưa phải sản phẩm đã nghiệm thu.</p><iframe sandbox="allow-scripts" referrerpolicy="no-referrer" title="Mô hình giao diện" srcdoc="'+escape(previewDocument(text))+'"></iframe>';
    else if(/\.pdf$/.test(source))content='<p>Tài liệu PDF được mở bằng trình đọc của trình duyệt.</p><a href="/evidence/'+encodeURIComponent(id)+'" target="_blank" rel="noopener">Đọc tài liệu PDF</a>';
    else content='<pre>'+escape(text)+'</pre>';
    $('#evidence-content').innerHTML=content+'<details class="provenance"><summary>Nguồn và đối chiếu bằng chứng</summary><dl><dt>Công việc</dt><dd>'+escape(record.taskTitle)+'</dd><dt>Phiên bản</dt><dd>'+record.revision+'</dd><dt>Người tạo</dt><dd>'+escape(sources[record.producer]||'Chưa ghi nhận')+'</dd><dt>Tệp gốc</dt><dd>'+escape(record.source)+'</dd><dt>Mã đối chiếu nội dung</dt><dd>'+escape(record.sha256)+'</dd></dl><p>Trình đọc chỉ thay đổi cách trình bày. Kết luận kiểm chứng và tệp gốc được giữ nguyên.</p></details>';
  } catch {
    if(request===viewerRequest)$('#evidence-content').textContent='Chưa mở được bằng chứng này. Tài liệu có thể không còn khớp với bản đã lưu; hãy kiểm tra lại trước khi nghiệm thu.';
  }
}
