/* auroraWX live-data module. No dependencies. Reads its config from the
   JSON <script id="aurora-config"> block emitted by each aurora page.
   All fetches degrade silently to em-dashes on failure. */
(function () {
  'use strict';

  var cfgEl = document.getElementById('aurora-config');
  if (!cfgEl) return;
  var cfg;
  try {
    cfg = JSON.parse(cfgEl.textContent);
  } catch (e) {
    return;
  }
  var page = cfg.page || '';

  var kpChart = null;

  var QUIET = '#43a047', MODERATE = '#fdd835', ELEVATED = '#fb8c00', STORM = '#e53935';

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function lastOf(json) {
    return Array.isArray(json) ? json[json.length - 1] : json;
  }

  function pick(obj, names) {
    if (!obj) return null;
    for (var i = 0; i < names.length; i++) {
      var v = obj[names[i]];
      if (v !== undefined && v !== null && !isNaN(Number(v))) return Number(v);
    }
    return null;
  }

  function fetchJson(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function normalizeKp(json) {
    var out = [];
    (Array.isArray(json) ? json : []).forEach(function (e) {
      var kp = pick(e, ['kp_index', 'estimated_kp', 'kp']);
      if (kp === null || !e.time_tag) return;
      var t = new Date(String(e.time_tag).replace(' ', 'T') + 'Z').getTime();
      if (!isNaN(t)) out.push({ t: t, kp: kp });
    });
    out.sort(function (a, b) { return a.t - b.t; });
    return out;
  }

  /* Status rule (old-site parity): Kp>=5 storm; Kp>=4 & Bz<-5 elevated;
     Kp>=3 moderate; else quiet. */
  function badgeFor(kp, bz) {
    if (kp >= 5) return { text: 'STORM', color: STORM };
    if (kp >= 4 && bz < -5) return { text: 'ELEVATED', color: ELEVATED };
    if (kp >= 3) return { text: 'MODERATE', color: MODERATE };
    return { text: 'QUIET', color: QUIET };
  }

  function renderStatus(kpSeries, bz, wind) {
    var kp = kpSeries.length ? kpSeries[kpSeries.length - 1].kp : null;
    var b = badgeFor(kp === null ? -1 : kp, bz === null ? 0 : bz);
    setText('kp-now', kp === null ? '\u2014' : kp.toFixed(1));
    setText('bz-now', bz === null ? '\u2014' : bz.toFixed(1));
    setText('wind-now', wind === null ? '\u2014' : String(Math.round(wind)));
    var cutoff = Date.now() - 24 * 3600 * 1000;
    var recent = kpSeries.filter(function (p) { return p.t >= cutoff; });
    setText('kp-peak', recent.length
      ? String(Math.max.apply(null, recent.map(function (p) { return p.kp; })))
      : '\u2014');
    var badge = document.getElementById('aurora-badge');
    if (badge && kp !== null) {
      badge.textContent = b.text;
      badge.style.backgroundColor = b.color;
    }
  }

  function renderKpChart(kpSeries) {
    var el = document.getElementById('kp-chart');
    if (!el || !window.ApexCharts || !kpSeries.length) return;
    var cutoff = Date.now() - 24 * 3600 * 1000;
    var data = kpSeries.filter(function (p) { return p.t >= cutoff; })
      .map(function (p) {
        return { x: p.t, y: p.kp,
                 fillColor: p.kp >= 5 ? STORM : p.kp >= 4 ? ELEVATED
                          : p.kp >= 3 ? MODERATE : QUIET };
      });
    if (kpChart) {
      kpChart.destroy();
      kpChart = null;
    }
    kpChart = new ApexCharts(el, {
      chart: { type: 'bar', height: 220, animations: { enabled: false } },
      theme: { mode: window.theme_mode || 'dark' },
      plotOptions: { bar: { columnWidth: '90%' } },
      dataLabels: { enabled: false },
      xaxis: { type: 'datetime' },
      yaxis: { min: 0, max: 9, tickAmount: 9 },
      series: [{ name: 'Kp', data: data }]
    });
    kpChart.render();
  }

  function xrayClass(flux) {
    if (flux === null) return '\u2014';
    if (flux >= 1e-4) return 'X';
    if (flux >= 1e-5) return 'M';
    if (flux >= 1e-6) return 'C';
    if (flux >= 1e-7) return 'B';
    return 'A';
  }

  function fetchSpaceWeather() {
    var bz = null, wind = null;
    var kpPromise = fetchJson(cfg.kpUrl).then(normalizeKp)
      .catch(function () { return []; });
    function freshEntry(j, maxAgeMs) {
      var e = lastOf(j);
      if (!e || !e.time_tag) return null;
      var s = String(e.time_tag);
      var t = new Date(s.replace(' ', 'T') + (/[Zz]$/.test(s) ? '' : 'Z')).getTime();
      if (isNaN(t) || Date.now() - t > maxAgeMs) return null;
      return e;
    }
    var magPromise = cfg.magUrl
      ? fetchJson(cfg.magUrl)
          .then(function (j) {
            var e = freshEntry(j, 60 * 60 * 1000);
            bz = e ? pick(e, ['bz_gsm']) : null;
          })
          .catch(function () {})
      : Promise.resolve();
    var windPromise = cfg.windUrl
      ? fetchJson(cfg.windUrl)
          .then(function (j) {
            var e = freshEntry(j, 60 * 60 * 1000);
            wind = e ? pick(e, ['proton_speed', 'speed']) : null;
          })
          .catch(function () {})
      : Promise.resolve();

    Promise.all([kpPromise, magPromise, windPromise]).then(function (res) {
      renderStatus(res[0], bz, wind);
      if (page === 'aurora' || page === 'solar') renderKpChart(res[0]);
    });

    if (page === 'solar') {
      fetchJson(cfg.xraysUrl).then(function (j) {
        var rows = (Array.isArray(j) ? j : []).filter(function (e) {
          return String(e.energy || '').indexOf('0.05-0.4') !== -1;
        });
        setText('xray-class', xrayClass(pick(lastOf(rows),
          ['observed_flux', 'obs_flux', 'flux'])));
      }).catch(function () { setText('xray-class', '\u2014'); });

      fetchJson(cfg.fluxUrl).then(function (j) {
        var f = pick(lastOf(j), ['Flux', 'flux']);
        setText('f107', f === null ? '\u2014' : String(Math.round(f)) + ' sfu');
      }).catch(function () { setText('f107', '\u2014'); });

      fetchJson(cfg.regionsUrl).then(function (j) {
        var tbody = document.getElementById('regions-tbody');
        if (!tbody) return;
        var rows = (Array.isArray(j) ? j : []).filter(function (r) {
          return String(r.status || '').toLowerCase() !== 'd';
        });
        var latest = rows.reduce(function (m, r) {
          return String(r.observed_date || '') > m ? String(r.observed_date) : m;
        }, '');
        if (latest) {
          rows = rows.filter(function (r) { return r.observed_date === latest; });
        }
        tbody.innerHTML = '';
        rows.forEach(function (r) {
          var tr = document.createElement('tr');
          [r.region, r.location, r.area, r.mag_class, r.c_xray_events,
           r.m_xray_events, r.x_xray_events, r.status].forEach(function (v) {
            var td = document.createElement('td');
            td.textContent = (v === undefined || v === null || v === '') ? '\u2014' : v;
            tr.appendChild(td);
          });
          tbody.appendChild(tr);
        });
        if (!tbody.children.length) {
          tbody.innerHTML = '<tr><td colspan="8" class="text-muted">' +
            'No active regions reported.</td></tr>';
        }
      }).catch(function () {
        var tbody = document.getElementById('regions-tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="text-muted">' +
          'Region data unavailable.</td></tr>';
      });
    }
  }

  function refreshSnapshot() {
    var img = document.getElementById('snapshot-img');
    if (!img || !cfg.snapshotUrl) return;
    var sep = cfg.snapshotUrl.indexOf('?') === -1 ? '?' : '&';
    var bust = cfg.snapshotUrl + sep + 't=' + Date.now();
    var probe = new Image();
    probe.onload = function () {
      img.src = bust;
      fetch(cfg.snapshotUrl, { method: 'HEAD', cache: 'no-store' })
        .then(function (r) {
          var lm = r.headers.get('Last-Modified');
          if (lm) {
            var ageMin = Math.max(0,
              Math.round((Date.now() - new Date(lm).getTime()) / 60000));
            setText('snapshot-age', 'updated ' + ageMin + ' min ago');
          }
        }).catch(function () {});
    };
    probe.src = bust;
  }

  fetchSpaceWeather();
  setInterval(fetchSpaceWeather,
    Math.max(30, Number(cfg.noaaRefreshSeconds) || 120) * 1000);
  if (cfg.snapshotRefreshSeconds && cfg.snapshotUrl) {
    setInterval(refreshSnapshot, Math.max(10, cfg.snapshotRefreshSeconds) * 1000);
  }
})();
