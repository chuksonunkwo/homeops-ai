const state = {
  jobId: null,
  job: null,
  lastAction: null,
  transcript: [],
  comparisonOpen: false,
};

const el = id => document.getElementById(id);
const landingView = el('landing-view');
const caseView = el('case-view');
const startForm = el('start-form');
const startMessage = el('start-message');
const chatForm = el('chat-form');
const messageInput = el('message');
const resetBtn = el('reset-btn');
const latestUpdate = el('latest-update');
const conversationLog = el('conversation-log');
const suggestionsEl = el('suggestions');
const decisionCard = el('decision-card');
const decisionContent = el('decision-content');
const decisionLoading = el('decision-loading');
const decisionActions = el('decision-actions');
const decisionDetail = el('decision-detail');
const comparisonSection = el('comparison-section');
const judgeView = el('judge-view');
const judgeToggle = el('judge-toggle');
const judgeClose = el('judge-close');
const bedrockTestBtn = el('bedrock-test');
const toast = el('toast');

function money(value) {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  return `${number < 0 ? '-' : ''}$${Math.abs(number).toFixed(2)}`;
}

function titleCase(value = '') {
  return String(value).replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

function serviceLabel(job) {
  const category = (job?.category || '').toLowerCase();
  if (category === 'hvac') return 'Air conditioning repair';
  if (category === 'plumbing') return 'Plumbing repair';
  return category ? `${titleCase(category)} service` : 'Home repair';
}

function selectedQuote(job) {
  return job?.quotes?.find(q => q.provider_id === job.selected_provider_id) || null;
}

function recommendedQuote(job) {
  if (!job?.quotes?.length) return null;
  return job.quotes.find(q => q.recommendation === 'BEST_VALUE')
    || [...job.quotes].sort((a, b) => Number(b.score || 0) - Number(a.score || 0))[0];
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 4000);
}

function setLoading(isLoading, copy = 'Understanding your request and checking suitable options.') {
  decisionCard.setAttribute('aria-busy', String(isLoading));
  decisionLoading.hidden = !isLoading;
  decisionContent.hidden = isLoading;
  el('loading-copy').textContent = copy;
  startMessage.disabled = isLoading;
  messageInput.disabled = isLoading;
}

function addTranscript(role, text) {
  if (!text) return;
  state.transcript.push({ role, text });
  renderConversationLog();
}

function renderConversationLog() {
  conversationLog.innerHTML = '';
  state.transcript.forEach(item => {
    const row = document.createElement('div');
    row.className = `log-message ${item.role}`;
    const label = document.createElement('span');
    label.textContent = item.role === 'user' ? 'You' : 'HomeOps';
    const copy = document.createElement('p');
    copy.textContent = item.text;
    row.append(label, copy);
    conversationLog.appendChild(row);
  });
  conversationLog.scrollTop = conversationLog.scrollHeight;
}

function updateLatest(text) {
  const copy = latestUpdate.querySelector('p');
  copy.textContent = text || 'HomeOps is ready.';
}

function setCaseHeader(job, action) {
  el('case-title').textContent = serviceLabel(job);
  el('case-subtitle').textContent = job?.issue || 'HomeOps is working on your request.';
  const status = el('user-status');
  status.className = 'user-status';

  if (action === 'EMERGENCY_ESCALATION') {
    status.textContent = 'Safety alert';
    status.classList.add('attention');
  } else if (job?.status === 'CLOSED') {
    status.textContent = 'Complete';
    status.classList.add('good');
  } else if (job?.status === 'INVOICE_REVIEW' && job?.latest_invoice?.decision === 'HOLD_FOR_APPROVAL') {
    status.textContent = 'Needs your attention';
    status.classList.add('attention');
  } else if (job?.status === 'SCHEDULED' || job?.status === 'AWARDED') {
    status.textContent = 'Booked';
    status.classList.add('good');
  } else if (job?.status === 'COMPLETED') {
    status.textContent = 'Bill check next';
    status.classList.add('warning');
  } else {
    status.textContent = 'In progress';
  }
}

