const $ = (sel) => document.querySelector(sel);
const api = (path, opts = {}) =>
  fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });

// Tabs
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $(`#tab-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "goods") loadGoods();
  });
});

// Health
api("/health")
  .then((r) => r.json())
  .then((d) => {
    const el = $("#health");
    el.textContent = d.openai_configured
      ? "✓ API up, OpenAI key configured"
      : "⚠ API up, but OPENAI_API_KEY is missing — Q&A and extraction will fail";
  })
  .catch(() => ($("#health").textContent = "✗ API unreachable"));

// --- Q&A ---
const qaHistory = [];
$("#qa-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = $("#qa-input");
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  appendMsg("user", q);
  const placeholder = appendMsg("assistant", "…");
  try {
    const res = await api("/qa", {
      method: "POST",
      body: JSON.stringify({ question: q, conversation: qaHistory }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "error");
    placeholder.textContent = data.answer;
    qaHistory.push({ role: "user", content: q });
    qaHistory.push({ role: "assistant", content: data.answer });
  } catch (err) {
    placeholder.textContent = `Error: ${err.message}`;
  }
});

function appendMsg(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
  $("#qa-history").appendChild(div);
  div.scrollIntoView();
  return div;
}

// --- Extract ---
let lastExtraction = null;
$("#extract-run").addEventListener("click", async () => {
  const text = $("#extract-input").value;
  const hint = $("#extract-cn").value.trim() || null;
  $("#extract-output").textContent = "Extracting…";
  $("#extract-add").disabled = true;
  try {
    const res = await api("/extract", {
      method: "POST",
      body: JSON.stringify({ document_text: text, hint_cn_code: hint }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "error");
    lastExtraction = data;
    $("#extract-output").textContent = JSON.stringify(data, null, 2);
    $("#extract-add").disabled = !canAddToRegistry(data);
  } catch (err) {
    $("#extract-output").textContent = `Error: ${err.message}`;
  }
});

$("#extract-sample").addEventListener("click", () => {
  $("#extract-input").value = SAMPLE_STEEL;
  $("#extract-cn").value = "72081000";
});

$("#extract-add").addEventListener("click", async () => {
  if (!lastExtraction) return;
  const entry = toGoodEntry(lastExtraction);
  const res = await api("/goods", { method: "POST", body: JSON.stringify(entry) });
  const data = await res.json();
  if (!res.ok) {
    $("#extract-output").textContent = `Add failed: ${data.detail || JSON.stringify(data)}`;
    return;
  }
  $("#extract-output").textContent = `Added to registry as ${data.id}`;
  lastExtraction = null;
  $("#extract-add").disabled = true;
});

function canAddToRegistry(d) {
  return (
    d &&
    d.cn_code &&
    d.country_of_origin &&
    typeof d.quantity === "number" &&
    typeof d.direct_emissions_per_unit === "number" &&
    typeof d.indirect_emissions_per_unit === "number"
  );
}

function toGoodEntry(d) {
  return {
    cn_code: d.cn_code,
    description: d.description || null,
    sector: d.sector || null,
    country_of_origin: d.country_of_origin,
    quantity: d.quantity,
    quantity_unit: d.quantity_unit || "tonne",
    production_method: d.production_method || null,
    installation: d.installation && d.installation.name ? d.installation : null,
    direct_emissions_per_unit: d.direct_emissions_per_unit,
    indirect_emissions_per_unit: d.indirect_emissions_per_unit,
    emissions_source: d.emissions_source || "estimated",
    carbon_price_paid: d.carbon_price_paid || null,
  };
}

// --- Goods ---
$("#goods-refresh").addEventListener("click", loadGoods);
async function loadGoods() {
  const res = await api("/goods");
  const goods = await res.json();
  const tbody = $("#goods-table tbody");
  tbody.innerHTML = "";
  for (const g of goods) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${g.cn_code}</td>
      <td>${g.sector || ""}</td>
      <td>${g.country_of_origin}</td>
      <td>${g.quantity} ${g.quantity_unit}</td>
      <td>${g.direct_emissions_per_unit}</td>
      <td>${g.indirect_emissions_per_unit}</td>
      <td>${g.emissions_source}</td>
      <td><button data-id="${g.id}" class="ghost del">Delete</button></td>
    `;
    tbody.appendChild(tr);
  }
  tbody.querySelectorAll(".del").forEach((b) =>
    b.addEventListener("click", async () => {
      await api(`/goods/${b.dataset.id}`, { method: "DELETE" });
      loadGoods();
    })
  );
}

// --- Report ---
$("#report-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    reporting_year: parseInt($("#r-year").value, 10),
    reporting_quarter: parseInt($("#r-quarter").value, 10),
    declarant_name: $("#r-name").value,
    declarant_eori: $("#r-eori").value,
    declarant_country: $("#r-country").value.toUpperCase(),
  };
  const res = await api("/report", { method: "POST", body: JSON.stringify(body) });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    $("#report-output").textContent = `Error: ${err.detail}`;
    return;
  }
  const xml = await res.text();
  $("#report-output").textContent = xml;
  const blob = new Blob([xml], { type: "application/xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `CBAM_${body.declarant_eori}_${body.reporting_year}Q${body.reporting_quarter}.xml`;
  a.click();
  URL.revokeObjectURL(url);
});

const SAMPLE_STEEL = `SUPPLIER EMISSIONS REPORT
Issued: 2025-03-14
Installation: Bosporus Steel Works, Karabük, Türkiye
UNLOCODE: TRKBK   Lat 41.2050 Lon 32.6275
CN code: 7208.10.00 (hot-rolled flat steel in coils, with patterns in relief)
Production route: Integrated BF-BOF (blast furnace / basic oxygen furnace)
Reporting period: 2025-01-01 to 2025-03-31
Quantity delivered to EU importer: 1,250.00 tonnes
Direct embedded emissions: 2,438 tCO2e (1.95 tCO2e/t, monitored per Implementing Reg. 2023/1773)
Indirect embedded emissions: 225 tCO2e (0.18 tCO2e/t)
Methodology: actual emissions from continuous monitoring
Carbon price paid in country of origin: none (no ETS in force for this installation)
Destination country: Netherlands (NL)
`;
