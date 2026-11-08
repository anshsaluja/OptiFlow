<script lang="ts">
  import type { PageData } from './$types';
  export let data: PageData;
  const fmt = (value: number) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2, signDisplay: 'always' }).format(value);
  const rate = (value: number | null) => value === null ? 'N/A' : `${(100 * value).toFixed(1)}%`;
</script>

<svelte:head>
  <title>OptiFlow | Scenario Lab</title>
  <meta name="description" content="Compare independently optimized supply-chain disruption scenarios" />
</svelte:head>

<main>
  <nav><a href="/">← Allocation overview</a><span>OPTIFLOW / SCENARIO LAB</span></nav>
  <header><div><p class="eyebrow">SUPPLY CHAIN RESILIENCE</p><h1>Scenario impact analysis</h1><p>Compare separately optimized disruptions against a common baseline. Ranked by incremental total cost.</p></div><div class="badge">LOCAL SNAPSHOTS</div></header>
  {#if data.error}
    <section class="empty"><h2>Scenario snapshots not ready</h2><p>{data.error}</p><p>Create <code>output/scenarios/manifest.json</code> and the referenced Scala-generated allocation reports, or set <code>OPTIFLOW_SCENARIOS_PATH</code>.</p></section>
  {:else if data.impacts.length === 0}
    <section class="empty"><h2>No scenarios configured</h2><p>Add scenario entries to the manifest to compare them against the baseline.</p></section>
  {:else}
    <div class="summary"><article><small>SCENARIOS ANALYZED</small><strong>{data.impacts.length}</strong></article><article><small>HIGHEST INCREMENTAL COST</small><strong>{fmt(data.impacts[0].costDelta)}</strong><p>{data.impacts[0].label}</p></article></div>
    <section class="panel"><h2>Disruption ranking</h2><p class="caption">Positive cost and shortage deltas indicate a worse outcome. Monetary values use dataset units.</p><div class="scroll"><table><thead><tr><th>SCENARIO</th><th>TOTAL COST Δ</th><th>COST CHANGE</th><th>FULFILLED Δ</th><th>SHORTAGE Δ</th><th>FULFILLMENT</th></tr></thead><tbody>
      {#each data.impacts as impact (impact.id)}
        <tr><td><strong>{impact.label}</strong><small>{impact.id}</small></td><td class:bad={impact.costDelta > 0} class:good={impact.costDelta < 0}>{fmt(impact.costDelta)}</td><td>{impact.costDeltaPercent === null ? 'N/A' : `${fmt(impact.costDeltaPercent)}%`}</td><td>{fmt(impact.fulfilledDelta)}</td><td class:bad={impact.shortageDelta > 0}>{fmt(impact.shortageDelta)}</td><td>{rate(impact.fulfillmentRate)}</td></tr>
      {/each}
    </tbody></table></div></section>
    <section class="panel"><h2>Cost drivers</h2><p class="caption">Each scenario's change in transportation spend and shortage penalties relative to baseline.</p><div class="scroll"><table><thead><tr><th>SCENARIO</th><th>TRANSPORT Δ</th><th>SHORTAGE PENALTY Δ</th><th>BASELINE FULFILLMENT</th></tr></thead><tbody>
      {#each data.impacts as impact (impact.id)}
        <tr><td><strong>{impact.label}</strong></td><td>{fmt(impact.transportDelta)}</td><td>{fmt(impact.shortagePenaltyDelta)}</td><td>{rate(impact.baselineFulfillmentRate)}</td></tr>
      {/each}
    </tbody></table></div></section>
  {/if}
  <footer>Comparisons use validated, independently generated optimizer snapshots. This page does not solve scenarios in the browser.</footer>
</main>
<style>
  :global(body){margin:0;background:#0b1424;color:#eaf0fb;font-family:Inter,ui-sans-serif,system-ui,sans-serif} :global(*){box-sizing:border-box}
  main{max-width:1320px;margin:auto;padding:42px 38px}nav{display:flex;justify-content:space-between;gap:12px;color:#7796ad;font-size:12px;letter-spacing:1px}a{color:#63dfc5;text-decoration:none}header{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:55px 0 35px}h1{font-size:38px;letter-spacing:-1px;margin:8px 0}h2{font-size:20px}header p,.caption,.empty p{color:#91a8bf;line-height:1.6}.eyebrow{color:#5ee4c8;font-size:11px;letter-spacing:2px}.badge{white-space:nowrap;border:1px solid #29685b;background:#143a38;color:#79eac9;padding:12px 16px;border-radius:30px;font-size:11px}.summary{display:grid;grid-template-columns:1fr 2fr;gap:18px;margin-bottom:24px}.summary article,.panel,.empty{background:#142238;border:1px solid #293b50;border-radius:16px;padding:26px}.summary small{display:block;color:#91a8bf;font-size:11px;letter-spacing:1px}.summary strong{display:block;font-size:32px;margin-top:12px}.summary p{color:#9db0c6;margin:5px 0}.panel{margin-bottom:22px}.caption{font-size:13px}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;text-align:left;margin-top:20px}th{font-size:10px;letter-spacing:1px;color:#8fa5bc;border-bottom:1px solid #35465b;padding:14px 10px;white-space:nowrap}td{padding:18px 10px;border-bottom:1px solid #293a4d;font-size:13px;white-space:nowrap}td small{display:block;color:#7d94ac;margin-top:6px}.bad{color:#ff9a9a}.good{color:#6ee7bd}footer{font-size:12px;color:#8197b0;margin:30px 0}code{color:#6ee7bd;overflow-wrap:anywhere}
  @media(max-width:720px){main{padding:24px 16px}header{display:block;margin:35px 0}h1{font-size:30px}.badge{display:inline-block;margin-top:14px}.summary{grid-template-columns:1fr}.panel{padding:18px}}
</style>