function stageIndex(job, action) {
  if (action === 'EMERGENCY_ESCALATION') return 0;
  const map = {
    OPEN: 0,
    QUOTING: 1,
    QUOTES_READY: 1,
    AWARDED: 2,
    SCHEDULED: 2,
    IN_PROGRESS: 2,
    COMPLETED: 3,
    INVOICE_REVIEW: 3,
    CLOSED: 4,
  };
  return map[job?.status] ?? 0;
}

function renderProgress(job, action) {
  const index = stageIndex(job, action);
  document.querySelectorAll('#progress li').forEach((item, i) => {
    item.classList.toggle('done', index === 4 || i < index);
    item.classList.toggle('active', index !== 4 && i === index);
    const marker = item.querySelector(':scope > span');
    marker.textContent = (index === 4 || i < index) ? '✓' : String(i + 1);
  });
}

function renderSummary(job) {
  el('summary-service').textContent = serviceLabel(job);
  const selected = selectedQuote(job);
  el('summary-provider').textContent = selected?.provider_name || 'Not selected yet';
  el('summary-appointment').textContent = job?.appointment_window || 'Not scheduled yet';
  el('summary-approved').textContent = money(job?.approved_amount);
  const bill = job?.latest_invoice;
  el('summary-bill-row').hidden = !bill;
  el('summary-bill').textContent = bill ? money(bill.invoice_amount) : '—';
}

function actionButton(label, message, kind = 'primary', className = '') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = kind === 'primary' ? 'primary-button' : 'text-button';
  if (className) button.classList.add(className);
  button.textContent = label;
  button.addEventListener('click', () => send(message));
  return button;
}

function localButton(label, handler, kind = 'secondary') {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = kind === 'primary' ? 'primary-button' : kind === 'text' ? 'text-button' : 'secondary-button';
  button.textContent = label;
  button.addEventListener('click', handler);
  return button;
}

function setDecision(eyebrow, title, body) {
  el('decision-eyebrow').textContent = eyebrow;
  el('decision-title').textContent = title;
  el('decision-body').textContent = body;
  decisionDetail.innerHTML = '';
  decisionActions.innerHTML = '';
}

function renderRecommended(job) {
  const quote = recommendedQuote(job);
  if (!quote) return;
  const wrap = document.createElement('div');
  wrap.className = 'recommendation-card';

  const left = document.createElement('div');
  const name = document.createElement('div');
  name.className = 'provider-name';
  name.textContent = quote.provider_name;
  const meta = document.createElement('div');
  meta.className = 'provider-meta';
  meta.textContent = `★ ${quote.rating} · ${quote.arrival_window}`;
  const why = document.createElement('div');
  why.className = 'why';
  why.textContent = 'Recommended for the best balance of price, customer rating and availability.';
  left.append(name, meta, why);

  const right = document.createElement('div');
  right.className = 'price';
  right.textContent = money(quote.amount);
  const small = document.createElement('small');
  small.textContent = 'estimated price';
  right.appendChild(small);
  wrap.append(left, right);
  decisionDetail.appendChild(wrap);

  decisionActions.append(
    actionButton(`Approve ${quote.provider_name} — ${money(quote.amount)}`, `Choose ${quote.provider_name}`),
    localButton(`Compare all ${job.quotes.length} providers`, () => toggleComparison(true), 'text')
  );
}

function renderBooked(job, rescheduled = false) {
  const quote = selectedQuote(job);
  const wrap = document.createElement('div');
  wrap.className = 'success-panel';
  const strong = document.createElement('strong');
  strong.textContent = `${quote?.provider_name || 'Your provider'} is booked`;
  const p = document.createElement('p');
  p.textContent = `${job.appointment_window || 'Appointment scheduled'} · Agreed price ${money(job.approved_amount)}.`;
  wrap.append(strong, p);
  decisionDetail.appendChild(wrap);

  decisionActions.append(
    actionButton('The work is finished', 'The technician completed the repair'),
    actionButton('Reschedule', 'Reschedule', 'secondary')
  );
  if (rescheduled) showToast('Appointment updated.');
}

