"use strict";
// Fair Share front end: plain JavaScript, no libraries. Text from users is always set with
// textContent (never innerHTML), so names can't inject markup.

const $ = (id) => document.getElementById(id);
let state = null;
let view = "board"; // "board" or "settings"
const draft = {
  step: 1,
  people: [],
  chores: [
    { name: "Dishes", effort: 1 }, { name: "Take out trash", effort: 1 }, { name: "Vacuum", effort: 2 },
    { name: "Laundry", effort: 2 }, { name: "Clean bathroom", effort: 3 },
  ],
};

function el(tag, props = {}, ...kids) {
  const node = Object.assign(document.createElement(tag), props);
  for (const kid of kids) if (kid != null) node.append(kid);
  return node;
}

async function api(action, body) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 8000);
  const options = action === "state" ? { signal: ctrl.signal }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}), signal: ctrl.signal };
  try {
    const res = await fetch(`/api/${action}`, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Something went wrong. Please try again.");
    return data;
  } catch (err) {
    if (err.name === "AbortError" || err instanceof TypeError) {
      throw new Error("Can't reach Fair Share. Is it still running on the computer?");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function act(action, body, undoable = false) {
  try {
    const res = await api(action, body);
    state = res.state;
    render();
    toast(res.message, undoable);
    return true;
  } catch (err) {
    toast(err.message);
    refresh(); // the page may be out of date (someone else changed things)
    return false;
  }
}

async function refresh() {
  try {
    state = await api("state");
    render();
  } catch (err) {
    showNotice(err.message);
  }
}

let toastTimer;
function toast(text, undoable = false) {
  $("toast-text").textContent = text;
  $("toast-undo").hidden = !undoable;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), undoable ? 8000 : 4000);
}

function showNotice(text) {
  $("notice").textContent = text;
  $("notice").hidden = !text;
}

const nameOf = (id) => (state.people.find((p) => p.id === id) || {}).name || "someone";
const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);

function balanceText(b) {
  if (Math.abs(b) < 0.05) return "even";
  const n = Math.abs(b).toFixed(1).replace(/\.0$/, "");
  return b > 0 ? `${n} ahead` : `${n} behind`;
}

function dayText(iso) {
  const days = Math.round((new Date(today() + "T00:00") - new Date(iso + "T00:00")) / 86400000);
  return days <= 0 ? "today" : days === 1 ? "yesterday" : `${days} days ago`;
}

function effortSelect(value) {
  const select = el("select", { title: "Effort: 1 is quick, 5 is a big job" });
  for (let i = 1; i <= 5; i++) select.append(el("option", { value: i, textContent: `Effort ${i}`, selected: i === value }));
  return select;
}

function confirmButton(label, onConfirm) {
  const button = el("button", { className: "danger", textContent: label });
  button.onclick = () => {
    if (button.dataset.armed) return onConfirm();
    button.dataset.armed = "1";
    button.textContent = "Tap again to confirm";
    setTimeout(() => { delete button.dataset.armed; button.textContent = label; }, 3000);
  };
  return button;
}

function render() {
  const ready = state.setup_done;
  $("title").textContent = state.household || "Fair Share";
  document.title = state.household ? `${state.household} · Fair Share` : "Fair Share";
  $("wizard").hidden = ready;
  $("board").hidden = !ready || view !== "board";
  $("settings").hidden = !ready || view !== "settings";
  $("open-settings").hidden = !ready || view !== "board";
  $("close-settings").hidden = !ready || view !== "settings";
  if (state.recovered_from) {
    showNotice(state.recovered_from === "none"
      ? "Your data file was damaged and no backup could be read, so Fair Share started fresh. The damaged file was kept in your data folder."
      : "Your data file was damaged, so Fair Share restored the most recent backup.");
  }
  if (!ready) return renderWizard();
  return view === "board" ? renderBoard() : renderSettings();
}

function renderBoard() {
  $("balances").replaceChildren(...state.people.map((p) => el("li",
    { className: p.away ? "away" : p.balance < -0.05 ? "behind" : p.balance > 0.05 ? "ahead" : "" },
    el("strong", { textContent: p.name }), ` ${p.away ? "away" : balanceText(p.balance)}`)));
  $("board-empty").hidden = state.chores.length > 0;
  $("chores").replaceChildren(...state.chores.map(choreCard));
  $("history").replaceChildren(...(state.history.length
    ? state.history.map((h) => el("li", { textContent: `${h.by} did ${h.chore}, ${dayText(h.day)}` }))
    : [el("li", { className: "empty", textContent: "Nothing done yet. Tap a chore's button when it's finished." })]));
}

