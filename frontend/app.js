(() => {
  const tg = window.Telegram?.WebApp;
  tg?.ready(); tg?.expand();
  const $ = (id) => document.getElementById(id);
  let category = "all";
  let currentItems = [];

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const money = (value) => {
    if (!value) return "По договорённости";
    const numeric = Number(String(value).replace(/[^0-9.]/g, ""));
    return Number.isFinite(numeric) && numeric > 0 ? new Intl.NumberFormat("ru-RU").format(numeric) + " ₽" : esc(value);
  };

  function card(item) {
    return `<button class="request-card" data-id="${item.id}">
      <div class="card-top"><span class="cargo-icon">${item.category === "liquid" ? "◉" : "▣"}</span><strong>${esc(item.cargo)}</strong><span class="tag">${item.category === "liquid" ? "Наливные" : "Сухие"}</span></div>
      <div class="route">${esc(item.origin)} <span>→</span> ${esc(item.destination)}</div>
      <div class="meta"><span>▦ ${esc(item.pickup_date)}</span><span>⚖ ${esc(item.weight_tons)} т</span></div>
      <div class="card-bottom"><strong>${money(item.price_rub)}</strong><span>${esc(item.vehicle_type)}</span></div>
    </button>`;
  }

  async function load() {
    $("results").innerHTML = '<div class="empty">Ищем подходящие заявки…</div>';
    const params = new URLSearchParams({category, origin:$("origin").value.trim(), destination:$("destination").value.trim(), cargo:$("cargo").value.trim(), vehicle:$("vehicle").value.trim()});
    try {
      const response = await fetch("/api/requests?" + params.toString());
      if (!response.ok) throw new Error("API " + response.status);
      const data = await response.json();
      currentItems = data.items || [];
      $("count").textContent = "Найдено " + data.total;
      $("results").innerHTML = currentItems.length ? currentItems.map(card).join("") : '<div class="empty">По заданным параметрам заявок пока нет. Измените фильтры или попробуйте позже.</div>';
      document.querySelectorAll(".request-card").forEach((el) => el.addEventListener("click", () => showDetail(Number(el.dataset.id))));
    } catch (error) {
      $("count").textContent = "Нет соединения";
      $("results").innerHTML = '<div class="empty">Не удалось загрузить заявки. Проверьте соединение и повторите поиск.</div>';
    }
  }

  async function showDetail(id) {
    let item = currentItems.find((x) => x.id === id);
    if (!item) return;
    $("detail").classList.remove("hidden");
    $("detail").innerHTML = `<div class="detail-head"><div><p class="eyebrow">АКТУАЛЬНАЯ ЗАЯВКА</p><h3>Заявка №${item.id}</h3></div><button class="close" id="close-detail">✕</button></div>
      <div class="detail-route"><div><small>Загрузка</small><strong>⌖ ${esc(item.origin)}</strong></div><div class="arrow">↓</div><div><small>Выгрузка</small><strong>⌖ ${esc(item.destination)}</strong></div></div>
      <div class="detail-grid"><span>Груз</span><strong>${esc(item.cargo)}</strong><span>Объём / вес</span><strong>${esc(item.weight_tons)} т</strong><span>Транспорт</span><strong>${esc(item.vehicle_type)}</strong><span>Дата загрузки</span><strong>${esc(item.pickup_date)}</strong><span>Ставка</span><strong>${money(item.price_rub)}</strong></div>
      <p class="notice">Контактные данные заказчика доступны после подключения безопасного обмена откликами.</p>
      <button class="primary" id="offer">Предложить ставку</button>`;
    $("close-detail").addEventListener("click", () => $("detail").classList.add("hidden"));
    $("offer").addEventListener("click", () => {
      const msg = "Модуль отправки ставок будет включён после подключения авторизации Telegram и таблицы предложений. Заявка №" + id;
      if (tg?.showAlert) tg.showAlert(msg); else alert(msg);
    });
    $("detail").scrollIntoView({behavior:"smooth",block:"start"});
  }

  document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    button.classList.add("active"); category = button.dataset.category; load();
  }));
  document.querySelectorAll("[data-route]").forEach((button) => button.addEventListener("click", () => {
    const [from,to] = button.dataset.route.split("|"); $("origin").value = from; $("destination").value = to; load();
  }));
  $("search").addEventListener("click", load);
  load();
})();
