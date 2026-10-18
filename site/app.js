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
