const API_BASE = '/api';

async function saveLLMKey() {
  const keyInput = document.getElementById('llmKeyInput');
  const key = keyInput.value.trim();
  if (!key) {
    alert("Please paste a valid LLM API key (e.g., Groq 'gsk_...' or OpenAI 'sk-...').");
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/settings/llm-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key })
    });
    const data = await res.json();
    if (res.ok) {
      alert("✅ LLM API Key activated! DealFlow agents are now calling real LLM inference models live.");
      document.getElementById('llmStatusBadge').innerHTML = `<span class="pulse-dot" style="background:#38bdf8;"></span> LLM Active`;
    } else {
      alert("Error setting key: " + (data.detail || "Invalid key."));
    }
  } catch (err) {
    console.error(err);
    alert("Unable to save key.");
  }
}

function switchTab(tabName) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));

  if (tabName === 'dashboard') {
    document.querySelector("button[onclick=\"switchTab('dashboard')\"]").classList.add('active');
    document.getElementById('tab-dashboard').classList.remove('hidden');
  } else if (tabName === 'history') {
    document.querySelector("button[onclick=\"switchTab('history')\"]").classList.add('active');
    document.getElementById('tab-history').classList.remove('hidden');
    loadHistory();
  } else if (tabName === 'pitch') {
    document.querySelector("button[onclick=\"switchTab('pitch')\"]").classList.add('active');
    document.getElementById('tab-pitch').classList.remove('hidden');
  }
}

function loadPreset(promptText) {
  document.getElementById('promptInput').value = promptText;
  const riskChk = document.getElementById('simRiskVeto');
  const payChk = document.getElementById('simPaymentFail');
  if (riskChk) riskChk.checked = false;
  if (payChk) payChk.checked = false;
}

function clearConsole() {
  document.getElementById('logConsole').innerHTML = `
    <div class="log-entry SYSTEM">
      <div class="log-header"><span class="log-agent">SYSTEM</span><span>Ready</span></div>
      <div class="log-msg">Log cleared. Ready for new deal negotiation...</div>
    </div>
  `;
  resetAgentNodes();
}

function resetAgentNodes() {
  document.querySelectorAll('.agent-node').forEach(node => {
    node.className = 'agent-node';
  });
}

function highlightAgentNode(agentName, status = 'active') {
  const node = document.getElementById(`node-${agentName}`);
  if (node) {
    if (status === 'active') {
      node.className = 'agent-node active';
    } else if (status === 'done') {
      node.className = 'agent-node done';
    } else if (status === 'vetoed') {
      node.className = 'agent-node vetoed';
    }
  }
}

function appendLog(agentName, action, reasoning, timestamp = '') {
  const consoleEl = document.getElementById('logConsole');
  const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
  
  const entry = document.createElement('div');
  entry.className = `log-entry ${agentName}`;
  entry.innerHTML = `
    <div class="log-header">
      <span class="log-agent">[${agentName}] ${action.toUpperCase()}</span>
      <span>${timeStr}</span>
    </div>
    <div class="log-msg">${reasoning}</div>
  `;
  consoleEl.appendChild(entry);
  consoleEl.scrollTop = consoleEl.scrollHeight;

  highlightAgentNode(agentName, 'active');
}

