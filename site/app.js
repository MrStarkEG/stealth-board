"use strict";

const IP_NOTES = {
  datacenter: "Datacenter IP: tests run on a cloud server with no proxy. This is the hardest case, because protection systems trust these addresses the least.",
  residential: "Residential IP: tests run on a home internet connection with no proxy.",
};
const IP_LABELS = { datacenter: "Datacenter IP", residential: "Residential IP" };
const TARGET_GROUPS = [["open", "No protection"], ["test", "Bot test pages"], ["site", "Protected sites"]];
const GOOD_RATE = 0.8;
const POOR_RATE = 0.3;
const SPARK = { width: 90, height: 22, days: 30 };

// Every value from the results goes in as text, never as HTML.
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children);
  return node;
}

function percent(passed, tries) {
  return tries ? Math.round((100 * passed) / tries) + "%" : "-";
}

function tone(passed, tries) {
  if (!tries) return "none";
  const rate = passed / tries;
  return rate >= GOOD_RATE ? "good" : rate >= POOR_RATE ? "mid" : "bad";
}

function scoreBadge(passed, tries) {
  return el("span", { className: "cell " + tone(passed, tries), textContent: percent(passed, tries) });
}

function trendLine(daily) {
  const svgNs = "http://www.w3.org/2000/svg";
  const points = daily
    .map((score, day) => (score === null ? null : [(day * SPARK.width) / (SPARK.days - 1), SPARK.height - 2 - score * (SPARK.height - 4)]))
    .filter(Boolean);
  if (points.length === 1) points.push([SPARK.width, points[0][1]]);

  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("class", "spark");
  svg.setAttribute("viewBox", `0 0 ${SPARK.width} ${SPARK.height}`);
  const line = document.createElementNS(svgNs, "polyline");
  line.setAttribute("points", points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" "));
  const title = document.createElementNS(svgNs, "title");
  title.textContent = "Daily score, last 30 days";
  svg.append(line, title);
  return svg;
}

function groupTargets(targets) {
  return TARGET_GROUPS
    .map(([kind, label]) => ({ label, targets: targets.filter((target) => target.kind === kind) }))
    .filter((group) => group.targets.length);
}

function cellTooltip(cell) {
  if (!cell.tries_30d) return "Not tested yet";
  const week = [`${cell.passed_7d} of ${cell.tries_7d} tries passed` + (cell.after_click ? ` (${cell.after_click} after clicking the check box)` : "")];
  if (cell.challenge) week.push(`${cell.challenge} stuck on a challenge`);
  if (cell.blocked) week.push(`${cell.blocked} blocked`);
  if (cell.error) week.push(`${cell.error} errors`);
  const lastFailure = cell.last_failure ? ` Last failure: ${cell.last_failure}` : "";
  return `7 days: ${week.join(", ")}. 30 days: ${cell.passed_30d} of ${cell.tries_30d} passed.${lastFailure}`;
}

// One word under the number: the most common way it failed, or that it needed a click.
function cellNote(cell) {
  const failures = [["challenge", cell.challenge], ["blocked", cell.blocked], ["error", cell.error]];
  const [kind, count] = failures.sort((a, b) => b[1] - a[1])[0];
  if (count) return kind;
  return cell.after_click ? "with click" : "";
}

function targetCell(cell, startsGroup) {
  const td = el("td", { className: startsGroup ? "first" : "", title: cellTooltip(cell) }, scoreBadge(cell.passed_7d, cell.tries_7d));
  const note = cellNote(cell);
  if (note) td.append(el("small", { className: "why", textContent: note }));
  return td;
}

function nameCell(row) {
  const td = el("td", { className: "name" }, el("b", { textContent: row.tool }), el("span", { className: "tag", textContent: row.mode }));
  if (row.control) td.append(el("span", { className: "tag", textContent: "control" }));
  const version = row.version ? `v${row.version}, ` : "";
  td.append(el("small", { textContent: `${version}run ${row.last_run}` }));
  return td;
}

function toolRow(row, targets, groupStarts) {
  if (row.broken !== null) {
    const message = "Broken: the newest release failed to install or start. " + row.broken;
    return el("tr", { className: "broken" }, nameCell(row), el("td", { className: "msg", colSpan: 3 + targets.length, textContent: message }));
  }
  const tr = el("tr", {}, nameCell(row),
    el("td", {}, scoreBadge(row.passed_7d, row.tries_7d)),
    el("td", {}, scoreBadge(row.passed_30d, row.tries_30d)),
    el("td", {}, trendLine(row.daily)));
  for (const target of targets) tr.append(targetCell(row.cells[target.id], groupStarts.has(target.id)));
  return tr;
}

function tableHead(groups, flags, groupStarts) {
  const groupRow = el("tr", {},
    el("th", { className: "name", rowSpan: 2, textContent: "Library" }),
    el("th", { rowSpan: 2, textContent: "Score 7 days" }),
    el("th", { rowSpan: 2, textContent: "30 days" }),
    el("th", { rowSpan: 2, textContent: "Trend" }));
  const targetRow = el("tr");
  for (const group of groups) {
    groupRow.append(el("th", { className: "group", colSpan: group.targets.length, textContent: group.label }));
    for (const target of group.targets) {
      const th = el("th", { className: groupStarts.has(target.id) ? "first" : "" },
        el("a", { href: target.url, textContent: target.name, rel: "noopener nofollow" }));
      if (flags[target.id]) th.append(" ", el("span", { className: "flag", textContent: "⚠", title: flags[target.id] }));
      th.append(el("small", { textContent: target.vendor }));
      targetRow.append(th);
    }
  }
  return el("thead", {}, groupRow, targetRow);
}

function weakTargetList(targets, flags) {
  const flagged = targets.filter((target) => flags[target.id]);
  if (!flagged.length) return [];
  const items = flagged.map((target) => el("li", {}, el("b", { textContent: target.name + ": " }), flags[target.id]));
  return [el("h2", { textContent: "Targets to read with care" }), el("ul", {}, ...items)];
}

function showBoard(data, ipType) {
  const board = data.boards[ipType];
  const groups = groupTargets(data.targets);
  const targets = groups.flatMap((group) => group.targets);
  const groupStarts = new Set(groups.map((group) => group.targets[0].id));

  document.getElementById("ipnote").textContent = IP_NOTES[ipType];
  const body = el("tbody", {}, ...board.rows.map((row) => toolRow(row, targets, groupStarts)));
  document.getElementById("board").replaceChildren(tableHead(groups, board.flags, groupStarts), body);
  document.getElementById("flags").replaceChildren(...weakTargetList(targets, board.flags));
}

function showDashboard(data) {
  const updated = document.getElementById("updated");
  const ipTypes = Object.keys(data.boards);
  if (!ipTypes.length) {
    updated.textContent = "No results yet. The first run will fill this page.";
    return;
  }
  updated.textContent = `Last run: ${data.generated} (UTC). Updated once a day.`;

  const tabs = document.getElementById("tabs");
  const select = (ipType) => {
    for (const tab of tabs.children) tab.setAttribute("aria-pressed", tab.dataset.ipType === ipType);
    showBoard(data, ipType);
  };
  for (const ipType of ipTypes) {
    const tab = el("button", { textContent: IP_LABELS[ipType] });
    tab.dataset.ipType = ipType;
    tab.onclick = () => select(ipType);
    tabs.append(tab);
  }
  select(ipTypes[0]);
}

fetch("data.json")
  .then((response) => response.json())
  .then(showDashboard)
  .catch(() => {
    document.getElementById("updated").textContent = "No results yet. The first run will fill this page.";
  });
