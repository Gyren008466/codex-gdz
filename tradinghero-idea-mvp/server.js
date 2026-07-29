const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const PORT = Number(process.env.PORT || 5177);
const ROOT = path.resolve(__dirname, "..");
const PUBLIC_DIR = path.join(__dirname, "public");
const GIFT_DIR = path.join(ROOT, "outputs", "tradinghero_gift_library");
const ACTIVE_GIFT_PATH = path.join(GIFT_DIR, "gift_library_latest_active.csv");
const REVIEW_PATH = path.join(GIFT_DIR, "gift_trend_candidates_review.csv");
const GENERATE_TREND_SCRIPT = path.join(ROOT, "scripts", "generate_tradinghero_trend_gift_candidates.py");
const MERGE_TREND_SCRIPT = path.join(ROOT, "scripts", "merge_tradinghero_trend_candidates_to_library.py");
const PYTHON_EXE =
  process.env.PYTHON_EXE ||
  "C:\\Users\\admin\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function sendJson(res, status, payload) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload, null, 2));
}

function sendError(res, status, message, detail = "") {
  sendJson(res, status, { error: message, detail });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 2_000_000) {
        reject(new Error("Request body is too large."));
      }
    });
    req.on("end", () => {
      if (!data) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

function readText(filePath) {
  if (!fs.existsSync(filePath)) return "";
  const raw = fs.readFileSync(filePath, "utf8");
  return raw.charCodeAt(0) === 0xfeff ? raw.slice(1) : raw;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];
    if (inQuotes) {
      if (ch === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        cell += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (ch !== "\r") {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  if (!rows.length) return { columns: [], records: [] };
  const columns = rows[0].map((col) => col.trim());
  const records = rows
    .slice(1)
    .filter((line) => line.some((value) => String(value || "").trim() !== ""))
    .map((line) => Object.fromEntries(columns.map((col, index) => [col, line[index] || ""])));
  return { columns, records };
}

function escapeCsv(value) {
  const text = String(value ?? "");
  if (/[",\r\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function writeCsv(filePath, columns, records) {
  const lines = [columns.map(escapeCsv).join(",")];
  for (const record of records) {
    lines.push(columns.map((col) => escapeCsv(record[col] || "")).join(","));
  }
  fs.writeFileSync(filePath, `\ufeff${lines.join("\r\n")}\r\n`, "utf8");
}

function readCsvFile(filePath) {
  return parseCsv(readText(filePath));
}

function toNumber(value, fallback = 0) {
  const number = Number(String(value ?? "").replace(/[^\d.-]/g, ""));
  return Number.isFinite(number) ? number : fallback;
}

function parseBool(value) {
  return String(value || "").trim().toLowerCase() === "true";
}

function isTrendGift(row) {
  return `${row.source_type || ""};${row.frontend_tags || ""}`.includes("趋势");
}

function cleanGift(row) {
  return {
    gift_id: row.gift_id || "",
    gift_name: row.gift_name || "",
    category: row.category || "",
    budget_cost: toNumber(row.budget_cost),
    market_price: toNumber(row.market_price, toNumber(row.budget_cost)),
    budget_band: row.budget_band || "",
    source_type: row.source_type || "",
    frontend_tags: row.frontend_tags || "",
    benefit_type: row.benefit_type || "gift",
    discount_amount: toNumber(row.discount_amount),
    affects_payment_price: parseBool(row.affects_payment_price),
    is_zero_budget: parseBool(row.is_zero_budget),
    is_inventory: parseBool(row.is_inventory),
    is_trend: isTrendGift(row),
    gift_role: row.gift_role || "",
    suitable_play_types: row.suitable_play_types || "",
    skill_usage_notes: row.skill_usage_notes || "",
  };
}

function getActiveGifts() {
  const { records } = readCsvFile(ACTIVE_GIFT_PATH);
  return records
    .filter((row) => String(row.is_selectable || "").toUpperCase() === "TRUE")
    .filter((row) => String(row.needs_manual_review || "").toUpperCase() !== "TRUE")
    .map(cleanGift);
}

function discountRate(price) {
  return `${((price / 3690) * 10).toFixed(1)}折`;
}

function monthOf(activityDate) {
  const date = new Date(activityDate);
  if (Number.isNaN(date.getTime())) return null;
  return date.getMonth() + 1;
}

function seasonAngle(activityDate) {
  const month = monthOf(activityDate);
  if (!month) return "未提供明确日期，按普通周播处理。";
  if ([1, 2].includes(month)) return "新年/春节氛围，适合金色寓意、开工实用礼和立减金。";
  if (month === 3) return "春季学习和工具升级，适合指标手册、订单流材料和课程承接。";
  if ([5, 6, 7, 8].includes(month)) return "夏季看盘和办公场景，适合桌面小电器、护眼、清凉和现金感福利。";
  if ([9, 10].includes(month)) return "学习重启和交易工作流升级，适合复盘、桌面、学习资料组合。";
  if ([11, 12].includes(month)) return "双11/双12和年终复盘，适合立减金、京东卡、复盘礼和跨年权益。";
  return "普通周播节点，适合用清晰价格理由叠加轻福利。";
}

function priceRisk(price) {
  if (price <= 2691) return { label: "强转化价格带", confidence: "高", note: "接近历史高转化秒杀带。" };
  if (price <= 2890) return { label: "较优价格带", confidence: "中高", note: "可结合阶梯价和限时名额。" };
  if (price <= 3090) return { label: "中等价格带", confidence: "中", note: "需要清晰活动理由和福利助推。" };
  if (price <= 3250) return { label: "偏高价格带", confidence: "中低", note: "需用立减金、稀缺名额或私域承接降低犹豫。" };
  return { label: "高风险价格带", confidence: "低", note: "不建议作为主推价，除非有强课程/服务承接。" };
}

function salesBands(basePrice, type, goal, hasDiscount) {
  let bands;
  if (basePrice <= 2691) bands = { stable: [8, 12, 18], sprint: [12, 20, 28], interactive: [8, 12, 16] };
  else if (basePrice <= 2890) bands = { stable: [6, 9, 13], sprint: [9, 14, 20], interactive: [6, 9, 13] };
  else if (basePrice <= 3090) bands = { stable: [5, 8, 12], sprint: [8, 12, 16], interactive: [5, 8, 11] };
  else if (basePrice <= 3250) bands = { stable: [4, 6, 9], sprint: [6, 9, 13], interactive: [4, 6, 8] };
  else bands = { stable: [2, 4, 6], sprint: [4, 6, 9], interactive: [3, 5, 7] };
  const selected = [...bands[type]];
  if (goal === "冲GMV" && type === "sprint") selected[1] += 1;
  if (goal === "冲销量") selected.forEach((_, i) => (selected[i] += i === 2 ? 2 : 1));
  if (hasDiscount) selected[1] += 1;
  return selected;
}

function estimate(basePrice, finalPrice, type, goal, hasDiscount) {
  const sales = salesBands(basePrice, type, goal, hasDiscount);
  const gmv = sales.map((count) => count * finalPrice);
  return {
    sales: { conservative: sales[0], target: sales[1], aggressive: sales[2] },
    gmv: { conservative: gmv[0], target: gmv[1], aggressive: gmv[2] },
  };
}

function usableGifts(gifts, input) {
  const high = toNumber(input.budgetHigh);
  return gifts
    .filter((gift) => gift.budget_cost <= high)
    .filter((gift) => input.allowTrendGift || !gift.is_trend)
    .filter((gift) => input.allowPriceDiscount || gift.benefit_type !== "price_discount");
}

function pickZeroGifts(gifts, names = []) {
  const zeros = gifts.filter((gift) => gift.budget_cost === 0);
  const preferred = [];
  for (const name of names) {
    const found = zeros.find((gift) => gift.gift_name.includes(name));
    if (found && !preferred.includes(found)) preferred.push(found);
  }
  for (const gift of zeros) {
    if (preferred.length >= 2) break;
    if (!preferred.includes(gift)) preferred.push(gift);
  }
  return preferred;
}

function pickGiftByType(gifts, benefitType, maxCost, order = "desc") {
  const rows = gifts
    .filter((gift) => gift.benefit_type === benefitType && gift.budget_cost > 0 && gift.budget_cost <= maxCost)
    .sort((a, b) => (order === "asc" ? a.budget_cost - b.budget_cost : b.budget_cost - a.budget_cost));
  return rows[0] || null;
}

function pickPhysicalGift(gifts, maxCost, activityDate) {
  const month = monthOf(activityDate);
  const summerNames = ["护眼台灯", "桌面静音小风扇", "保温杯", "无线鼠标"];
  const learningNames = ["交易复盘笔记本", "K线形态速查卡", "桌面计时器"];
  const names = [5, 6, 7, 8].includes(month) ? summerNames : learningNames;
  for (const name of names) {
    const found = gifts.find((gift) => gift.gift_name.includes(name) && gift.budget_cost > 0 && gift.budget_cost <= maxCost);
    if (found) return found;
  }
  return gifts
    .filter((gift) => gift.benefit_type === "gift" && gift.budget_cost > 0 && gift.budget_cost <= maxCost)
    .sort((a, b) => b.budget_cost - a.budget_cost)[0] || null;
}

function benefitSummary(gifts) {
  if (!gifts.length) return "无额外礼品";
  return gifts.map((gift) => `${gift.gift_name}（预算${gift.budget_cost}元）`).join(" + ");
}

function totalBudget(gifts) {
  return gifts.reduce((sum, gift) => sum + gift.budget_cost, 0);
}

function historicalReference(type, mode) {
  if (mode === "不参考历史") {
    return "创意假设：借鉴直播电商常见的限时立减、福利投票、里程碑解锁，但未作为历史效果证明。";
  }
  if (type === "sprint") {
    return "数据事实：2025-06-18「618秒杀」78160 GMV/30单；2026-06-18「2280元秒杀」63840 GMV/28单；2026-03-19 三轮秒杀 28692 GMV/12单。";
  }
  if (type === "interactive") {
    return "数据事实：2025-12-12「主播礼品二选一」40374 GMV/15单；互动玩法要绑定清晰价格理由。风险参照：2026-05-22 高UV但0 GMV。";
  }
  return "数据事实：强折扣/秒杀平均 GMV 明显高于非强折扣玩法；礼品适合做辅助成交理由，不宜单独承担主转化。";
}

function makePlan(kind, title, input, gifts, selectedGifts, mechanic, talkingPoints) {
  const basePrice = toNumber(input.basePrice);
  const discountGift = selectedGifts.find((gift) => gift.benefit_type === "price_discount");
  const discountAmount = discountGift ? discountGift.discount_amount || discountGift.budget_cost : 0;
  const finalPrice = basePrice - discountAmount;
  const forecast = estimate(basePrice, finalPrice, kind, input.goal, discountAmount > 0);
  const risk = priceRisk(basePrice);
  const budgetUsed = totalBudget(selectedGifts);
  const confidence = kind === "sprint" && input.mode !== "不参考历史" ? risk.confidence : risk.confidence === "高" ? "中高" : "中";
  return {
    key: kind,
    title,
    position: kind === "stable" ? "稳妥复用型" : kind === "sprint" ? "冲 GMV 型" : "互动创意型",
    basePrice,
    discountRate: discountRate(basePrice),
    discountAmount,
    finalPrice,
    budgetUsed,
    benefits: selectedGifts,
    benefitSummary: benefitSummary(selectedGifts),
    mechanic,
    historicalReference: historicalReference(kind, input.mode),
    forecast,
    confidence,
    logic: discountAmount
      ? `立减金直接降低支付价，GMV 预测按 ${finalPrice} 元计算；礼品预算消耗 ${budgetUsed} 元。`
      : `未使用立减金，GMV 预测按基础售价 ${basePrice} 元计算；礼品预算消耗 ${budgetUsed} 元。`,
    risk: `${risk.label}：${risk.note}${budgetUsed > toNumber(input.budgetHigh) ? " 当前福利超预算，需要删减。" : ""}`,
    talkingPoints,
  };
}

function generatePlans(input) {
  const gifts = usableGifts(getActiveGifts(), input);
  const basePrice = toNumber(input.basePrice);
  const budgetHigh = toNumber(input.budgetHigh);
  const zeroStudy = pickZeroGifts(gifts, ["指标手册", "订单流"]);
  const discount = pickGiftByType(gifts, "price_discount", budgetHigh, "desc");
  const voucher = pickGiftByType(gifts, "voucher", budgetHigh, "desc");
  const smallVoucher = pickGiftByType(gifts, "voucher", Math.min(100, budgetHigh), "desc");
  const physical = pickPhysicalGift(gifts, budgetHigh, input.activityDate);
  const lowCostPhysical = pickPhysicalGift(gifts, Math.max(0, budgetHigh - 100), input.activityDate);

  const stableBenefits = physical ? [physical, ...pickZeroGifts(gifts, ["指标手册"]).slice(0, 1)] : zeroStudy;
  const sprintBenefits = discount ? [discount, ...pickZeroGifts(gifts, ["黄金手机贴"]).slice(0, 1)] : voucher ? [voucher] : zeroStudy;
  const interactiveBenefits =
    smallVoucher && input.allowPriceDiscount && pickGiftByType(gifts, "price_discount", 100, "desc")
      ? [smallVoucher, pickGiftByType(gifts, "price_discount", 100, "desc")]
      : lowCostPhysical
        ? [lowCostPhysical, ...pickZeroGifts(gifts, ["K线", "指标手册"]).slice(0, 1)]
        : zeroStudy;

  return {
    setup: {
      activityDate: input.activityDate,
      seasonAngle: seasonAngle(input.activityDate),
      mode: input.mode,
      basePrice,
      discountRate: discountRate(basePrice),
      budgetRange: `${input.budgetLow}-${input.budgetHigh}元`,
      goal: input.goal,
      assumptions: [
        "只预测 TradingHero 旗舰年会员，不纳入月会员。",
        "第一版使用规则型估算，不等同于机器学习预测。",
        "PDF 作为创意来源，Excel 实际玩法是效果判断主依据。",
      ],
    },
    plans: [
      makePlan(
        "stable",
        "方案 A：稳妥复用型",
        input,
        gifts,
        stableBenefits.filter(Boolean),
        "基础售价不再继续复杂拆分，主打「今天下单锁定价格 + 实用看盘礼」。适合正常周播。",
        ["今天不是拼礼品数量，而是把软件价格和看盘实用礼一次讲清。", "前 N 名额外加送 0 元库存学习资料，增强临门一脚。"],
      ),
      makePlan(
        "sprint",
        "方案 B：冲 GMV 型",
        input,
        gifts,
        sprintBenefits.filter(Boolean),
        discount
          ? `${discount.gift_name} 限时窗口，最终支付价 ${basePrice - (discount.discount_amount || discount.budget_cost)} 元，叠加 0 元库存礼。`
          : "限时强福利窗口，优先使用现金感礼品/京东卡，配合名额稀缺。若要更强冲刺，建议开放立减金。",
        ["这一轮不是普通优惠，是限时成交窗口。", "倒计时结束后恢复基础售价和普通福利。"],
      ),
      makePlan(
        "interactive",
        "方案 C：互动创意型",
        input,
        gifts,
        interactiveBenefits.filter(Boolean),
        "直播间投票二选一：现金感福利 vs 实用桌面/学习礼。投票结束后开启 15 分钟下单窗口。",
        ["评论区投票决定今天主福利，但价格理由不变。", "福利二选一只做互动，不让用户看不懂最终到手价。"],
      ),
    ],
    recommendation: {
      first: input.goal === "冲GMV" ? "优先用方案 B，但要严格控制福利预算并讲清最终支付价。" : "优先用方案 A，执行简单、风险低。",
      backup: "方案 C 适合需要提升直播间互动时使用。",
      avoid: basePrice > 3090 ? "避免只靠普通礼品支撑 3090 元以上价格，容易出现高 UV 低成交。" : "避免福利层数超过 3 层，防止用户理解成本过高。",
    },
  };
}

function runPython(scriptPath, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON_EXE, [scriptPath, ...args], { cwd: ROOT, windowsHide: true });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => (stdout += chunk.toString("utf8")));
    child.stderr.on("data", (chunk) => (stderr += chunk.toString("utf8")));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code !== 0) reject(new Error(stderr || stdout || `Python exited with code ${code}`));
      else resolve({ stdout, stderr });
    });
  });
}