async function runNegotiation() {
  const promptInput = document.getElementById('promptInput');
  const userPrompt = promptInput.value.trim();
  const negotiateBtn = document.getElementById('negotiateBtn');
  const outputArea = document.getElementById('outputArea');
  const simRiskVetoEl = document.getElementById('simRiskVeto');
  const simPaymentFailEl = document.getElementById('simPaymentFail');
  const simRiskVeto = simRiskVetoEl ? simRiskVetoEl.checked : false;
  const simPaymentFail = simPaymentFailEl ? simPaymentFailEl.checked : false;

  if (!userPrompt) {
    alert("Please enter a product request or budget preference.");
    return;
  }

  resetAgentNodes();
  negotiateBtn.disabled = true;
  negotiateBtn.innerHTML = '<span>Negotiating...</span> ⏳';

  outputArea.innerHTML = `
    <div style="font-size: 0.9rem; color: var(--accent-cyan); text-align: center; padding: 1.5rem; background: rgba(6, 182, 212, 0.05); border: 1px solid rgba(6, 182, 212, 0.2); border-radius: 10px;">
      🔄 <strong>Negotiation Engine Active:</strong> Routing between Buyer, Merchant, Critic, Risk, and Payment agents...
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/negotiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_prompt: userPrompt,
        simulate_risk_veto: simRiskVeto,
        simulate_payment_fail: simPaymentFail
      })
    });

    if (!res.ok) {
      throw new Error(`Server returned ${res.status}`);
    }

    const data = await res.json();
    
    // Animate Log Trace Step-by-Step
    if (data.audit_trail && data.audit_trail.length > 0) {
      for (let i = 0; i < data.audit_trail.length; i++) {
        const step = data.audit_trail[i];
        await new Promise(r => setTimeout(r, 350));
        appendLog(step.agent_name, step.action, step.reasoning, step.timestamp);
        
        if (step.status === 'approved' || step.status === 'success') {
          highlightAgentNode(step.agent_name, 'done');
        } else if (step.status === 'vetoed' || step.status === 'rejected') {
          highlightAgentNode(step.agent_name, 'vetoed');
        }
      }
    }

    // Render Final Output Result Card
    renderOutputCard(data);

  } catch (err) {
    console.error(err);
    outputArea.innerHTML = `
      <div class="alert-fallback">
        ⚠️ <strong>Error:</strong> Unable to communicate with DealFlow negotiation backend. Make sure the backend server is running.
      </div>
    `;
  } finally {
    negotiateBtn.disabled = false;
    negotiateBtn.innerHTML = '<span>Run DealFlow</span> ➔';
  }
}

function renderOutputCard(data) {
  const outputArea = document.getElementById('outputArea');
  const status = data.status;
  const offer = data.current_offer;
  const teller = data.teller_result;

  if (status === 'SUCCESS' && offer && teller) {
    const base = offer.base_product || {};
    const upsell = offer.upsell_bundle;
    const paymentUrl = teller.payment_link || '#';
    const orderId = teller.order_id || 'RZP_ORDER_TEST';

    let upsellHtml = '';
    if (upsell) {
      upsellHtml = `
        <div class="upsell-box">
          <span class="upsell-tag">🚀 AI Revenue Growth Upsell</span>
          <div class="product-row" style="margin-top: 0.3rem;">
            <span class="product-name">${upsell.name}</span>
            <span class="product-price">+ ₹${upsell.price.toFixed(2)}</span>
          </div>
          <div style="font-size: 0.78rem; color: var(--text-muted); font-style: italic;">"${upsell.pitch}"</div>
        </div>
      `;
    }

    outputArea.innerHTML = `
      <div class="offer-card">
        <div class="offer-header">
          <div>
            <div style="font-size: 0.75rem; color: #34d399; font-weight: 700; text-transform: uppercase;">✅ Negotiation Approved</div>
            <div style="font-size: 1.1rem; font-weight: 700;">${base.name || 'Negotiated Item'}</div>
          </div>
          <span class="badge badge-rzp">Razorpay Test Mode</span>
        </div>

        <div class="product-row">
          <span style="color: var(--text-muted); font-size: 0.88rem;">Base Product Price</span>
          <span style="font-weight: 600;">₹${base.price ? base.price.toFixed(2) : '0.00'}</span>
        </div>

        ${upsellHtml}

        <div class="total-row">
          <span>Total Negotiated Price</span>
          <span class="total-amount">₹${offer.total_price ? offer.total_price.toFixed(2) : '0.00'}</span>
        </div>

        <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.5rem; font-family: var(--font-mono);">
          Razorpay Order ID: <strong>${orderId}</strong>
        </div>

        <a href="${paymentUrl}" target="_blank" class="pay-btn">
          💳 Pay ₹${offer.total_price ? offer.total_price.toFixed(2) : '0.00'} via Razorpay Link ➔
        </a>
      </div>
    `;
  } else {
    // Graceful Fallback View
    const fallbackMsg = data.fallback_message || "Negotiation safely paused due to constraint limits or risk policy.";
    outputArea.innerHTML = `
      <div class="alert-fallback">
        <div style="font-weight: 700; margin-bottom: 0.4rem; color: #f43f5e; font-size: 0.95rem;">
          ⚠️ Graceful Fallback Handled (${status})
        </div>
        <div>${fallbackMsg}</div>
        <div style="font-size: 0.78rem; margin-top: 0.5rem; color: var(--text-muted);">
          Negotiation state logged to SQLite audit trail. Zero unhandled exceptions.
        </div>
      </div>
    `;
  }
}

async function loadHistory() {
  const tbody = document.getElementById('historyBody');
  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">Loading audit records...</td></tr>`;

  try {
    const res = await fetch(`${API_BASE}/negotiations?limit=15`);
    const list = await res.json();

    if (!list || list.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No negotiation history found in SQLite DB yet. Run a deal first!</td></tr>`;
      return;
    }

    tbody.innerHTML = list.map(item => {
      let statusBadge = `<span class="badge badge-rzp" style="background: rgba(16, 185, 129, 0.15); color: #34d399;">SUCCESS</span>`;
      if (item.status.includes('RISK') || item.status.includes('VETO')) {
        statusBadge = `<span class="badge badge-rzp" style="background: rgba(244, 63, 94, 0.15); color: #f43f5e;">RISK VETO</span>`;
      } else if (item.status.includes('FAIL')) {
        statusBadge = `<span class="badge badge-rzp" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24;">FALLBACK</span>`;
      }

      return `
        <tr>
          <td style="font-family: var(--font-mono); font-size: 0.8rem; color: #38bdf8;">${item.id}</td>
          <td>${item.user_prompt}</td>
          <td>${statusBadge}</td>
          <td style="font-weight: 700;">₹${item.final_price ? item.final_price.toFixed(2) : '0.00'}</td>
          <td style="font-family: var(--font-mono); font-size: 0.78rem;">${item.razorpay_order_id || 'N/A'}</td>
          <td style="text-align: center;">${item.loop_count}</td>
          <td style="font-size: 0.78rem; color: var(--text-muted);">${new Date(item.created_at).toLocaleString()}</td>
        </tr>
      `;
    }).join('');

  } catch (err) {
    console.error(err);
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #f43f5e; padding: 2rem;">Error loading history from server.</td></tr>`;
  }
}
