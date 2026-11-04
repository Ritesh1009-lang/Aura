(() => {
  const form = document.getElementById("quiz-form");
  if (!form) return;

  const cards = Array.from(form.querySelectorAll(".checkin-question"));
  const navigation = document.getElementById("quiz-navigation");
  const previous = document.getElementById("quiz-previous");
  const next = document.getElementById("quiz-next");
  const submit = document.getElementById("quiz-submit");
  const fallbackSubmit = form.querySelector(".quiz-fallback-submit");
  const progress = document.getElementById("quiz-progress");
  const error = document.getElementById("quiz-answer-error");
  let current = 0;

  if (!cards.length) return;

  const clearError = () => {
    error.hidden = true;
    cards[current].removeAttribute("aria-invalid");
  };

  const validateCurrent = () => {
    const card = cards[current];
    if (card.querySelector('input[type="radio"]:checked')) {
      clearError();
      return true;
    }

    error.textContent = `Please select an answer for question ${current + 1} to continue.`;
    error.hidden = false;
    card.setAttribute("aria-invalid", "true");
    card.querySelector('input[type="radio"]').focus();
    return false;
  };

  const showQuestion = (index) => {
    cards[current].removeAttribute("aria-invalid");
    current = index;
    cards.forEach((card, cardIndex) => {
      card.hidden = cardIndex !== current;
    });
    progress.textContent = `Question ${current + 1} of ${cards.length}`;
    previous.disabled = current === 0;
    next.hidden = current === cards.length - 1;
    submit.hidden = current !== cards.length - 1;
    clearError();
    cards[current].focus();
  };

  const goNext = () => {
    if (current < cards.length - 1 && validateCurrent()) {
      showQuestion(current + 1);
    }
  };

  previous.addEventListener("click", () => {
    if (current > 0) showQuestion(current - 1);
  });
  next.addEventListener("click", goNext);
  form.addEventListener("change", (event) => {
    if (event.target.matches('input[type="radio"]')) clearError();
  });
  form.addEventListener("submit", (event) => {
    const unanswered = cards.findIndex(
      (card) => !card.querySelector('input[type="radio"]:checked')
    );
    if (unanswered !== -1) {
      event.preventDefault();
      showQuestion(unanswered);
      validateCurrent();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (!event.altKey || !["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    if (event.key === "ArrowRight") goNext();
    else if (current > 0) showQuestion(current - 1);
  });

  fallbackSubmit.hidden = true;
  navigation.hidden = false;
  showQuestion(0);
})();
