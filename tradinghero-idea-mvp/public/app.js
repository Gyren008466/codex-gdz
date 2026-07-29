const state = {
  gifts: [],
  candidates: [],
  lastInput: null,
};

const $ = (selector) => document.querySelector(selector);

function money(value) {
  return `${Number(value || 0).toLocaleString("zh-CN")} 元`;
}

function requestJson(url, options = {}) {
  return fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  }).then(async (response) => {
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "请求失败");
    return data;
  });
}

function formInput() {
  const form = new FormData($("#planForm"));
  return {
    activityDate: form.get("activityDate"),
    basePrice: Number(form.get("basePrice")),
    budgetLow: Number(form.get("budgetLow")),
    budgetHigh: Number(form.get("budgetHigh")),
    goal: form.get("goal"),
    mode: form.get("mode"),
    allowPriceDiscount: form.get("allowPriceDiscount") === "on",
    allowTrendGift: form.get("allowTrendGift") === "on",
  };
}

function giftTypeLabel(type) {
  if (type === "price_discount") return "立减金";
  if (type === "voucher") return "京东卡/券";
  return "普通礼品";
}

function giftTypeClass(type) {
  if (type === "price_discount") return "red";
  if (type === "voucher") return "gold";
  return "green";
}

function renderGifts() {
  const type = $("#giftTypeFilter").value;
  const trend = $("#giftTrendFilter").value;
  const rows = state.gifts
    .filter((gift) => !type || gift.benefit_type === type)
    .filter((gift) => {
      if (!trend) return true;
      return trend === "trend" ? gift.is_trend : !gift.is_trend;
    });

  $("#giftRows").innerHTML = rows
    .map(
      (gift) => `
        <tr>
          <td>
            <strong>${gift.gift_name}</strong>
            <div class="muted">${gift.category || "未分类"}</div>
          </td>
          <td><span class="tag ${giftTypeClass(gift.benefit_type)}">${giftTypeLabel(gift.benefit_type)}</span></td>
          <td class="nowrap">${money(gift.budget_cost)}</td>
          <td>${gift.is_trend ? "趋势/人工审核" : gift.is_inventory ? "库存/内部" : gift.source_type}</td>
          <td>${gift.affects_payment_price ? `最终支付价 = 售价 - ${gift.discount_amount}` : gift.skill_usage_notes || gift.gift_role || "不改变支付价"}</td>
        </tr>
      `,
    )
    .join("");

  $("#giftStatus").textContent = `已加载 ${state.gifts.length} 个可用礼品`;
}

function planCard(plan) {
  const benefitTags = plan.benefits
    .map((gift) => `<span class="tag ${giftTypeClass(gift.benefit_type)}">${gift.gift_name} / ${gift.budget_cost}元</span>`)
    .join("");
  return `
    <article class="plan-card">
      <div>
        <h3>${plan.title}</h3>
        <div class="tag-row">
          <span class="tag green">${plan.position}</span>
          <span class="tag">${plan.discountRate}</span>
          <span class="tag ${plan.discountAmount ? "red" : ""}">${plan.discountAmount ? `${plan.discountAmount}元立减` : "不改支付价"}</span>
        </div>
      </div>
      <p class="plan-line"><strong>价格：</strong>${plan.basePrice} 元 → 最终支付 ${plan.finalPrice} 元</p>
      <p class="plan-line"><strong>福利：</strong>${plan.benefitSummary}</p>
      <div class="tag-row">${benefitTags}</div>
      <p class="plan-line"><strong>机制：</strong>${plan.mechanic}</p>
      <div class="stats">
        <div class="mini-stat"><span class="muted">目标销量</span><b>${plan.forecast.sales.target} 单</b></div>
        <div class="mini-stat"><span class="muted">目标 GMV</span><b>${money(plan.forecast.gmv.target)}</b></div>
      </div>
      <p class="plan-line"><strong>预测区间：</strong>保守 ${plan.forecast.sales.conservative} 单 / ${money(plan.forecast.gmv.conservative)}；激进 ${plan.forecast.sales.aggressive} 单 / ${money(plan.forecast.gmv.aggressive)}</p>
      <p class="plan-line"><strong>数据事实/参考：</strong>${plan.historicalReference}</p>
      <p class="plan-line"><strong>计算口径：</strong>${plan.logic}</p>
      <p class="plan-line"><strong>风险：</strong>${plan.risk}</p>
      <p class="plan-line"><strong>主播话术：</strong>${plan.talkingPoints.join(" ")}</p>
    </article>
  `;
}

function renderPlans(data) {
  $("#setupBox").innerHTML = `
    <strong>${data.setup.activityDate}</strong>｜${data.setup.goal}｜${data.setup.mode}｜基础售价 ${data.setup.basePrice} 元（${data.setup.discountRate}）｜福利预算 ${data.setup.budgetRange}<br />
    <span>${data.setup.seasonAngle}</span><br />
    <span class="muted">假设：${data.setup.assumptions.join("；")}</span><br />
    <strong>推荐：</strong>${data.recommendation.first} 备选：${data.recommendation.backup} 不建议：${data.recommendation.avoid}
  `;
  $("#plans").innerHTML = data.plans.map(planCard).join("");
}

