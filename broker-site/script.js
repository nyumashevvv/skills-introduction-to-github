// Банки-партнёры (вымышленные, условия — для примера)
const BANKS = [
  { id: "aurora",   name: "Аврора Банк",       short: "А", color: "#7c5cff", fee: 0,   maxTerm: 24, maxSum: 500000,  decision: 1, chance: 0.9,  tags: ["0% переплаты", "Онлайн-подпись"] },
  { id: "north",    name: "Северный Капитал",  short: "С", color: "#22d3ee", fee: 0,   maxTerm: 12, maxSum: 300000,  decision: 2, chance: 0.85, tags: ["0% переплаты", "Без первого взноса"] },
  { id: "meridian", name: "Меридиан",          short: "М", color: "#f472b6", fee: 4.9, maxTerm: 36, maxSum: 1000000, decision: 3, chance: 0.8,  tags: ["До 1 млн ₽", "До 36 мес"] },
  { id: "prime",    name: "Прайм Финанс",      short: "П", color: "#f59e0b", fee: 2.5, maxTerm: 24, maxSum: 700000,  decision: 1, chance: 0.75, tags: ["Кэшбэк 3%", "Решение за 1 мин"] },
  { id: "vector",   name: "Вектор Банк",       short: "В", color: "#34d399", fee: 0,   maxTerm: 18, maxSum: 400000,  decision: 2, chance: 0.7,  tags: ["0% переплаты", "Досрочно без штрафов"] },
  { id: "granite",  name: "Гранит Банк",       short: "Г", color: "#60a5fa", fee: 6.5, maxTerm: 36, maxSum: 800000,  decision: 3, chance: 0.95, tags: ["Высокое одобрение", "До 36 мес"] },
];

const $ = (s, el = document) => el.querySelector(s);
const fmt = (n) => Math.round(n).toLocaleString("ru-RU") + " ₽";
const logo = (b) => `<span class="bank-logo" style="--c:${b.color};background:${b.color}">${b.short}</span>`;

function calcPay(bank, amount, term) {
  const total = amount * (1 + (bank.fee / 100) * (term / 12));
  return { monthly: total / term, over: total - amount };
}

/* ---------- nav ---------- */
const nav = $("#nav");
addEventListener("scroll", () => nav.classList.toggle("scrolled", scrollY > 20), { passive: true });
$("#burger").addEventListener("click", (e) => {
  e.currentTarget.classList.toggle("open");
  $("#navLinks").classList.toggle("open");
});
$("#navLinks").addEventListener("click", () => {
  $("#burger").classList.remove("open");
  $("#navLinks").classList.remove("open");
});

/* ---------- typing headline ---------- */
const phrases = ["рассрочка 0%", "6 банков сразу", "решение за 3 мин", "без переплат"];
(function type(i = 0, j = 0, del = false) {
  const el = $("#typed"), word = phrases[i];
  el.textContent = word.slice(0, j);
  if (!del && j === word.length) return setTimeout(() => type(i, j, true), 1800);
  if (del && j === 0) return setTimeout(() => type((i + 1) % phrases.length, 0, false), 300);
  setTimeout(() => type(i, j + (del ? -1 : 1), del), del ? 40 : 85);
})();

/* ---------- orbit ---------- */
const track = $("#orbitTrack");
BANKS.forEach((b, i) => {
  const angle = (i / BANKS.length) * Math.PI * 2;
  const r = 43; // % от радиуса
  const node = document.createElement("div");
  node.className = "orbit-bank";
  node.style.background = b.color;
  node.style.left = `calc(50% + ${Math.cos(angle) * r}%)`;
  node.style.top = `calc(50% + ${Math.sin(angle) * r}%)`;
  node.innerHTML = `<span>${b.short}</span>`;
  const beam = document.createElement("div");
  beam.className = "orbit-beam";
  beam.style.width = r + "%";
  beam.style.transform = `rotate(${angle}rad)`;
  beam.style.animationDelay = `${-i * 0.4}s`;
  track.append(beam, node);
});