function renderCompleted(job) {
  const wrap = document.createElement('div');
  wrap.className = 'success-panel';
  const strong = document.createElement('strong');
  strong.textContent = 'Work marked complete';
  const p = document.createElement('p');
  p.textContent = `The agreed price is ${money(job.approved_amount)}. HomeOps will check the final bill before payment.`;
  const demo = document.createElement('p');
  demo.className = 'demo-note';
  demo.textContent = 'Demo scenario: a $135 final bill is ready to review.';
  wrap.append(strong, p, demo);
  decisionDetail.appendChild(wrap);
  decisionActions.append(actionButton('Review final bill — $135', 'The final invoice is $135'));
}

function renderInvoice(job) {
  const invoice = job.latest_invoice;
  if (!invoice) return;

  if (invoice.decision === 'HOLD_FOR_APPROVAL') {
    const wrap = document.createElement('div');
    wrap.className = 'cost-alert';
    const explanation = document.createElement('p');
    explanation.textContent = 'The additional charge has not been approved. HomeOps recommends asking the provider to explain it before payment.';
    explanation.style.margin = '0';
    const grid = document.createElement('div');
    grid.className = 'cost-grid';
    [
      ['Agreed price', money(invoice.approved_amount), ''],
      ['Final bill', money(invoice.invoice_amount), ''],
      ['Extra cost', `+${money(invoice.variance)}`, 'extra'],
    ].forEach(([label, value, cls]) => {
      const cell = document.createElement('div');
      if (cls) cell.className = cls;
      const s = document.createElement('span');
      s.textContent = label;
      const strong = document.createElement('strong');
      strong.textContent = value;
      cell.append(s, strong);
      grid.appendChild(cell);
    });
    wrap.append(explanation, grid);
    decisionDetail.appendChild(wrap);
    decisionActions.append(
      actionButton('Ask provider to explain', 'Request justification'),
      actionButton(`Approve extra ${money(invoice.variance)}`, 'Approve variance', 'secondary', 'danger-link')
    );
  } else {
    const wrap = document.createElement('div');
    wrap.className = 'success-panel';
    const strong = document.createElement('strong');
    strong.textContent = 'The final bill is within the agreed price';
    const p = document.createElement('p');
    p.textContent = `${money(invoice.invoice_amount)} can proceed through the normal payment process.`;
    wrap.append(strong, p);
    decisionDetail.appendChild(wrap);
    decisionActions.append(actionButton('Close repair', 'Close job'));
  }
}

function renderEmergency(reply) {
  const wrap = document.createElement('div');
  wrap.className = 'safety-panel';
  const strong = document.createElement('strong');
  strong.textContent = 'Normal provider sourcing has been stopped.';
  const p = document.createElement('p');
  p.textContent = reply;
  wrap.append(strong, p);
  decisionDetail.appendChild(wrap);
  decisionActions.append(localButton('Start over', resetDemo, 'primary'));
}