function choreCard(c) {
  const done = (personId) => act("done", { chore_id: c.id, person_id: personId }, true);
  const other = el("select", { title: "Someone else did it" },
    el("option", { value: "", textContent: "Someone else did it…" }),
    ...state.people.map((p) => el("option", { value: p.id, textContent: p.name })));
  other.onchange = () => other.value && done(other.value);
  const main = c.next
    ? el("button", { className: "primary", textContent: `${nameOf(c.next)} did it`, onclick: () => done(c.next) })
    : el("span", { className: "hint", textContent: "Everyone is away." });
  return el("article", { className: "card" },
    el("div", { className: "card-head" },
      el("h3", { textContent: c.name }),
      el("span", { className: "effort", title: `Effort ${c.effort} of 5`, textContent: "●".repeat(c.effort) + "○".repeat(5 - c.effort) })),
    el("p", { className: "hint", textContent: c.last_done ? `Last done by ${c.last_done.by}, ${dayText(c.last_done.day)}` : "Not done yet" }),
    el("div", { className: "row" }, main, other));
}

function renderSettings() {
  $("s-household").value = state.household;
  $("s-people").replaceChildren(...state.people.map((p) => {
    const until = el("input", { type: "date", value: p.away_until || "", min: today(), title: "Last day away" });
    const away = p.away
      ? el("button", { textContent: "I'm back", onclick: () => act("set_away", { person_id: p.id, until: null }) })
      : el("button", { textContent: "Set away", onclick: () => (until.value
        ? act("set_away", { person_id: p.id, until: until.value }) : toast("Pick the last day they'll be away first.")) });
    return el("li", {},
      el("span", { className: "grow" }, el("strong", { textContent: p.name }), p.away ? ` (away until ${p.away_until})` : ""),
      p.away ? null : el("label", { className: "small-label" }, "Away until", until), away, confirmButton("Remove", () => act("remove_person", { person_id: p.id })));
  }));
  $("s-chores").replaceChildren(...state.chores.map((c) => {
    const effort = effortSelect(c.effort);
    effort.onchange = () => act("edit_chore", { chore_id: c.id, effort: Number(effort.value) });
    return el("li", {}, el("strong", { className: "grow", textContent: c.name }), effort,
      confirmButton("Remove", () => act("remove_chore", { chore_id: c.id })));
  }));
}

function renderWizard() {
  document.querySelectorAll("#wizard .step").forEach((s) => (s.hidden = Number(s.dataset.step) !== draft.step));
  document.querySelectorAll(".steps li").forEach((li) => li.classList.toggle("current", Number(li.dataset.step) === draft.step));
  const remove = (list, i) => el("button", { className: "link", textContent: "remove", onclick: () => { list.splice(i, 1); renderWizard(); } });
  $("w-people").replaceChildren(...draft.people.map((name, i) => el("li", {}, el("span", { className: "grow", textContent: name }), remove(draft.people, i))));
  $("w-chores").replaceChildren(...draft.chores.map((c, i) => {
    const effort = effortSelect(c.effort);
    effort.onchange = () => (c.effort = Number(effort.value));
    return el("li", {}, el("span", { className: "grow", textContent: c.name }), effort, remove(draft.chores, i));
  }));
}

function wizardStep(delta) {
  if (delta > 0 && draft.step === 1 && !$("w-household").value.trim()) return toast("Give your home a name first.");
  if (delta > 0 && draft.step === 2 && draft.people.length < 2) return toast("Add at least two people.");
  draft.step += delta;
  renderWizard();
  const input = document.querySelector(`#wizard .step[data-step="${draft.step}"] input`);
  if (input) input.focus();
}

function onSubmit(formId, inputId, handle) {
  $(formId).addEventListener("submit", async (event) => {
    event.preventDefault();
    const value = $(inputId).value.trim();
    if (!value) return toast("Type a name first.");
    if (await handle(value)) $(inputId).value = "";
  });
}

function addToDraft(list, name, item) {
  if (list.some((x) => (x.name || x).toLowerCase() === name.toLowerCase())) { toast(`${name} is already in the list.`); return false; }
  list.push(item);
  renderWizard();
  return true;
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-next]").forEach((b) => (b.onclick = () => wizardStep(1)));
  document.querySelectorAll("[data-back]").forEach((b) => (b.onclick = () => wizardStep(-1)));
  const openSettings = () => { view = "settings"; render(); };
  $("open-settings").onclick = openSettings;
  document.querySelectorAll("[data-open-settings]").forEach((b) => (b.onclick = openSettings));
  $("close-settings").onclick = () => { view = "board"; render(); };
  $("toast-undo").onclick = () => act("undo");
  $("w-finish").onclick = () => (draft.chores.length
    ? act("setup", { household: $("w-household").value, people: draft.people, chores: draft.chores })
    : toast("Add at least one chore."));
  onSubmit("w-person-form", "w-person", (name) => addToDraft(draft.people, name, name));
  onSubmit("w-chore-form", "w-chore", (name) => addToDraft(draft.chores, name, { name, effort: 1 }));
  onSubmit("s-household-form", "s-household", (household) => act("rename_household", { household }));
  onSubmit("s-person-form", "s-person", (name) => act("add_person", { name }));
  onSubmit("s-chore-form", "s-chore", (name) => act("add_chore", { name, effort: 1 }));
  document.addEventListener("visibilitychange", () => document.visibilityState === "visible" && state && refresh());
  refresh();
});
