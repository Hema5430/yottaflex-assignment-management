const $ = (s) => document.querySelector(s);
const state = { view: "home", role: "student", learnerId: "LRN-2026-000001", learner: null, overview: null, chat: [] };
const titles = {
  home: ["Your learning overview", "A clear view of assignments, submissions, and review activity."],
  assignments: ["My assignments", "Find the work you need to complete and submit."],
  submissions: ["My submissions", "Track attempts, grades, and instructor feedback."],
  reviews: ["Review workspace", "Review submissions and respond to learner requests."],
  assistant: ["YottaFlex AI assistant", "Ask about assignment workflows, grading policies, and data-quality findings."],
  audit: ["Activity history", "A transparent record of important workflow events."]
};
async function api(url, options={}) {
  const res = await fetch(url, {headers: {"Content-Type":"application/json"}, ...options});
  const data = await res.json().catch(()=>({detail:"Unexpected server response"}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}
function esc(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function fmtDate(v) { if(!v) return "Not set"; const d=new Date(v); return isNaN(d)?v:d.toLocaleDateString(undefined,{month:"short",day:"numeric",year:"numeric"}); }
function toast(msg) { const t=$("#toast"); t.textContent=msg; t.classList.add("show"); setTimeout(()=>t.classList.remove("show"),3200); }
function setView(view) {
  state.view=view;
  document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===view));
  $("#pageTitle").textContent=titles[view][0]; $("#pageSubtitle").textContent=titles[view][1];
  $("#identityBar").classList.toggle("hide", !["assignments","submissions","reviews"].includes(view) || state.role!=="student");
  render();
}
function setRole(role) {
  state.role=role;
  const isStudent=role==="student";
  $("#identityBar").classList.toggle("hide",!isStudent || !["assignments","submissions","reviews"].includes(state.view));
  $("#profileName").textContent=isStudent?(state.learner?.full_name || "Demo learner"):"Instructor workspace";
  $("#profileRole").textContent=isStudent?"Student workspace":role==="instructor"?"Instructor workspace":"Operations overview";
  $("#avatar").textContent=isStudent?"ST":role==="instructor"?"IN":"OP";
  document.querySelectorAll(".nav-item").forEach(b=>{
    const v=b.dataset.view;
    b.classList.toggle("hide", isStudent && v==="reviews");
    b.classList.toggle("hide", !isStudent && ["assignments","submissions"].includes(v));
  });
  if(!isStudent && ["assignments","submissions"].includes(state.view)) state.view="home";
  setView(state.view);
}
async function loadLearner() {
  const query=$("#learnerSearch").value.trim() || "LRN-2026-000001";
  const matches=await api("/api/learners?search="+encodeURIComponent(query)+"&limit=10");
  const exact=matches.find(x=>x.learner_id.toLowerCase()===query.toLowerCase()) || matches[0];
  if(!exact) throw new Error("No learner matched. Try a learner ID such as LRN-2026-000001.");
  state.learnerId=exact.learner_id; state.learner=exact;
  $("#learnerSearch").value=exact.learner_id;
  $("#profileName").textContent=exact.full_name; $("#avatar").textContent=exact.full_name.split(/\s+/).map(x=>x[0]).join("").slice(0,2).toUpperCase();
  toast("Loaded "+exact.full_name); render();
}
async function init() {
  try {
    state.overview=await api("/api/overview");
    const l=await api("/api/learners?search=LRN-2026-000001&limit=1");
    state.learner=l[0]||null;
    if(state.learner) $("#profileName").textContent=state.learner.full_name;
    render();
  } catch(e) {
    $("#content").innerHTML=`<div class="notice error">Unable to load the application: ${esc(e.message)}. Confirm that the API server is running from your project root.</div>`;
  }
}
async function render() {
  try {
    if(state.view==="home") return await renderHome();
    if(state.view==="assignments") return await renderAssignments();
    if(state.view==="submissions") return await renderSubmissions();
    if(state.view==="reviews") return await renderReviews();
    if(state.view==="assistant") return renderAssistant();
    if(state.view==="audit") return await renderAudit();
  } catch(e) { $("#content").innerHTML=`<div class="notice error">${esc(e.message)}</div>`; }
}
function metric(label,value,icon,note="From the current SQLite database") {
  return `<div class="metric"><div class="metric-top"><span>${esc(label)}</span><span class="metric-icon">${icon}</span></div><strong>${Number(value||0).toLocaleString()}</strong><small>${esc(note)}</small></div>`;
}
async function renderHome() {
  if(!state.overview) state.overview=await api("/api/overview");
  const m=state.overview.metrics, findings=state.overview.findings;
  const student=state.role==="student";
  $("#content").innerHTML=`
    <div class="section-heading"><div><h2>${student?"Welcome back":"Operations snapshot"}</h2><p>${student?"Pick up where you left off. Your coursework and feedback are in one place.":"Monitor workflow health, grading activity, and issues that need review."}</p></div><button class="btn btn-primary" onclick="setView('${student?"assignments":"reviews"}')">${student?"Browse assignments":"Open review queue"} <span>→</span></button></div>
    <div class="metrics">
      ${metric(student?"Available assignments":"Assignments",m.assignments,"▤")}
      ${metric(student?"Learners in platform":"Learners",m.learners,"♙")}
      ${metric(student?"Submission records":"Submissions",m.submissions,"↗")}
      ${metric(student?"Grade records":"Pending appeals",student?m.grades:m.pending_appeals,"✓",student?"Grading and feedback records":"Require instructor attention")}
    </div>
    <div class="grid-two">
      <section class="panel"><div class="section-heading"><div><h3>${student?"Continue your learning":"Data quality review"}</h3><p class="panel-subtitle">${student?"Quick access to your coursework.":"Rule-based findings that may require attention."}</p></div><span class="pill ${findings.length?"medium":"green"}">${findings.length} findings</span></div>
        ${student?`<div class="finding"><div class="finding-icon">▤</div><div><h4>Browse assignments</h4><p>See published assignments for your enrolled courses, with due dates and attempt limits.</p><button class="btn btn-quiet" style="margin-top:9px" onclick="setView('assignments')">View assignments →</button></div></div>
        <div class="finding"><div class="finding-icon">↗</div><div><h4>Check your submissions</h4><p>Review attempt history, scores, and instructor feedback.</p><button class="btn btn-quiet" style="margin-top:9px" onclick="setView('submissions')">View submissions →</button></div></div>`:
        findings.slice(0,5).map(f=>`<div class="finding"><div class="finding-icon">!</div><div style="flex:1"><h4>${esc(f.title)}</h4><p>${esc(f.description)}</p><div style="margin-top:7px"><span class="pill ${f.severity.toLowerCase()}">${esc(f.severity)} priority</span></div></div></div>`).join("")}
      </section>
      <section class="panel"><h3>${student?"Your workspace":"Workflow overview"}</h3><p class="panel-subtitle">${student?"Everything you need to complete your work.":"A snapshot of workflow activity and governance."}</p>
        <div class="finding"><div class="finding-icon">✦</div><div><h4>AI assignment assistant</h4><p>Ask questions about grading, submissions, appeals, and the review process.</p><button class="btn btn-quiet" style="margin-top:9px" onclick="setView('assistant')">Ask the assistant →</button></div></div>
        <div class="finding"><div class="finding-icon">◷</div><div><h4>Transparent activity history</h4><p>Important submissions and review decisions are recorded for traceability.</p><button class="btn btn-quiet" style="margin-top:9px" onclick="setView('audit')">View activity →</button></div></div>
        <div class="notice info">Synthetic demo data is used. Choose a learner profile above to explore student-specific workflows.</div>
      </section>
    </div>`;
}
async function renderAssignments() {
  const rows=await api("/api/assignments?learner_id="+encodeURIComponent(state.learnerId));
  $("#content").innerHTML=`<div class="section-heading"><div><h2>Published assignments</h2><p>Only assignments available to the selected learner's active course enrollments are shown.</p></div><span class="pill blue">${rows.length} available</span></div>
  <div class="cards">${rows.length?rows.map(a=>{
    const full=a.attempts_used>=a.max_attempts;
    return `<article class="assignment-card"><div class="assignment-top"><span class="course-label">${esc(a.course_name)}</span><span class="pill ${full?"":"green"}">${full?"Attempts used":"Open"}</span></div><div><h3>${esc(a.title)}</h3><p>${esc(a.description||"No additional instructions provided.")}</p></div><div class="assignment-meta"><span>◷ Due ${fmtDate(a.due_at)}</span><span>↻ ${a.attempts_used}/${a.max_attempts} attempts</span>${a.latest_score!==null?`<span>✓ Latest score ${a.latest_score}</span>`:""}</div>${a.latest_feedback?`<div class="notice info">${esc(a.latest_feedback)}</div>`:""}<div class="assignment-actions"><button class="btn btn-primary" ${full?"disabled":""} onclick="openSubmit('${esc(a.assignment_id)}','${esc(a.title)}')">${full?"Attempt limit reached":"Submit work"} →</button></div></article>`;
  }).join(""):`<div class="empty"><strong>No published assignments found</strong>Try loading another learner profile or check enrollment records.</div>`}</div>`;
}
window.openSubmit=(assignmentId,title)=>{
  $("#modalRoot")?.remove();
  const el=document.createElement("div");el.id="modalRoot";el.className="modal-backdrop";
  el.innerHTML=`<div class="modal"><div class="modal-head"><h2>Submit assignment</h2><button class="btn btn-quiet" onclick="document.getElementById('modalRoot').remove()">Close ✕</button></div><p class="muted">${esc(title)}</p><form id="submitForm"><div class="field"><label for="submissionContent">Your response / submission notes</label><textarea id="submissionContent" minlength="10" maxlength="20000" required placeholder="Write your response here (at least 10 characters)…"></textarea><small class="muted">This demo stores text in the local application database. Do not enter sensitive personal information.</small></div><div class="form-actions"><button class="btn btn-primary" type="submit">Submit work</button><button type="button" class="btn btn-quiet" onclick="document.getElementById('modalRoot').remove()">Cancel</button></div></form></div>`;
  document.body.appendChild(el);
  $("#submitForm").addEventListener("submit",async ev=>{
    ev.preventDefault();const btn=ev.submitter;btn.disabled=true;btn.textContent="Submitting…";
    try{const r=await api("/api/submissions",{method:"POST",body:JSON.stringify({learner_id:state.learnerId,assignment_id:assignmentId,content:$("#submissionContent").value})});el.remove();toast("Submission received · "+r.submission_id);state.overview=null;setView("submissions");}
    catch(e){btn.disabled=false;btn.textContent="Submit work";toast(e.message);}
  });
};
async function renderSubmissions() {
  const rows=await api("/api/submissions?learner_id="+encodeURIComponent(state.learnerId));
  $("#content").innerHTML=`<div class="section-heading"><div><h2>Submission history</h2><p>Track your attempts, grading outcomes, and instructor feedback.</p></div><button class="btn btn-primary" onclick="setView('assignments')">Browse assignments →</button></div>
  ${rows.length?`<div class="table-wrap"><table><thead><tr><th>Assignment</th><th>Attempt</th><th>Submitted</th><th>Status</th><th>Score</th><th>Feedback</th><th>Actions</th></tr></thead><tbody>${rows.map(s=>`<tr><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.course_name)}</span></td><td>${s.attempt_number}</td><td>${fmtDate(s.submitted_at)}${s.is_late?'<span class="pill high">Late</span>':''}</td><td><span class="pill ${s.status==="graded"?"green":s.status==="late"?"medium":"blue"}">${esc(s.status)}</span></td><td>${s.final_score===null?"Awaiting grade":`${s.final_score} / ${s.rubric_maximum??"—"}`}</td><td>${s.feedback?esc(s.feedback.slice(0,120)):"—"}</td><td><button class="btn btn-quiet" onclick="requestResubmission('${esc(s.submission_id)}')">Request resubmission</button> <button class="btn btn-outline" onclick="openAppeal('${esc(s.submission_id)}')">Appeal</button></td></tr>`).join("")}</tbody></table></div>`:`<div class="empty"><strong>No submissions yet</strong>Browse your assignments and submit your first piece of work.</div>`}`;
}
window.requestResubmission=async id=>{
  const reason=prompt("Why are you requesting a resubmission? (minimum 5 characters)");
  if(!reason)return;
  try{await api("/api/resubmission-requests",{method:"POST",body:JSON.stringify({learner_id:state.learnerId,original_submission_id:id,reason})});toast("Resubmission request sent to instructor.");renderSubmissions();}
  catch(e){toast(e.message);}
};
window.openAppeal=async id=>{
  const reason=prompt("Explain why you are appealing this grade (minimum 10 characters):");
  if(!reason)return;
  try{await api("/api/appeals",{method:"POST",body:JSON.stringify({learner_id:state.learnerId,submission_id:id,reason})});toast("Appeal submitted for review.");renderSubmissions();}
  catch(e){toast(e.message);}
};
async function renderReviews() {
  const q=await api("/api/instructor/queue");
  const rows=q.submissions;
  $("#content").innerHTML=`<div class="section-heading"><div><h2>Instructor review queue</h2><p>Review submissions, provide rubric-based scores, and respond to learner requests.</p></div><span class="pill blue">${rows.length} submissions</span></div>
  <div class="metrics">${metric("Awaiting grade",rows.filter(s=>!s.final_grade_count).length,"✎")}${metric("Late submissions",rows.filter(s=>s.is_late).length,"◷")}${metric("Pending resubmissions",q.resubmission_requests.length,"↻")}${metric("Pending appeals",q.appeals.length,"⚑")}</div>
  <section class="panel"><h3>Submissions to review</h3><p class="panel-subtitle">Select a submission to record a score and feedback.</p>
  ${rows.length?`<div class="table-wrap"><table><thead><tr><th>Learner</th><th>Assignment</th><th>Attempt</th><th>Submitted</th><th>Status</th><th>Score</th><th>Action</th></tr></thead><tbody>${rows.map(s=>`<tr><td><span class="cell-title">${esc(s.full_name)}</span><span class="cell-sub">${esc(s.learner_id)}</span></td><td>${esc(s.title)}<span class="cell-sub">${esc(s.course_name)}</span></td><td>${s.attempt_number}</td><td>${fmtDate(s.submitted_at)}</td><td><span class="pill ${s.is_late?"medium":"blue"}">${esc(s.status)}</span></td><td>${s.final_score===null?"Not graded":s.final_score+" / "+s.rubric_maximum}</td><td><button class="btn btn-primary" onclick="openGrade('${esc(s.submission_id)}','${esc(s.title)}',${Number(s.rubric_maximum||100)})">Review</button></td></tr>`).join("")}</tbody></table></div>`:`<div class="empty">No submissions in the current review queue.</div>`}</section>
  <div class="grid-two" style="margin-top:16px">
    <section class="panel"><h3>Resubmission requests</h3><p class="panel-subtitle">Approve or reject with a recorded reason.</p>${q.resubmission_requests.length?q.resubmission_requests.map(r=>`<div class="finding"><div style="flex:1"><h4>${esc(r.full_name)} · ${esc(r.title)}</h4><p>${esc(r.reason)}</p><small class="muted">${fmtDate(r.created_at)}</small><div class="assignment-actions" style="margin-top:9px"><button class="btn btn-primary" onclick="decideResubmission('${esc(r.request_id)}','approved')">Approve</button><button class="btn btn-danger" onclick="decideResubmission('${esc(r.request_id)}','rejected')">Reject</button></div></div></div>`).join(""):`<div class="empty">No pending requests.</div>`}</section>
    <section class="panel"><h3>Grade appeals</h3><p class="panel-subtitle">Record an uphold or reject decision.</p>${q.appeals.length?q.appeals.map(a=>`<div class="finding"><div style="flex:1"><h4>${esc(a.full_name)} · ${esc(a.title)}</h4><p>${esc(a.reason)}</p><div class="assignment-actions" style="margin-top:9px"><button class="btn btn-primary" onclick="decideAppeal('${esc(a.appeal_id)}','upheld')">Uphold</button><button class="btn btn-danger" onclick="decideAppeal('${esc(a.appeal_id)}','rejected')">Reject</button></div></div></div>`).join(""):`<div class="empty">No pending appeals.</div>`}</section>
  </div>`;
}
window.openGrade=(id,title,max)=>{
  const el=document.createElement("div");el.id="gradeModal";el.className="modal-backdrop";
  el.innerHTML=`<div class="modal"><div class="modal-head"><h2>Review submission</h2><button class="btn btn-quiet" onclick="document.getElementById('gradeModal').remove()">Close ✕</button></div><p class="muted">${esc(title)} · Maximum score ${max}</p><form id="gradeForm"><div class="field"><label>Score (0–${max})</label><input id="score" type="number" min="0" max="${max}" step="0.5" required></div><div class="field"><label>Feedback for learner</label><textarea id="feedback" minlength="3" required placeholder="Share strengths and specific improvement suggestions…"></textarea></div><div class="form-actions"><button class="btn btn-primary" type="submit">Save grade & feedback</button></div></form></div>`;
  document.body.appendChild(el);
  $("#gradeForm").addEventListener("submit",async e=>{e.preventDefault();try{await api("/api/grades",{method:"POST",body:JSON.stringify({submission_id:id,raw_score:Number($("#score").value),feedback:$("#feedback").value})});el.remove();toast("Grade and feedback saved. Audit history recorded.");state.overview=null;renderReviews();}catch(err){toast(err.message);}});
};
window.decideResubmission=async(id,status)=>{
 const note=prompt("Optional reviewer note:")||"Reviewed by instructor.";
 try{await api(`/api/instructor/resubmissions/${encodeURIComponent(id)}/decision`,{method:"POST",body:JSON.stringify({status,reviewer_note:note})});toast("Resubmission request "+status+".");renderReviews();}
 catch(e){toast(e.message);}
};
window.decideAppeal=async(id,status)=>{
 const note=prompt("Decision explanation (required):");
 if(!note)return;
 try{await api(`/api/instructor/appeals/${encodeURIComponent(id)}/decision`,{method:"POST",body:JSON.stringify({status,decision:note})});toast("Appeal decision recorded.");renderReviews();}
 catch(e){toast(e.message);}
};
function renderAssistant() {
  $("#content").innerHTML=`<div class="section-heading"><div><h2>AI-powered workflow assistant</h2><p>Get plain-language guidance about assignments, grading, and detected data-quality findings.</p></div><span class="pill blue">Evidence-aware assistant</span></div>
  <div class="chat-layout"><section class="chatbox"><div class="chat-header"><div class="metric-icon">✦</div><div><strong>YottaFlex Assistant</strong><small>Groq-hosted model · deterministic fallback available</small></div><span class="pill green" style="margin-left:auto">Advisory</span></div><div id="chatMessages" class="chat-messages">${state.chat.length?state.chat.map(m=>`<div class="bubble ${m.role}">${esc(m.text)}</div>`).join(""):`<div class="bubble bot">Hi! I'm your YottaFlex assistant. I can explain how submissions, grading, resubmissions, appeals, and anomaly reviews work. I won't change grades or make decisions on behalf of an instructor.</div>`}</div><form id="chatForm" class="chat-input"><input id="chatQuestion" placeholder="Ask about an assignment or review issue…" maxlength="2000" required><button class="btn btn-primary">Send ↑</button></form></section>
  <aside><div class="side-tip"><h4>Try asking</h4><p>Use one of these prompts to explore the assistant.</p><div class="quick-prompts"><button class="quick-prompt" data-prompt="Explain the grade review process.">Grade review process</button><button class="quick-prompt" data-prompt="What should a reviewer do when a score exceeds the rubric maximum?">Score anomaly</button><button class="quick-prompt" data-prompt="How does a learner request a resubmission?">Resubmission</button><button class="quick-prompt" data-prompt="Why is an audit trail important for grade appeals?">Audit trail</button></div></div><div class="panel"><h3>Responsible AI</h3><p class="panel-subtitle">AI explains and assists. Python rules and instructor decisions remain authoritative.</p><div class="notice info">Never submit private student data or secrets to the AI assistant. Answers are advisory and should be checked against the assignment policy.</div></div></aside></div>`;
  $("#chatForm").addEventListener("submit",async e=>{
    e.preventDefault();const q=$("#chatQuestion").value.trim();if(!q)return;
    state.chat.push({role:"user",text:q});renderAssistant();const input=$("#chatQuestion");input.disabled=true;
    const msgs=$("#chatMessages");msgs.insertAdjacentHTML("beforeend",`<div class="bubble bot" id="typing">Thinking…</div>`);msgs.scrollTop=msgs.scrollHeight;
    try {
      const context={role:state.role, learner_id:state.learnerId, findings:state.overview?.findings||[], workflow_summary:"The application supports published assignments, submissions, rubric-based grades and feedback, resubmission requests, grade appeals, and audit history."};
      const answer=await api("/api/ai/chat",{method:"POST",body:JSON.stringify({question:q,context})});
      state.chat.push({role:"bot",text:answer.answer||"No answer returned."});
    } catch(err) { state.chat.push({role:"bot",text:"I couldn't reach the AI provider: "+err.message+". You can still use the application workflows; check GROQ_API_KEY configuration."}); }
    renderAssistant();
    const m=$("#chatMessages");m.scrollTop=m.scrollHeight;
  });
  document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{$("#chatQuestion").value=b.dataset.prompt;$("#chatQuestion").focus();}));
  const cm=$("#chatMessages");cm.scrollTop=cm.scrollHeight;
}
async function renderAudit() {
  const rows=await api("/api/audit?limit=80");
  $("#content").innerHTML=`<div class="section-heading"><div><h2>Activity history</h2><p>Recent workflow changes recorded by the system.</p></div><span class="pill blue">${rows.length} events</span></div><section class="panel"><h3>Audit timeline</h3><p class="panel-subtitle">This timeline includes existing synthetic events and actions taken through the web app.</p>${rows.length?rows.map(r=>`<div class="audit-row"><div class="audit-dot"></div><div><strong>${esc(r.action.replace(/_/g," "))} · ${esc(r.entity_type)}</strong><p>${esc(r.reason||"Workflow event recorded.")}<br><span class="muted">Record: ${esc(r.entity_id)} · Actor: ${esc(r.actor_id||"System")}</span></p></div><time>${fmtDate(r.occurred_at)}</time></div>`).join(""):`<div class="empty">No audit events recorded.</div>`}</section>`;
}
$("#nav").addEventListener("click",e=>{const b=e.target.closest("[data-view]");if(b)setView(b.dataset.view);});
$("#roleSelect").addEventListener("change",e=>setRole(e.target.value));
$("#useLearner").addEventListener("click",()=>loadLearner().catch(e=>toast(e.message)));
setView("home");init();
