// static/app.js
async function api(path, method="GET", body) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch("/api" + path, opts);
  return res.json();
}

async function addIncome() {
  const name = document.getElementById("income_name").value || "income";
  const amount = parseFloat(document.getElementById("income_amount").value) || 0;
  await api("/income", "POST", {name, amount});
  alert("Income added");
  refreshStatus();
}

async function addExpense() {
  const name = document.getElementById("expense_name").value || "expense";
  const amount = parseFloat(document.getElementById("expense_amount").value) || 0;
  await api("/expense", "POST", {name, amount});
  alert("Expense added");
  refreshStatus();
}

async function addDebt() {
  const name = document.getElementById("debt_name").value;
  const balance = parseFloat(document.getElementById("debt_balance").value) || 0;
  const apr = parseFloat(document.getElementById("debt_apr").value) || 0;
  const min_payment = parseFloat(document.getElementById("debt_min").value) || 0;
  if (!name || balance <= 0) { alert("Enter valid debt name and balance"); return; }
  await api("/debt", "POST", {name, balance, apr, min_payment});
  alert("Debt added");
  refreshStatus();
}

async function refreshStatus() {
  const s = await api("/status");
  document.getElementById("status").innerHTML = `
    <div class="card"><div class="card-body">
      <div><strong>Monthly Income:</strong> ₹ ${s.monthly_income}</div>
      <div><strong>Fixed Expenses:</strong> ₹ ${s.fixed_expenses}</div>
      <div><strong>Available for Debt:</strong> ₹ ${s.available_for_debt}</div>
      <div><strong>Total Debt:</strong> ₹ ${s.total_debt} (count: ${s.debts_count})</div>
    </div></div>
  `;
  const debts = await api("/debts");
  const list = debts.debts.map(d => 
    `<tr><td>${d.name}</td><td>₹ ${d.balance}</td><td>${d.apr}%</td><td>₹ ${d.min_payment}</td></tr>`
  ).join("");
  document.getElementById("debts_list").innerHTML = `
    <div class="card"><div class="card-body">
      <h6>Debts</h6>
      <table class="table table-sm"><thead><tr><th>Name</th><th>Balance</th><th>APR</th><th>Min</th></tr></thead><tbody>${list}</tbody></table>
    </div></div>
  `;
}

async function generatePlan() {
  const method = document.getElementById("method").value;
  const extra = parseFloat(document.getElementById("extra_payment").value) || 0;
  const res = await api("/plan", "POST", {method, extra_payment: extra, months_limit:120});
  if (res.error) { alert(res.error); return; }
  // display simple summary
  const months = res.months;
  let html = `<div class="card"><div class="card-body"><h5>Plan (months: ${res.total_months})</h5>`;
  html += `<div class="mb-2"><strong>Total paid:</strong> ₹ ${res.total_paid}</div>`;
  html += `<div style="max-height:350px; overflow:auto;"><table class="table table-sm"><thead><tr><th>M</th><th>Paid</th><th>Remaining</th></tr></thead><tbody>`;
  for (let m of months) {
    html += `<tr><td>${m.month}</td><td>₹ ${m.paid}</td><td>₹ ${m.remaining}</td></tr>`;
  }
  html += `</tbody></table></div></div></div>`;
  document.getElementById("plan_output").innerHTML = html;
}

window.onload = refreshStatus;