function renderDecision(data) {
  const job = data.job || state.job;
  const action = data.action || state.lastAction;
  const status = job?.status;

  if (action === 'EMERGENCY_ESCALATION') {
    setDecision('SAFETY FIRST', 'This may be an emergency', 'HomeOps will not continue normal automated sourcing when the description suggests immediate danger.');
    renderEmergency(data.reply);
    return;
  }

  if (status === 'QUOTES_READY') {
    const quote = recommendedQuote(job);
    setDecision('RECOMMENDATION', 'We found a good option', `HomeOps compared ${job.quotes?.length || 0} suitable providers. ${quote?.provider_name || 'The recommended provider'} gives you the best overall balance.`);
    renderRecommended(job);
    return;
  }

  if (status === 'AWARDED' || status === 'SCHEDULED' || status === 'IN_PROGRESS') {
    setDecision('BOOKED', 'Your repair is scheduled', 'The provider is confirmed and your agreed price is recorded. HomeOps will flag any later increase.');
    renderBooked(job, action === 'SERVICE_RESCHEDULED');
    return;
  }

  if (status === 'COMPLETED') {
    setDecision('SERVICE COMPLETE', 'Now check the final bill', 'The repair is complete. HomeOps will compare the final charge with the price you agreed before the visit.');
    renderCompleted(job);
    return;
  }

  if (status === 'INVOICE_REVIEW') {
    const invoice = job.latest_invoice;
    if (invoice?.decision === 'HOLD_FOR_APPROVAL') {
      const prefix = action === 'VARIANCE_CHALLENGED' ? 'Explanation requested' : 'Your attention is needed';
      setDecision('COST CHECK', invoice.variance > 0 ? `The final bill is ${money(invoice.variance)} higher than agreed` : prefix, action === 'VARIANCE_CHALLENGED'
        ? 'The provider has been asked to explain the additional charge. Payment remains on hold while you decide what to do next.'
        : `That is ${invoice.variance_percentage.toFixed(1)}% above the agreed price. Nothing extra has been approved.`);
      renderInvoice(job);
      if (action === 'VARIANCE_CHALLENGED') {
        decisionActions.innerHTML = '';
        decisionActions.append(
          actionButton('Show current status', 'Show status'),
          actionButton(`Approve extra ${money(invoice.variance)}`, 'Approve variance', 'secondary', 'danger-link')
        );
      }
    } else {
      setDecision('COST CHECK', 'The final bill is within the agreed price', 'HomeOps found no unapproved increase.');
      renderInvoice(job);
    }
    return;
  }

  if (status === 'CLOSED') {
    setDecision('COMPLETE', 'Your repair is closed', 'The final decision is recorded. You can start another request whenever you need help at home.');
    const wrap = document.createElement('div');
    wrap.className = 'success-panel';
    const strong = document.createElement('strong');
    strong.textContent = 'Repair complete';
    const p = document.createElement('p');
    p.textContent = 'HomeOps kept the agreed cost visible and recorded the final approval decision.';
    wrap.append(strong, p);
    decisionDetail.appendChild(wrap);
    decisionActions.append(localButton('Start another repair', resetDemo, 'primary'));
    return;
  }

  if (action === 'NEED_APPOINTMENT_WINDOW') {
    setDecision('RESCHEDULE', 'When should we move the visit?', 'Tell HomeOps the new appointment window.');
    decisionActions.append(actionButton('Friday, 2–4 PM', 'Reschedule to Friday 2-4 PM'));
    return;
  }

  setDecision('NEXT STEP', 'HomeOps is ready', 'Ask a question below or choose one of the suggested actions.');
}

function renderProviders(job) {
  const list = el('provider-list');
  list.innerHTML = '';
  if (!job?.quotes?.length) return;
  const sorted = [...job.quotes].sort((a, b) => Number(b.score || 0) - Number(a.score || 0));
  sorted.forEach(q => {
    const card = document.createElement('article');
    const recommended = q.recommendation === 'BEST_VALUE';
    card.className = `provider-card${recommended ? ' recommended' : ''}`;
    const badge = document.createElement('span');
    badge.className = 'provider-badge';
    badge.textContent = recommended ? 'Recommended' : q.recommendation === 'FASTEST' ? 'Available soonest' : 'Alternative';
    const h3 = document.createElement('h3');
    h3.textContent = q.provider_name;
    const price = document.createElement('div');
    price.className = 'provider-price';
    price.textContent = money(q.amount);
    const meta = document.createElement('div');
    meta.className = 'provider-meta';
    meta.textContent = `★ ${q.rating} · ${q.arrival_window}`;
    const reason = document.createElement('p');
    reason.className = 'provider-reason';
    reason.textContent = recommended
      ? 'Best overall balance of price, rating and availability.'
      : q.recommendation === 'FASTEST'
        ? 'Useful when speed matters most.'
        : 'Another suitable option for this repair.';
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'provider-action';
    button.textContent = state.job?.selected_provider_id === q.provider_id ? 'Selected' : `Choose ${q.provider_name}`;
    button.disabled = state.job?.status !== 'QUOTES_READY' || state.job?.selected_provider_id === q.provider_id;
    button.addEventListener('click', () => send(`Choose ${q.provider_name}`));
    card.append(badge, h3, price, meta, reason, button);
    list.appendChild(card);
  });
}

