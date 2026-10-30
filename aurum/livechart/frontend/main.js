// Aurum live chart: a Streamlit component (plain JavaScript, no build step) around TradingView Lightweight Charts.
// Python sends a payload (see aurum/livechart/payload.py); everything shown is computed by Aurum. While the symbol,
// timeframe and layout stay the same, new data updates the series in place, so zoom and scroll are kept.
(function () {
  const LW = window.LightweightCharts;
  const el = document.getElementById("chart");
  const legend = document.getElementById("legend");
  const tip = document.getElementById("tip");
  const status = document.getElementById("status");
  let chart = null, layoutKey = null, series = {}, markersApi = null, payload = null, priceLines = [];

  function send(type, extra) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, extra || {}), "*");
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  function fmt(v, d) {
    if (v == null || !isFinite(v)) return "–";
    return Number(v).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function timeKey(t) {
    if (t == null) return "";
    if (typeof t === "object" && t.year) return t.year + "-" + String(t.month).padStart(2, "0") + "-" + String(t.day).padStart(2, "0");
    return String(t);
  }

  function colours(dark) {
    return {
      bg: dark ? "#0e1117" : "#ffffff", text: dark ? "#ecebe6" : "#1f1f1d", grid: dark ? "rgba(160,160,160,0.12)" : "rgba(128,128,128,0.14)",
      up: "#1baf7a", down: "#e34948", volUp: "rgba(27,175,122,0.35)", volDown: "rgba(227,73,72,0.35)", edge: dark ? "#3a3d45" : "#d8d7d2",
    };
  }

  function build(p) {
    if (chart) { chart.remove(); chart = null; }
    series = {}; priceLines = []; markersApi = null;
    const c = colours(p.dark);
    document.documentElement.setAttribute("data-theme", p.dark ? "dark" : "light");
    el.style.height = p.height + "px";
    chart = LW.createChart(el, {
      autoSize: true,
      layout: { background: { type: "solid", color: c.bg }, textColor: c.text, fontSize: 11, panes: { separatorColor: c.edge, enableResize: true } },
      grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } },
      rightPriceScale: { borderColor: c.edge },
      timeScale: { borderColor: c.edge, timeVisible: p.intraday, secondsVisible: false, rightOffset: 4 },
      crosshair: { mode: 1 },
    });
    // main pane: candles, volume underneath, price-type indicators on top
    series.candles = chart.addSeries(LW.CandlestickSeries, {
      upColor: c.up, downColor: c.down, borderUpColor: c.up, borderDownColor: c.down, wickUpColor: c.up, wickDownColor: c.down,
      priceLineVisible: true, lastValueVisible: true,
    }, 0);
    series.volume = chart.addSeries(LW.HistogramSeries, { priceScaleId: "vol", priceFormat: { type: "volume" }, lastValueVisible: false, priceLineVisible: false }, 0);
    series.volume.priceScale().applyOptions({ scaleMargins: { top: 0.84, bottom: 0 } });
    series.candles.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: 0.2 } });
    (p.overlays || []).forEach(o => {
      series["ov:" + o.name] = chart.addSeries(LW.LineSeries, {
        color: o.color, lineWidth: o.width || 2, lineStyle: o.dashed ? 2 : 0, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: "",
      }, 0);
    });
    // lower panes: oscillators, then the decision strip
    let pane = 1;
    (p.panels || []).forEach(pn => {
      pn.series.forEach(s => {
        const def = s.kind === "histogram" ? LW.HistogramSeries : LW.LineSeries;
        const opts = s.kind === "histogram" ? { color: s.color, priceLineVisible: false, lastValueVisible: false }
          : { color: s.color, lineWidth: 2, priceLineVisible: false, lastValueVisible: true, crosshairMarkerVisible: false, title: String(s.name).slice(0, 28) };
        const ser = chart.addSeries(def, opts, pane);
        (pn.levels || []).forEach(lv => ser.createPriceLine({ price: lv, color: c.edge, lineWidth: 1, lineStyle: 2, axisLabelVisible: false }));
        series["pn:" + pn.title + ":" + s.name] = ser;
      });
      pane += 1;
    });
    if (p.strip && p.strip.length) {
      // a thin band along the top of the price pane: blue = the strategy holds the asset, grey = cash
      series.strip = chart.addSeries(LW.HistogramSeries, { priceScaleId: "strip", priceLineVisible: false, lastValueVisible: false }, 0);
      series.strip.priceScale().applyOptions({ scaleMargins: { top: 0, bottom: 0.965 }, visible: false });
    }
    // relative pane heights: price pane biggest
    chart.panes().forEach((pp, i) => pp.setStretchFactor(i === 0 ? 3000 : 1000));
    markersApi = LW.createSeriesMarkers(series.candles, []);
    chart.subscribeCrosshairMove(onMove);
  }

  function setAll(p, keepRange) {
    const range = keepRange ? chart.timeScale().getVisibleLogicalRange() : null;
    series.candles.setData(p.bars);
    series.volume.setData(p.volume);
    (p.overlays || []).forEach(o => series["ov:" + o.name] && series["ov:" + o.name].setData(o.data));
    (p.panels || []).forEach(pn => pn.series.forEach(s => {
      const ser = series["pn:" + pn.title + ":" + s.name];
      if (ser) ser.setData(s.data);
    }));
    if (series.strip) series.strip.setData(p.strip);
    markersApi.setMarkers(p.markers || []);
    priceLines.forEach(l => series.candles.removePriceLine(l));
    priceLines = (p.price_lines || []).map(l => series.candles.createPriceLine({
      price: l.price, color: l.color, lineWidth: 1, lineStyle: l.style || 2, axisLabelVisible: true, title: l.title,
    }));
    if (range) chart.timeScale().setVisibleLogicalRange(range);
    else if (p.visible_bars) {
      const n = p.bars.length;
      chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, n - p.visible_bars), to: n + 3 });
    }
  }

  function legendHtml(p, i) {
    const b = i != null ? p.bars[i] : p.bars[p.bars.length - 1];
    if (!b) return "";
    const v = i != null ? p.volume[i] : p.volume[p.volume.length - 1];
    let h = '<div class="title">' + esc(p.title) + "</div>";
    h += '<div class="row">O ' + fmt(b.open, 2) + "  H " + fmt(b.high, 2) + "  L " + fmt(b.low, 2) + "  C " + fmt(b.close, 2)
      + (v ? "  Vol " + fmt(v.value, 0) : "") + "</div>";
    (p.overlays || []).forEach(o => {
      const pt = i != null ? o.byTime[timeKey(b.time)] : o.data.length ? o.data[o.data.length - 1].value : null;
      h += '<div class="row"><span style="color:' + o.color + '">■</span> ' + esc(o.name) + " " + fmt(pt, 2) + "</div>";
    });
    return h;
  }

  function onMove(param) {
    if (!payload) return;
    if (!param || !param.time) {
      legend.innerHTML = legendHtml(payload, null);
      tip.style.display = "none";
      return;
    }
    const k = timeKey(param.time);
    const i = payload.index[k];
    legend.innerHTML = legendHtml(payload, i);
    const t = payload.tips[k];
    if (t) {
      tip.innerHTML = t;
      tip.style.display = "block";
    } else {
      tip.style.display = "none";
    }
  }

  function render(args, theme) {
    const p = args.payload;
    // lookup tables for the hover legend
    p.index = {}; p.bars.forEach((b, i) => { p.index[timeKey(b.time)] = i; });
    (p.overlays || []).forEach(o => { o.byTime = {}; o.data.forEach(d => { o.byTime[timeKey(d.time)] = d.value; }); });
    p.dark = theme && theme.base === "dark";
    const key = p.layout_key + (p.dark ? ":dark" : ":light");
    if (key !== layoutKey || !chart) {
      build(p);
      layoutKey = key;
      setAll(p, false);
    } else {
      setAll(p, true);
    }
    payload = p;
    legend.innerHTML = legendHtml(p, null);
    status.textContent = p.status || "";
    send("streamlit:setFrameHeight", { height: p.height + 4 });
  }

  window.addEventListener("message", ev => {
    const d = ev.data;
    if (!d || d.type !== "streamlit:render") return;
    try {
      render(d.args, d.theme);
    } catch (e) {
      status.textContent = "Chart error: " + e.message;
      send("streamlit:setFrameHeight", { height: 80 });
    }
  });
  window.__aurum = () => ({ chart: chart, payload: payload, series: series });  // used by the automated screenshot test
  window.addEventListener("error", e => { status.textContent = "Chart error: " + (e.message || e); });
  send("streamlit:componentReady", { apiVersion: 1 });
})();