async function loadGifts() {
  const data = await requestJson("/api/gifts");
  state.gifts = data.gifts;
  renderGifts();
}

async function generatePlans(event) {
  event?.preventDefault();
  const input = formInput();
  state.lastInput = input;
  $("#plans").innerHTML = "";
  $("#setupBox").textContent = "正在生成方案...";
  const data = await requestJson("/api/generate-plans", {
    method: "POST",
    body: JSON.stringify(input),
  });
  renderPlans(data);
}

function renderReviewRows() {
  $("#reviewRows").innerHTML = state.candidates
    .slice()
    .sort((a, b) => Number(b.gift_score || 0) - Number(a.gift_score || 0))
    .map(
      (row) => `
        <tr data-candidate-id="${row.candidate_id}">
          <td>
            <strong>${row.gift_name}</strong>
            <div class="muted">${row.category || ""} ${row.benefit_type || ""}</div>
          </td>
          <td class="nowrap">${row.reference_price || ""}</td>
          <td class="nowrap">${row.gift_score || ""}</td>
          <td>
            <select data-field="manual_status">
              ${["待确认", "确认", "纳入", "拒绝", "归档"].map((status) => `<option ${row.manual_status === status ? "selected" : ""}>${status}</option>`).join("")}
            </select>
          </td>
          <td><input data-field="manual_budget_cost" value="${row.manual_budget_cost || ""}" placeholder="如 100" /></td>
          <td>
            <select data-field="manual_stock_status">
              ${["待确认", "可采购", "充足", "少量", "缺货"].map((status) => `<option ${row.manual_stock_status === status ? "selected" : ""}>${status}</option>`).join("")}
            </select>
          </td>
          <td><input data-field="manual_notes" value="${row.manual_notes || ""}" placeholder="人工备注" /></td>
        </tr>
      `,
    )
    .join("");
}

async function loadTrendReview() {
  const data = await requestJson("/api/trends/review");
  state.candidates = data.candidates;
  renderReviewRows();
}

function collectReviewUpdates() {
  return [...document.querySelectorAll("#reviewRows tr")].map((tr) => {
    const row = { candidate_id: tr.dataset.candidateId };
    tr.querySelectorAll("[data-field]").forEach((input) => {
      row[input.dataset.field] = input.value;
    });
    return row;
  });
}

async function saveReview() {
  const data = await requestJson("/api/trends/review", {
    method: "POST",
    body: JSON.stringify({ candidates: collectReviewUpdates() }),
  });
  state.candidates = data.candidates;
  renderReviewRows();
  alert("审核表已保存。");
}

async function generateTrends() {
  const input = {
    ...formInput(),
    keywords: $("#trendKeywords").value,
    maxCandidates: Number($("#maxCandidates").value || 20),
  };
  $("#reviewRows").innerHTML = `<tr><td colspan="7">正在生成趋势候选...</td></tr>`;
  const data = await requestJson("/api/trends/generate", {
    method: "POST",
    body: JSON.stringify(input),
  });
  state.candidates = data.candidates;
  renderReviewRows();
}

async function mergeReview() {
  if (!confirm("确认把已审核通过的趋势候选合并进正式礼品库？")) return;
  const data = await requestJson("/api/trends/merge", { method: "POST", body: "{}" });
  state.gifts = data.gifts;
  renderGifts();
  alert("已合并，并刷新正式礼品库。");
}

async function copySkillPrompt() {
  const input = state.lastInput || formInput();
  const prompt = `使用 tradinghero-live-idea-generator，活动日期${input.activityDate}，售价${input.basePrice}，福利预算${input.budgetLow}-${input.budgetHigh}元，目标${input.goal}，模式${input.mode}，${input.allowPriceDiscount ? "允许" : "不允许"}使用立减金，${input.allowTrendGift ? "允许" : "不允许"}使用趋势礼品，生成3个TradingHero直播活动方案。`;
  await navigator.clipboard.writeText(prompt);
  alert("已复制 skill 调用提示。");
}

function bindEvents() {
  $("#planForm").addEventListener("submit", generatePlans);
  $("#giftTypeFilter").addEventListener("change", renderGifts);
  $("#giftTrendFilter").addEventListener("change", renderGifts);
  $("#loadTrendReview").addEventListener("click", loadTrendReview);
  $("#generateTrends").addEventListener("click", generateTrends);
  $("#saveReview").addEventListener("click", saveReview);
  $("#mergeReview").addEventListener("click", mergeReview);
  $("#copyPrompt").addEventListener("click", copySkillPrompt);
}

async function init() {
  bindEvents();
  try {
    await loadGifts();
    await generatePlans();
    await loadTrendReview();
  } catch (error) {
    $("#giftStatus").textContent = "读取失败";
    $("#setupBox").textContent = error.message;
  }
}

init();