async function handleApi(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  try {
    if (req.method === "GET" && url.pathname === "/api/gifts") {
      return sendJson(res, 200, { gifts: getActiveGifts(), source: ACTIVE_GIFT_PATH });
    }

    if (req.method === "POST" && url.pathname === "/api/generate-plans") {
      const input = await readBody(req);
      return sendJson(res, 200, generatePlans(input));
    }

    if (req.method === "GET" && url.pathname === "/api/trends/review") {
      const { records } = readCsvFile(REVIEW_PATH);
      return sendJson(res, 200, { candidates: records, source: REVIEW_PATH });
    }

    if (req.method === "POST" && url.pathname === "/api/trends/generate") {
      const input = await readBody(req);
      const budgetRange = `${input.budgetLow || 0}-${input.budgetHigh || 200}`;
      await runPython(GENERATE_TREND_SCRIPT, [
        "--activity-date",
        input.activityDate || "",
        "--budget-range",
        budgetRange,
        "--goal",
        input.goal || "冲GMV",
        "--keywords",
        input.keywords || "夏季办公室礼品,交易员桌面用品,TradingHero礼品",
        "--source-platforms",
        input.sourcePlatforms || "manual_keyword_seed",
        "--max-candidates",
        String(input.maxCandidates || 20),
        "--append",
      ]);
      const { records } = readCsvFile(REVIEW_PATH);
      return sendJson(res, 200, { candidates: records, source: REVIEW_PATH });
    }

    if (req.method === "POST" && url.pathname === "/api/trends/review") {
      const input = await readBody(req);
      const updates = new Map((input.candidates || []).map((row) => [row.candidate_id, row]));
      const { columns, records } = readCsvFile(REVIEW_PATH);
      const editable = ["manual_status", "manual_actual_cost", "manual_budget_cost", "manual_market_price", "manual_stock_status", "manual_notes"];
      const next = records.map((row) => {
        const update = updates.get(row.candidate_id);
        if (!update) return row;
        const copy = { ...row };
        for (const col of editable) {
          if (Object.prototype.hasOwnProperty.call(update, col)) copy[col] = update[col];
        }
        return copy;
      });
      writeCsv(REVIEW_PATH, columns, next);
      return sendJson(res, 200, { saved: true, candidates: next, source: REVIEW_PATH });
    }

    if (req.method === "POST" && url.pathname === "/api/trends/merge") {
      await runPython(MERGE_TREND_SCRIPT, ["--update-latest"]);
      return sendJson(res, 200, { merged: true, gifts: getActiveGifts(), source: ACTIVE_GIFT_PATH });
    }

    return sendError(res, 404, "API not found");
  } catch (error) {
    return sendError(res, 500, "Request failed", error.message);
  }
}