function toggleComparison(open = !state.comparisonOpen) {
  state.comparisonOpen = open;
  comparisonSection.hidden = !open;
  if (open) {
    renderProviders(state.job);
    comparisonSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

const suggestionLabels = new Map([
  ['Choose the recommended provider', 'Choose recommended'],
  ['Choose the cheapest', 'Lowest price'],
  ['Choose the fastest', 'Available soonest'],
  ['Show status', "What's happening?"],
  ['The technician completed the repair', 'Work is complete'],
  ['Reschedule to Friday 2-4 PM', 'Move to Friday 2–4 PM'],
  ['The final invoice is $135', 'Review $135 bill'],
  ['Request justification', 'Ask about extra cost'],
  ['Approve variance', 'Approve extra cost'],
  ['Why is it on hold?', 'Why is payment on hold?'],
  ['Close job', 'Close repair'],
  ['Reset', 'Start over'],
]);

function renderSuggestions(items = []) {
  suggestionsEl.innerHTML = '';
  [...new Set(items)].slice(0, 3).forEach(message => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'suggestion';
    button.textContent = suggestionLabels.get(message) || message;
    button.addEventListener('click', () => message.toLowerCase() === 'reset' ? resetDemo() : send(message));
    suggestionsEl.appendChild(button);
  });
}

function renderJudge(job) {
  el('job-id').textContent = job?.id || 'No active job';
  const invoice = job?.latest_invoice;
  el('judge-decision').textContent = invoice?.decision || 'Waiting';
  el('judge-exception').textContent = invoice?.exception || '—';
  el('judge-action').textContent = invoice?.recommended_action || '—';
  el('judge-ai').textContent = invoice?.ai_source === 'bedrock'
    ? `Amazon Bedrock · ${invoice.ai_model_id || 'model'}`
    : 'Deterministic fallback';

  const audit = el('audit-list');
  if (!job?.events?.length) {
    audit.innerHTML = '<p class="muted">Run a scenario to generate evidence.</p>';
    return;
  }
  audit.innerHTML = '';
  [...job.events].reverse().slice(0, 10).forEach(event => {
    const row = document.createElement('div');
    row.className = 'audit-event';
    const strong = document.createElement('strong');
    strong.textContent = titleCase(event.event_type);
    const time = document.createElement('time');
    time.textContent = new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    row.append(strong, time);
    audit.appendChild(row);
  });
}

function renderAll(data) {
  const job = data.job || state.job;
  if (job) state.job = job;
  state.lastAction = data.action || state.lastAction;

  landingView.hidden = true;
  caseView.hidden = false;
  setCaseHeader(job, data.action);
  renderProgress(job, data.action);
  renderSummary(job);
  renderDecision(data);
  renderSuggestions(data.suggestions || []);
  renderProviders(job);
  renderJudge(job);
  updateLatest(data.reply || 'HomeOps updated your repair.');
}

function calmError(message) {
  const detail = message && message !== 'Unknown error' ? ` ${message}` : '';
  setDecision('TRY AGAIN', "We couldn't complete that step", `Nothing new was approved or changed.${detail}`);
  decisionActions.append(localButton('Try again', () => messageInput.focus(), 'primary'));
  updateLatest("We couldn't complete that step. Nothing new was approved or changed.");
}

async function send(message, { fromLanding = false } = {}) {
  const clean = String(message || '').trim();
  if (!clean) return;

  addTranscript('user', clean);
  if (fromLanding || !state.jobId) {
    landingView.hidden = true;
    caseView.hidden = false;
    el('case-title').textContent = 'Working on your request';
    el('case-subtitle').textContent = clean;
  }
  setLoading(true, state.jobId ? 'Updating your repair…' : 'Understanding the problem and comparing suitable options.');
  startMessage.value = '';
  messageInput.value = '';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: clean, job_id: state.jobId }),
    });
    const data = await response.json();

    if (!response.ok || data.success === false) {
      throw new Error(data.error || 'Please try again.');
    }

    if (data.action === 'NEED_SERVICE_REQUEST' && !data.job_id) {
      landingView.hidden = false;
      caseView.hidden = true;
      showToast(data.reply || 'Tell HomeOps what needs fixing at home.');
      return;
    }

    if (data.job_id !== undefined) state.jobId = data.job_id;
    if (data.reply) addTranscript('assistant', data.reply);
    renderAll(data);
  } catch (error) {
    if (caseView.hidden) {
      showToast("We couldn't start that request. Please try again.");
    } else {
      calmError(error.message);
    }
  } finally {
    setLoading(false);
    if (!caseView.hidden) messageInput.focus();
  }
}