/* ---------- marquee ---------- */
const mq = BANKS.map((b) => `<span><i style="background:${b.color}"></i>${b.name}</span>`).join("");
$("#marquee").innerHTML = mq + mq + mq + mq;

/* ---------- bank cards ---------- */
const grid = $("#bankGrid");
grid.innerHTML = BANKS.map((b) => `
  <article class="bank glass reveal" data-id="${b.id}" style="--c:${b.color}">
    <div class="bank-top">
      ${logo(b)}
      <div><div class="bank-name">${b.name}</div><span class="status">API подключено</span></div>
    </div>
    <div class="bank-specs">
      <div><small>Переплата</small><b>${b.fee ? b.fee + "% / год" : "0%"}</b></div>
      <div><small>Срок до</small><b>${b.maxTerm} мес</b></div>
      <div><small>Сумма до</small><b>${fmt(b.maxSum)}</b></div>
      <div><small>Решение</small><b>${b.decision} мин</b></div>
    </div>
    <div class="bank-tags">${b.tags.map((t) => `<span class="tag">${t}</span>`).join("")}</div>
  </article>`).join("");

grid.querySelectorAll(".bank").forEach((card) => {
  card.addEventListener("mousemove", (e) => {
    const r = card.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    card.style.setProperty("--mx", x + "px");
    card.style.setProperty("--my", y + "px");
    const rx = (y / r.height - 0.5) * -8, ry = (x / r.width - 0.5) * 8;
    card.style.transform = `perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-4px)`;
  });
  card.addEventListener("mouseleave", () => (card.style.transform = ""));
});

const FILTERS = {
  all: () => true,
  zero: (b) => b.fee === 0,
  long: (b) => b.maxTerm >= 24,
  fast: (b) => b.decision <= 1,
};
$("#filters").addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === btn));
  const fn = FILTERS[btn.dataset.filter];
  BANKS.forEach((b) => grid.querySelector(`[data-id="${b.id}"]`).classList.toggle("dim", !fn(b)));
});

/* ---------- calculator ---------- */
const amount = $("#amount"), term = $("#term"), results = $("#calcResults");
const mql = matchMedia("(max-width: 760px)");
const ROW_H = 80;
results.innerHTML = BANKS.map((b) => `
  <div class="row" data-id="${b.id}" style="--c:${b.color}">
    ${logo(b)}
    <div class="row-info"><b>${b.name}</b><small></small><div class="row-bar"><i></i></div></div>
    <div class="row-pay"><b></b><small></small></div>
  </div>`).join("");

function setFill(input) {
  const p = ((input.value - input.min) / (input.max - input.min)) * 100;
  input.style.setProperty("--p", p + "%");
}

function updateCalc() {
  const a = +amount.value, t = +term.value;
  setFill(amount); setFill(term);
  $("#amountOut").textContent = fmt(a);
  $("#termOut").textContent = t + " мес";

  const list = BANKS.map((b) => {
    const ok = a <= b.maxSum && t <= b.maxTerm;
    return { b, ok, ...calcPay(b, a, t) };
  }).sort((x, y) => (y.ok - x.ok) || (x.monthly - y.monthly));

  const best = list.find((x) => x.ok);
  const stacked = !mql.matches; // на десктопе строки плавно меняются местами
  results.style.height = stacked ? list.length * ROW_H + "px" : "";

  list.forEach((x, i) => {
    const row = results.querySelector(`[data-id="${x.b.id}"]`);
    row.style.position = stacked ? "absolute" : "";
    row.style.transform = stacked ? `translateY(${i * ROW_H}px)` : "";
    if (!stacked) results.append(row);
    row.classList.toggle("na", !x.ok);
    row.classList.toggle("top", x === best);
    const info = row.querySelector(".row-info small");
    const name = row.querySelector(".row-info b");
    name.innerHTML = x.b.name + (x === best ? '<span class="badge">Лучшее</span>' : "");
    if (x.ok) {
      info.textContent = x.over > 0 ? `Переплата ${fmt(x.over)}` : "Без переплаты";
      row.querySelector(".row-pay b").textContent = fmt(x.monthly);
      row.querySelector(".row-pay small").textContent = "в месяц";
      row.querySelector(".row-bar i").style.width = (best.monthly / x.monthly) * 100 + "%";
    } else {
      info.textContent = a > x.b.maxSum ? `Сумма до ${fmt(x.b.maxSum)}` : `Срок до ${x.b.maxTerm} мес`;
      row.querySelector(".row-pay b").textContent = "—";
      row.querySelector(".row-pay small").textContent = "недоступно";
      row.querySelector(".row-bar i").style.width = "0%";
    }
  });

  if (best) {
    animateNumber($("#bestPay"), best.monthly);
    $("#bestBank").textContent = `${best.b.name} · ${best.over > 0 ? "переплата " + fmt(best.over) : "без переплаты"}`;
  } else {
    $("#bestPay").textContent = "—";
    $("#bestBank").textContent = "Нет подходящих банков";
  }
}