function serveStatic(req, res) {
  const url = new URL(req.url, `http://localhost:${PORT}`);
  const cleanPath = decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname);
  const filePath = path.normalize(path.join(PUBLIC_DIR, cleanPath));
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end("Forbidden");
  }
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    res.writeHead(404);
    return res.end("Not found");
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(filePath)] || "application/octet-stream" });
  fs.createReadStream(filePath).pipe(res);
}

if (process.argv.includes("--self-test")) {
  const result = generatePlans({
    activityDate: "2026-07-15",
    basePrice: 3250,
    budgetLow: 150,
    budgetHigh: 200,
    goal: "冲GMV",
    mode: "混合模式",
    allowPriceDiscount: true,
    allowTrendGift: true,
  });
  console.log(
    JSON.stringify(
      {
        gifts: getActiveGifts().length,
        plans: result.plans.length,
        sprintFinalPrice: result.plans[1].finalPrice,
        sprintBudgetUsed: result.plans[1].budgetUsed,
      },
      null,
      2,
    ),
  );
} else {
  const server = http.createServer((req, res) => {
    if (req.url.startsWith("/api/")) return handleApi(req, res);
    return serveStatic(req, res);
  });

  server.listen(PORT, () => {
    console.log(`TradingHero idea MVP running at http://localhost:${PORT}`);
  });
}
