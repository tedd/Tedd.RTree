document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const source = document.getElementById(button.dataset.copyTarget);
    if (!source) return;

    const original = button.textContent;
    try {
      await navigator.clipboard.writeText(source.textContent.trim());
      button.textContent = "Copied";
    } catch {
      const selection = window.getSelection();
      selection?.removeAllRanges();
      const range = document.createRange();
      range.selectNodeContents(source);
      selection?.addRange(range);
      button.textContent = "Selected";
    }
    window.setTimeout(() => { button.textContent = original; }, 1800);
  });
});

const fixtureSelect = document.getElementById("comparison-fixture");
if (fixtureSelect) {
  const dataRequest = fetch("assets/mutable-packed.json").then((response) => {
    if (!response.ok) throw new Error("Comparison data unavailable");
    return response.json();
  });
  // The initial charts and complete table are static and remain readable if loading fails.
  dataRequest.catch(() => { fixtureSelect.disabled = true; });
  fixtureSelect.addEventListener("change", async () => {
    try {
      const data = await dataRequest;
      const [sizeText, distribution] = fixtureSelect.value.split("/");
      const size = Number(sizeText);
      document.querySelectorAll(".package-chart").forEach((chart) => {
        const operation = chart.dataset.operation;
        const rows = data.results.filter((row) => row.size === size && row.distribution === distribution && row.operation === operation).sort((a, b) => a.medianUs - b.medianUs);
        const units = operation === "build" ? size : 64;
        const peak = units / rows[0].medianUs;
        chart.querySelector("[data-fixture]").textContent = `${size.toLocaleString("en-GB")} ${distribution.toLowerCase()} rectangles`;
        const container = chart.querySelector(".package-chart-rows");
        container.replaceChildren(...rows.map((row) => {
          const own = row.library === "candidate";
          const rate = units / row.medianUs;
          const element = document.createElement("div");
          element.className = `bar-row${own ? " comparison-ours" : ""}`;
          const name = document.createElement("span");
          name.textContent = row.label;
          const track = document.createElement("div");
          track.className = "bar-track";
          const bar = document.createElement("i");
          bar.className = `bar ${own ? "ours" : "other"}`;
          bar.style.width = `${rate / peak * 100}%`;
          track.append(bar);
          const value = document.createElement("b");
          value.textContent = rate.toFixed(3);
          element.append(name, track, value);
          return element;
        }));
      });
    } catch {
      fixtureSelect.disabled = true;
    }
  });
}

const genericControls = document.querySelector(".generic-controls");
if (genericControls) {
  const dimension = document.getElementById("generic-dimension");
  const coordinate = document.getElementById("generic-coordinate");
  const mode = document.getElementById("generic-mode");
  const fixture = document.getElementById("generic-fixture");
  const request = fetch("assets/generic-packed.json").then((response) => {
    if (!response.ok) throw new Error("Generic comparison unavailable");
    return response.json();
  });
  request.catch(() => genericControls.querySelectorAll("select").forEach((select) => { select.disabled = true; }));
  genericControls.addEventListener("change", async () => {
    try {
      const data = await request;
      const wrapper = mode.value !== "plain";
      if (wrapper) fixture.value = "10000/uniform";
      fixture.disabled = wrapper;
      const [n, distribution] = fixture.value.split("/");
      const size = Number(n);
      const description = `${dimension.value}D ${coordinate.value} · ${size.toLocaleString("en-GB")} ${distribution} entries · ${mode.value}`;
      const selected = data.results.filter((row) => row.dimension === Number(dimension.value) && row.coordinate === coordinate.value && row.mode === mode.value && row.size === size && row.distribution === distribution);
      document.getElementById("generic-caption").textContent = description;
      document.querySelectorAll(".generic-chart").forEach((chart) => {
        const operation = chart.dataset.operation;
        const rows = selected.filter((row) => row.operation === operation).sort((a, b) => a.medianUs - b.medianUs);
        const units = operation === "build" ? size : 64;
        const peak = units / rows[0].medianUs;
        chart.querySelector("[data-generic-fixture]").textContent = description;
        chart.querySelector(".generic-chart-rows").replaceChildren(...rows.map((row) => {
          const current = row.stage === "candidate";
          const element = document.createElement("div"); element.className = `bar-row${current ? " comparison-ours" : ""}`;
          const label = document.createElement("span"); label.textContent = current ? "Current (C#)" : "Previous (C#)";
          const track = document.createElement("div"); track.className = "bar-track";
          const bar = document.createElement("i"); bar.className = `bar ${current ? "ours" : "other"}`;
          const rate = units / row.medianUs; bar.style.width = `${rate / peak * 100}%`; track.append(bar);
          const number = document.createElement("b"); number.textContent = rate.toFixed(3);
          element.append(label, track, number); return element;
        }));
      });
      document.getElementById("generic-timings").replaceChildren(...["build", "queries"].map((operation) => {
        const old = selected.find((row) => row.stage === "control" && row.operation === operation).medianUs;
        const current = selected.find((row) => row.stage === "candidate" && row.operation === operation).medianUs;
        const scale = operation === "build" ? 1000 : 1; const unit = operation === "build" ? "ms" : "µs";
        const tr = document.createElement("tr"); const th = document.createElement("th"); th.scope = "row"; th.textContent = operation === "build" ? "Bulk build" : "64 queries"; tr.append(th);
        for (const [value, className] of [[`${(old / scale).toFixed(3)} ${unit}`, ""], [`${(current / scale).toFixed(3)} ${unit}`, "comparison-ours"], [`${(old / current).toFixed(2)}×`, ""]]) {
          const td = document.createElement("td"); td.className = className; td.textContent = value; tr.append(td);
        }
        return tr;
      }));
    } catch {
      genericControls.querySelectorAll("select").forEach((select) => { select.disabled = true; });
    }
  });
}
