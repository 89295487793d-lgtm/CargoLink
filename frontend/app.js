(() => {
  const tg = window.Telegram?.WebApp;
  tg?.ready(); tg?.expand();
  const messages = {
    find:"Поиск грузов подключим следующим этапом.",
    create:"Форму размещения заявки подключим следующим этапом.",
    liquid:"Каталог наливных грузов подключим следующим этапом.",
    dry:"Каталог сухих грузов подключим следующим этапом.",
    vehicles:"Раздел свободных автомобилей подключим следующим этапом.",
    profile:"Профиль доступен через Telegram-бота; полноценный экран будет добавлен позже."
  };
  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const text = messages[button.dataset.action] || "Раздел готовится.";
      if (tg?.showAlert) tg.showAlert(text); else window.alert(text);
    });
  });
})();
