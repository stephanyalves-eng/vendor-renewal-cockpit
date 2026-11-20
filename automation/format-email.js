// Activepieces "Code" step for the weekly renewal alert.
// Input `rows`: the JSON body returned by the HTTP step (v_renewals_due, deadline within 30 days).
// Output: { send, subject, html, text }. The flow sends the e-mail only when `send` is true.
export const code = async (inputs) => {
  let rows = inputs.rows;
  if (typeof rows === "string") rows = JSON.parse(rows || "[]");
  if (!Array.isArray(rows)) rows = [];

  const brl = (n) => "BRL " + Number(n).toLocaleString("en-US", { maximumFractionDigits: 0 });
  const date = (iso) => {
    const [y, m, d] = String(iso).slice(0, 10).split("-");
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${Number(d)} ${months[Number(m) - 1]} ${y}`;
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const sorted = [...rows].sort((a, b) => String(a.decision_deadline).localeCompare(String(b.decision_deadline)));
  const subject = `Renewal decisions due: ${sorted.length} contract${sorted.length === 1 ? "" : "s"}`;
  const site = "https://stephanyalves-eng-renewal-cockpit.stephany-alves.workers.dev/renewals";

  const cell = 'style="padding:6px 10px;border-bottom:1px solid #e5e1d6;text-align:left"';
  const right = 'style="padding:6px 10px;border-bottom:1px solid #e5e1d6;text-align:right"';
  const body = sorted
    .map((r) => `<tr><td ${cell}>${esc(r.vendor_name)}</td><td ${cell}>${date(r.decision_deadline)} (${r.days_to_deadline} days)</td><td ${cell}>${esc(r.recommendation)}${r.auto_renew ? " · auto-renews" : ""}</td><td ${right}>${brl(r.estimated_annual_impact)}</td></tr>`)
    .join("");
  const html = `<div style="font-family:Arial,sans-serif;color:#1d2b28">
<p><strong>${esc(subject)}</strong> (synthetic data, scenario date 30 Nov 2026)</p>
<table style="border-collapse:collapse;font-size:14px">
<thead><tr><th ${cell}>Vendor</th><th ${cell}>Decision deadline</th><th ${cell}>Recommendation</th><th ${right}>Est. annual impact</th></tr></thead>
<tbody>${body}</tbody></table>
<p><a href="${site}">Open the Renewals page</a></p></div>`;
  const text = [subject, ...sorted.map((r) => `- ${r.vendor_name}: decide by ${date(r.decision_deadline)}, ${r.recommendation}, ${brl(r.estimated_annual_impact)}`), site].join("\n");

  return { send: sorted.length > 0, subject, html, text };
};