async function resetDemo() {
  try { await fetch('/api/demo/reset', { method: 'POST' }); } catch (_) { /* Local UI can still reset. */ }
  state.jobId = null;
  state.job = null;
  state.lastAction = null;
  state.transcript = [];
  state.comparisonOpen = false;
  landingView.hidden = false;
  caseView.hidden = true;
  comparisonSection.hidden = true;
  conversationLog.hidden = true;
  el('conversation-toggle').setAttribute('aria-expanded', 'false');
  el('conversation-toggle').textContent = 'See conversation';
  startMessage.value = '';
  messageInput.value = '';
  renderConversationLog();
  renderJudge(null);
  startMessage.focus();
}

function toggleJudge(open) {
  judgeView.hidden = !open;
  judgeToggle.setAttribute('aria-expanded', String(open));
  judgeToggle.textContent = open ? 'Hide demo details' : 'View demo details';
  if (open) judgeView.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

startForm.addEventListener('submit', event => {
  event.preventDefault();
  send(startMessage.value, { fromLanding: true });
});

document.querySelectorAll('.example-chip').forEach(button => {
  button.addEventListener('click', () => send(button.dataset.message, { fromLanding: true }));
});

chatForm.addEventListener('submit', event => {
  event.preventDefault();
  send(messageInput.value);
});

resetBtn.addEventListener('click', resetDemo);
el('comparison-close').addEventListener('click', () => toggleComparison(false));

el('conversation-toggle').addEventListener('click', () => {
  const open = conversationLog.hidden;
  conversationLog.hidden = !open;
  el('conversation-toggle').setAttribute('aria-expanded', String(open));
  el('conversation-toggle').textContent = open ? 'Hide conversation' : 'See conversation';
});

judgeToggle.addEventListener('click', () => toggleJudge(judgeView.hidden));
judgeClose.addEventListener('click', () => toggleJudge(false));

document.querySelectorAll('[data-scenario]').forEach(button => {
  button.addEventListener('click', async () => {
    await resetDemo();
    toggleJudge(true);
    send(button.dataset.scenario, { fromLanding: true });
  });
});

bedrockTestBtn.addEventListener('click', async () => {
  bedrockTestBtn.disabled = true;
  bedrockTestBtn.textContent = 'Testing…';
  try {
    const response = await fetch('/api/bedrock/test', { method: 'POST' });
    const data = await response.json();
    if (response.ok && data.success) {
      el('aws-status').textContent = `Live · ${data.model_id || 'Bedrock'}`;
      showToast('Amazon Bedrock connection verified.');
    } else {
      el('aws-status').textContent = 'Optional / not configured';
      showToast('Bedrock is optional. The core HomeOps demo remains available.');
    }
  } catch (_) {
    el('aws-status').textContent = 'Optional / unavailable';
    showToast('Bedrock is optional. The core HomeOps demo remains available.');
  } finally {
    bedrockTestBtn.disabled = false;
    bedrockTestBtn.textContent = 'Test Bedrock';
  }
});

(async function bootstrap() {
  try {
    const [healthResponse, toolsResponse] = await Promise.all([fetch('/health'), fetch('/api/tools')]);
    const health = await healthResponse.json();
    const tools = await toolsResponse.json();
    el('build-version').textContent = `v${health.version || '0.4.0'}`;
    el('mcp-status').textContent = health.mcp_available ? 'Streamable HTTP ready' : 'Dependency pending';
    el('tool-count').textContent = `${tools.tools?.length || 0} tools`;
    el('aws-status').textContent = health.bedrock?.configured ? 'Configured' : 'Optional / not configured';
  } catch (_) {
    el('mcp-status').textContent = 'Status unavailable';
    el('tool-count').textContent = '12 tools';
  }
})();