function animateNumber(el, to) {
  const from = parseInt(el.textContent.replace(/\D/g, "")) || 0;
  const start = performance.now(), dur = 400;
  cancelAnimationFrame(el._raf);
  const step = (now) => {
    const k = Math.min(1, (now - start) / dur);
    el.textContent = fmt(from + (to - from) * (1 - Math.pow(1 - k, 3)));
    if (k < 1) el._raf = requestAnimationFrame(step);
  };
  el._raf = requestAnimationFrame(step);
}

amount.addEventListener("input", updateCalc);
term.addEventListener("input", updateCalc);
mql.addEventListener("change", updateCalc);
updateCalc();

/* ---------- counters + reveal ---------- */
function countUp(el) {
  const to = +el.dataset.count, suffix = el.dataset.suffix || "";
  const start = performance.now(), dur = 1600;
  const step = (now) => {
    const k = Math.min(1, (now - start) / dur);
    el.textContent = Math.round(to * (1 - Math.pow(1 - k, 4))).toLocaleString("ru-RU") + suffix;
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

const io = new IntersectionObserver((entries) => {
  entries.forEach((en) => {
    if (!en.isIntersecting) return;
    const el = en.target;
    const siblings = [...el.parentElement.children].filter((c) => c.classList.contains("reveal"));
    el.style.transitionDelay = Math.max(0, siblings.indexOf(el)) * 80 + "ms";
    el.classList.add("in");
    el.querySelectorAll("[data-count]").forEach(countUp);
    io.unobserve(el);
  });
}, { threshold: 0.15 });
document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
// после появления убираем задержку, чтобы ховеры были мгновенными
document.addEventListener("transitionend", (e) => {
  if (e.target.classList?.contains("reveal") && e.propertyName === "opacity") e.target.style.transitionDelay = "";
});

/* ---------- application form ---------- */
const form = $("#applyForm"), phone = $("#fPhone"), fAmount = $("#fAmount");

phone.addEventListener("input", () => {
  let d = phone.value.replace(/\D/g, "");
  if (d.startsWith("8")) d = "7" + d.slice(1);
  if (!d.startsWith("7")) d = "7" + d;
  d = d.slice(0, 11);
  const p = [d.slice(1, 4), d.slice(4, 7), d.slice(7, 9), d.slice(9, 11)];
  phone.value = "+7" + (p[0] ? ` (${p[0]}` : "") + (p[0].length === 3 ? ")" : "") +
    (p[1] ? ` ${p[1]}` : "") + (p[2] ? `-${p[2]}` : "") + (p[3] ? `-${p[3]}` : "");
});
fAmount.addEventListener("input", () => {
  const d = fAmount.value.replace(/\D/g, "").slice(0, 7);
  fAmount.value = d ? (+d).toLocaleString("ru-RU") : "";
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const err = $("#formError");
  form.querySelectorAll(".field").forEach((f) => f.classList.remove("err"));
  const sum = +fAmount.value.replace(/\D/g, "");
  const bad = [];
  if ($("#fName").value.trim().length < 3) bad.push($("#fName"));
  if (phone.value.replace(/\D/g, "").length !== 11) bad.push(phone);
  if (sum < 5000 || sum > 1000000) bad.push(fAmount);
  if (bad.length) {
    bad.forEach((i) => { const f = i.closest(".field"); void f.offsetWidth; f.classList.add("err"); });
    err.textContent = sum && (sum < 5000 || sum > 1000000) ? "Сумма — от 5 000 до 1 000 000 ₽" : "Проверьте выделенные поля";
    return;
  }
  if (!$("#fAgree").checked) { err.textContent = "Нужно согласие на обработку данных"; return; }
  err.textContent = "";
  runScoring(sum, +$("#fTerm").value);
});

function runScoring(sum, t) {
  form.classList.add("hidden");
  const prog = $("#progress"), list = $("#progressList");
  prog.classList.remove("hidden");
  list.innerHTML = BANKS.map((b, i) => `
    <li data-id="${b.id}" style="animation-delay:${i * 90}ms">${logo(b)}<span>${b.name}</span>
      <span class="st"><span class="spinner"></span>проверка</span></li>`).join("");

  const results = BANKS.map((b) => {
    const fits = sum <= b.maxSum && t <= b.maxTerm;
    return { b, approved: fits && Math.random() < b.chance, reason: fits ? "отказ" : "не подходит" };
  });
  // гарантируем хотя бы одно одобрение среди подходящих банков
  if (!results.some((r) => r.approved)) {
    const fit = results.find((r) => sum <= r.b.maxSum && t <= r.b.maxTerm);
    if (fit) fit.approved = true;
  }

  let done = 0;
  results.forEach((r, i) => {
    setTimeout(() => {
      const st = list.querySelector(`[data-id="${r.b.id}"] .st`);
      st.className = "st " + (r.approved ? "yes" : "no");
      st.textContent = r.approved ? "✓ одобрено" : "✕ " + r.reason;
      if (++done === results.length) setTimeout(() => showOffers(results, sum, t), 700);
    }, 900 + r.b.decision * 500 + i * 250);
  });
}

function showOffers(results, sum, t) {
  $("#progress").classList.add("hidden");
  const box = $("#offers"), list = $("#offersList");
  box.classList.remove("hidden");
  const approved = results.filter((r) => r.approved)
    .map((r) => ({ ...r, ...calcPay(r.b, sum, t) }))
    .sort((a, b) => a.monthly - b.monthly);

  if (!approved.length) {
    list.innerHTML = `<p class="muted">Ни один банк не поддерживает такую сумму и срок. Попробуйте уменьшить сумму или срок.</p>`;
    return;
  }
  list.innerHTML = approved.map((x, i) => `
    <div class="row offer${i === 0 ? " top" : ""}" data-id="${x.b.id}" style="--c:${x.b.color};animation-delay:${i * 120}ms">
      ${logo(x.b)}
      <div class="row-info"><b>${x.b.name}${i === 0 ? '<span class="badge">Лучшее</span>' : ""}</b>
        <small>${t} мес · ${x.over > 0 ? "переплата " + fmt(x.over) : "без переплаты"}</small></div>
      <div class="row-pay"><b>${fmt(x.monthly)}</b><small>в месяц</small></div>
    </div>`).join("");

  list.querySelectorAll(".offer").forEach((o) => o.addEventListener("click", () => {
    list.querySelectorAll(".offer").forEach((x) => x.classList.toggle("chosen", x === o));
    const b = BANKS.find((x) => x.id === o.dataset.id);
    toast(`Выбрано: ${b.name}. Ссылка на подписание отправлена в SMS`);
  }));
}

$("#restart").addEventListener("click", () => {
  $("#offers").classList.add("hidden");
  form.classList.remove("hidden");
});

function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 3500);
}
