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
  const dateRu = (value) => value ? new Date(value + "T00:00:00").toLocaleDateString("ru-RU") : "";
  const isCreateMode = new URLSearchParams(location.search).get("mode") === "create";

  function card(item) {
    return `<button class="request-card" data-id="${item.id}">
      <div class="card-top"><span class="cargo-icon">${item.category === "liquid" ? "◉" : "▣"}</span><strong>${esc(item.cargo)}</strong><span class="tag">${item.category === "liquid" ? "Наливные" : "Сухие"}</span></div>
      <div class="route">${esc(item.origin)} <span>→</span> ${esc(item.destination)}</div>
      <div class="meta"><span>▦ ${esc(item.pickup_date)}</span><span>⚖ ${esc(item.weight_tons)} т</span></div>
      <div class="card-bottom"><strong>${money(item.price_rub)}</strong><span>${esc(item.vehicle_type)}</span></div>
    </button>`;
  }
  async function load() {
    if (!$("results")) return;
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
    const item = currentItems.find((x) => x.id === id);
    if (!item) return;
    $("detail").classList.remove("hidden");
    $("detail").innerHTML = `<div class="detail-head"><div><p class="eyebrow">АКТУАЛЬНАЯ ЗАЯВКА</p><h3>Заявка №${item.id}</h3></div><button class="close" id="close-detail">✕</button></div>
      <div class="detail-route"><div><small>Загрузка</small><strong>⌖ ${esc(item.origin)}</strong></div><div class="arrow">↓</div><div><small>Выгрузка</small><strong>⌖ ${esc(item.destination)}</strong></div></div>
      <div class="detail-grid"><span>Груз</span><strong>${esc(item.cargo)}</strong><span>Вес</span><strong>${esc(item.weight_tons)} т</strong><span>Транспорт</span><strong>${esc(item.vehicle_type)}</strong><span>Дата загрузки</span><strong>${esc(item.pickup_date)}</strong><span>Ставка</span><strong>${money(item.price_rub)}</strong></div>
      <p class="notice">Контактные данные заказчика доступны после подключения безопасного обмена откликами.</p><button class="primary" id="offer">Предложить ставку</button>`;
    $("close-detail").addEventListener("click", () => $("detail").classList.add("hidden"));
    $("offer").addEventListener("click", () => { const msg = "Отправка ставок доступна через Telegram-бот. Заявка №" + id; tg?.showAlert ? tg.showAlert(msg) : alert(msg); });
    $("detail").scrollIntoView({behavior:"smooth",block:"start"});
  }

  function selectedCargo() {
    const value = $("f-cargo").value;
    return value === "manual" ? $("f-cargo-manual").value.trim() : value;
  }
  function selectedVehicle() {
    const value = $("f-vehicle").value;
    return value === "manual" ? $("f-vehicle-manual").value.trim() : value;
  }
  function collect() {
    const dangerous = $("f-adr-toggle").checked;
    return {
      origin:$("f-origin").value.trim(), destination:$("f-destination").value.trim(),
      cargo:selectedCargo(), category:$("f-category").value,
      weight_tons:Number($("f-weight").value), volume_m3:$("f-volume").value ? Number($("f-volume").value) : null,
      adr_class:dangerous ? $("f-adr").value : null, vehicle_type:selectedVehicle(),
      pickup_date:$("f-pickup").value, unloading_date:$("f-unloading").value || null,
      price_rub:$("f-price").value.trim() || null, vat_mode:$("f-vat").value,
      comment:$("f-comment").value.trim() || null
    };
  }
  function previewHtml(d) {
    const range = dateRu(d.pickup_date) + (d.unloading_date ? " — " + dateRu(d.unloading_date) : "");
    const specs = [d.weight_tons + " т", d.volume_m3 ? d.volume_m3 + " м³" : "", d.adr_class ? "ADR " + d.adr_class : ""].filter(Boolean).join(" · ");
    return `<div class="preview-head"><div><p class="eyebrow">CARGOLINK · ПРЕДПРОСМОТР</p><h3>Новая заявка</h3></div><span class="tag">Черновик</span></div>
      <div class="preview-route"><strong>${esc(d.origin)}</strong><span>→</span><strong>${esc(d.destination)}</strong></div>
      <div class="preview-price"><strong>${d.price_rub ? money(d.price_rub) : "По договорённости"}</strong><span>${esc(d.vat_mode)}</span></div>
      <div class="preview-grid"><span>Груз</span><strong>${esc(d.cargo)}</strong><span>Категория</span><strong>${d.category === "liquid" ? "Налив" : "Обычный"}</strong><span>Вес / объём / ADR</span><strong>${esc(specs)}</strong><span>Транспорт</span><strong>${esc(d.vehicle_type)}</strong><span>Даты</span><strong>${esc(range)}</strong>${d.comment ? '<span>Комментарий</span><strong>' + esc(d.comment) + '</strong>' : ''}</div>
      <div class="preview-actions"><button type="button" class="secondary" id="edit-request">← Изменить заявку</button><button type="button" class="primary" id="publish-request">Опубликовать заявку</button></div><p id="publish-error" class="form-error hidden"></p>`;
  }
  function showFormError(message) {
    $("form-error").textContent = message;
    $("form-error").classList.remove("hidden");
  }

  function bindAddressAutocomplete(inputId, listId) {
    const input=$(inputId), list=$(listId); if(!input||!list)return;
    let timer=null,controller=null,lastQuery="";
    const popularCities=["Москва, Россия","Санкт-Петербург, Россия","Новосибирск, Россия","Екатеринбург, Россия","Казань, Россия","Нижний Новгород, Россия","Краснодар, Россия","Челябинск, Россия","Самара, Россия","Уфа, Россия","Ростов-на-Дону, Россия","Красноярск, Россия","Пермь, Россия","Воронеж, Россия","Волгоград, Россия","Омск, Россия","Тюмень, Россия","Иркутск, Россия","Хабаровск, Россия","Владивосток, Россия","Саратов, Россия","Тольятти, Россия","Ижевск, Россия","Барнаул, Россия","Махачкала, Россия","Ставрополь, Россия","Оренбург, Россия","Ярославль, Россия","Рязань, Россия","Тула, Россия","Калининград, Россия","Кемерово, Россия"];
    const close=()=>list.classList.add("hidden");
    const render=values=>{
      const options=values.filter((v,i,a)=>v&&a.indexOf(v)===i).slice(0,10);
      if(!options.length)list.innerHTML='<div class="suggestion-item">Ничего не найдено — укажите адрес вручную</div>';
      else {list.innerHTML=options.map((v,i)=>'<button type="button" class="suggestion-item" data-index="'+i+'">'+esc(v)+'</button>').join("");list.querySelectorAll("button").forEach(b=>b.addEventListener("click",()=>{input.value=options[Number(b.dataset.index)];close();input.dispatchEvent(new Event("change",{bubbles:true}));}));}
      list.classList.remove("hidden");
    };
    const popular=q=>{const query=q.trim().toLocaleLowerCase("ru");render(popularCities.filter(city=>!query||city.toLocaleLowerCase("ru").includes(query)));};
    input.addEventListener("focus",()=>{if(input.value.trim().length<3)popular(input.value);});
    input.addEventListener("input",()=>{
      const query=input.value.trim();clearTimeout(timer);
      if(query.length<3){controller?.abort();lastQuery="";popular(query);return;}
      timer=setTimeout(async()=>{
        if(query===lastQuery)return;lastQuery=query;controller?.abort();controller=new AbortController();
        const q=query.toLocaleLowerCase("ru"),priority=popularCities.filter(city=>city.toLocaleLowerCase("ru").startsWith(q)||city.toLocaleLowerCase("ru").includes(q));
        list.innerHTML='<div class="suggestion-item">Ищем города и адреса…</div>';list.classList.remove("hidden");
        try{
          const url="https://photon.komoot.io/api/?q="+encodeURIComponent(query)+"&lang=ru&limit=10";
          const response=await fetch(url,{signal:controller.signal,headers:{Accept:"application/json"}});
          if(!response.ok)throw new Error("Geocoder unavailable");
          const data=await response.json();
          const found=(data.features||[]).map(feature=>{const p=feature.properties||{},locality=p.city||p.town||p.village||p.county||"",name=p.name||locality,street=[p.street,p.housenumber].filter(Boolean).join(", ");return [...new Set([name,street,locality,p.state,p.country].filter(Boolean))].join(", ");});
          render([...priority,...found]);
        }catch(error){if(error.name!=="AbortError")render(priority);}
      },280);
    });
    input.addEventListener("keydown",event=>{if(event.key==="Escape")close();if(event.key==="Enter"&&!list.classList.contains("hidden")){const first=list.querySelector("button");if(first){event.preventDefault();first.click();}}});
    document.addEventListener("click",event=>{if(!list.contains(event.target)&&event.target!==input)close();});
  }

  function applyCargoSuggestions() {
    const cargo = $("f-cargo").value;
    const category = $("f-category"), vehicle = $("f-vehicle");
    const defaults = {
      "Дизельное топливо": {category:"liquid", vehicle:"Бензовоз", adr:true},
      "Бензин": {category:"liquid", vehicle:"Бензовоз", adr:true},
      "Бензин АИ-92": {category:"liquid", vehicle:"Бензовоз", adr:true},
      "Бензин АИ-95": {category:"liquid", vehicle:"Бензовоз", adr:true},
      "Бензин АИ-98 / АИ-100": {category:"liquid", vehicle:"Бензовоз", adr:true},
      "Авиакеросин": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Керосин": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Мазут": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "Битум": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "Нефть сырая": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Газовый конденсат": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Смазочные материалы": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "СУГ (пропан-бутан)": {category:"liquid", vehicle:"Газовоз", adr:true},
      "СПГ (сжиженный природный газ)": {category:"liquid", vehicle:"Газовоз", adr:true},
      "Аммиак": {category:"liquid", vehicle:"Газовоз", adr:true},
      "Аммиачная вода": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "Метанол": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Этанол": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Растворители": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Кислоты и щёлочи": {category:"liquid", vehicle:"Автоцистерна", adr:true},
      "Химическое сырьё": {category:"liquid", vehicle:"Автоцистерна"},
      "Жидкие удобрения": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "Молоко": {category:"liquid", vehicle:"Молоковоз", adr:false},
      "Растительное масло": {category:"liquid", vehicle:"Пищевой наливной транспорт", adr:false},
      "Патока / меласса": {category:"liquid", vehicle:"Пищевой наливной транспорт", adr:false},
      "Пищевые жидкости": {category:"liquid", vehicle:"Пищевой наливной транспорт", adr:false},
      "Питьевая вода": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "Техническая вода": {category:"liquid", vehicle:"Автоцистерна", adr:false},
      "Зерно": {category:"dry", vehicle:"Зерновоз", adr:false},
      "Сахар": {category:"dry", vehicle:"Тентованный автомобиль", adr:false},
      "Удобрения": {category:"dry", vehicle:"Тентованный автомобиль", adr:false},
      "Цемент": {category:"dry", vehicle:"Цементовоз", adr:false},
      "Известь": {category:"dry", vehicle:"Самосвал", adr:false},
      "Песок": {category:"dry", vehicle:"Самосвал", adr:false},
      "Щебень": {category:"dry", vehicle:"Самосвал", adr:false},
      "Пиломатериалы": {category:"dry", vehicle:"Бортовой автомобиль", adr:false},
      "Металлопродукция": {category:"dry", vehicle:"Бортовой автомобиль", adr:false},
      "Паллетный груз / ТНП": {category:"dry", vehicle:"Фура / еврофура", adr:false},
      "Контейнерный груз": {category:"dry", vehicle:"Контейнеровоз", adr:false},
      "ADR — другой опасный груз": {adr:true},
      "Хим. продукты опасные": {adr:true},
      "Хим. продукты неопасные": {adr:false},
      "Нефтепродукты": {category:"liquid", vehicle:"Автоцистерна"},
      "20\' танк-контейнер": {category:"liquid", vehicle:"Контейнеровоз"},
      "40\' танк-контейнер": {category:"liquid", vehicle:"Контейнеровоз"}
    };
    const suggestion = defaults[cargo];
    if (!suggestion) return;
    if (suggestion.category) category.value = suggestion.category;
    if (suggestion.vehicle) vehicle.value = suggestion.vehicle;
    if (typeof suggestion.adr === "boolean") {
      $("f-adr-toggle").checked = suggestion.adr;
      $("adr-wrap").classList.toggle("hidden", !suggestion.adr);
    }
  }
  if (isCreateMode) {
    $("create-flow").classList.remove("hidden");
    ["market-hero","market-search","market-results-head","results","detail"].forEach(id => $(id)?.classList.add("hidden"));
    bindAddressAutocomplete("f-origin", "f-origin-suggestions");
    bindAddressAutocomplete("f-destination", "f-destination-suggestions");
    const cargoSelect = $("f-cargo");
    const cargoSearch = $("f-cargo-search");
    const cargoResults = $("f-cargo-results");
    const cargoSelected = $("f-cargo-selected");
    const cargoOptions = Array.from(cargoSelect.options).filter(o => o.value !== "" && o.value !== "manual");
    function renderCargoResults(query = "") {
      const q = query.trim().toLocaleLowerCase("ru");
      const matches = cargoOptions.filter(o => o.textContent.toLocaleLowerCase("ru").includes(q)).slice(0, 35);
      cargoResults.innerHTML = "";
      if (!matches.length) {
        cargoResults.innerHTML = '<div class="cargo-empty">Ничего не найдено. Можно ввести название вручную.</div>';
      } else {
        matches.forEach(option => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "cargo-result";
          button.setAttribute("role", "option");
          button.textContent = option.textContent;
          button.addEventListener("click", () => {
            cargoSelect.value = option.value;
            cargoSearch.value = option.textContent;
            cargoResults.classList.add("hidden");
            cargoSelected.classList.remove("hidden");
            cargoSelected.textContent = "Выбрано: " + option.textContent;
            $("manual-cargo-wrap").classList.add("hidden");
            applyCargoSuggestions();
          });
          cargoResults.appendChild(button);
        });
      }
      const manual = document.createElement("button");
      manual.type = "button";
      manual.className = "cargo-result";
      manual.textContent = "✍️ Ввести вручную";
      manual.addEventListener("click", () => {
        cargoSelect.value = "manual";
        cargoSearch.value = "";
        cargoResults.classList.add("hidden");
        cargoSelected.classList.add("hidden");
        $("manual-cargo-wrap").classList.remove("hidden");
        $("f-cargo-manual").focus();
      });
      cargoResults.appendChild(manual);
      cargoResults.classList.remove("hidden");
    }
    cargoSearch.addEventListener("focus", () => renderCargoResults(cargoSearch.value));
    cargoSearch.addEventListener("input", () => {
      cargoSelect.value = "";
      cargoSelected.classList.add("hidden");
      renderCargoResults(cargoSearch.value);
    });
    cargoSearch.addEventListener("keydown", event => {
      if (event.key === "Escape") cargoResults.classList.add("hidden");
      if (event.key === "Enter") {
        const first = cargoResults.querySelector(".cargo-result");
        if (first && !cargoResults.classList.contains("hidden")) { event.preventDefault(); first.click(); }
      }
    });
    document.addEventListener("click", event => {
      if (!event.target.closest("#f-cargo-search") && !event.target.closest("#f-cargo-results")) cargoResults.classList.add("hidden");
    });

    $("f-vehicle").addEventListener("change", () => $("manual-vehicle-wrap").classList.toggle("hidden", $("f-vehicle").value !== "manual"));
    $("f-adr-toggle").addEventListener("change", () => $("adr-wrap").classList.toggle("hidden", !$("f-adr-toggle").checked));
    $("create-form").addEventListener("submit", (event) => {
      event.preventDefault();
      $("form-error").classList.add("hidden");
      if (!$("create-form").reportValidity()) return;
      const data = collect();
      if (!data.cargo || data.cargo.length < 2) return showFormError("Укажите наименование груза.");
      if (!data.vehicle_type || data.vehicle_type.length < 2) return showFormError("Укажите тип транспорта.");
      if (data.adr_class === "") return showFormError("Выберите класс ADR или отключите отметку опасного груза.");
      if (data.unloading_date && data.unloading_date < data.pickup_date) return showFormError("Дата выгрузки не может быть раньше даты загрузки.");
      $("preview").innerHTML = previewHtml(data);
      $("preview").classList.remove("hidden");
      $("preview").scrollIntoView({behavior:"smooth",block:"start"});
      $("edit-request").addEventListener("click", () => { $("preview").classList.add("hidden"); $("create-form").scrollIntoView({behavior:"smooth",block:"start"}); });
      $("publish-request").addEventListener("click", publish);
    });
  }
  async function publish() {
    const button = $("publish-request");
    const error = $("publish-error");
    error.classList.add("hidden");
    if (!tg?.initData) {
      error.textContent = "Откройте форму через Telegram-бот CargoLink, чтобы подтвердить аккаунт и опубликовать заявку.";
      error.classList.remove("hidden"); return;
    }
    button.disabled = true; button.textContent = "Публикуем…";
    try {
      const response = await fetch("/api/requests", {
        method:"POST", headers:{"Content-Type":"application/json","X-Telegram-Init-Data":tg.initData},
        body:JSON.stringify(collect())
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Не удалось сохранить заявку");
      $("preview").innerHTML = '<div class="success-state"><div class="success-mark">✓</div><p class="eyebrow">CARGOLINK MARKETPLACE</p><h3>Заявка опубликована</h3><p>Номер заявки: <strong>№' + esc(result.item.id) + '</strong></p><p>Заявка доступна перевозчикам в CargoLink.</p><button class="primary" id="close-app">Готово</button></div>';
      $("close-app").addEventListener("click", () => tg?.close());
    } catch (err) {
      error.textContent = err.message || "Ошибка публикации. Попробуйте ещё раз.";
      error.classList.remove("hidden");
      button.disabled = false; button.textContent = "Опубликовать заявку";
    }
  }

  if (!isCreateMode) {
    document.querySelectorAll(".tab").forEach((button) => button.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
      button.classList.add("active"); category = button.dataset.category; load();
    }));
    document.querySelectorAll("[data-route]").forEach((button) => button.addEventListener("click", () => {
      const [from,to] = button.dataset.route.split("|"); $("origin").value = from; $("destination").value = to; load();
    }));
    $("search").addEventListener("click", load);
    load();
  }
})();