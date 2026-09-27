/*
 * Period picker wiring: binds the vendored flatpickr calendar to the
 * Historical pages' period inputs. flatpickr.min.js/css are vendored
 * (MIT, no dependencies); periods.js provides window.AuroraPeriods:
 *   { days: ["YYYY-MM-DD", ...], weeks: [Mondays, ...], months: ["YYYY-MM", ...] }
 * The input carries data-periods (days|weeks|months|years) and
 * data-prefix (e.g. "day/day-"); a selection navigates to
 * prefix + value + ".html". Weeks are named by their Monday, so a click
 * on any day snaps to that week's Monday; years are derived from the
 * distinct years in the days list.
 */
(function () {
    'use strict';

    function boot() {
        var periods = window.AuroraPeriods || {};
        if (!window.flatpickr || !periods.days || !periods.days.length) {
            return;
        }

        function pad2(n) { return (n < 10 ? '0' : '') + n; }

        function iso(d) {
            return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' +
                pad2(d.getDate());
        }

        function expandWeeks(mondays) {
            // Each archived week contributes all 7 of its dates.
            var out = [];
            mondays.forEach(function (monday) {
                var base = new Date(monday + 'T12:00:00');
                for (var i = 0; i < 7; i++) {
                    var d = new Date(base.getTime());
                    d.setDate(base.getDate() + i);
                    out.push(iso(d));
                }
            });
            return out;
        }

        var CONFIG = {
            days: function () {
                return {
                    enable: periods.days,
                    altFormat: 'M j, Y',
                    onChange: function (dates, dateStr) {
                        if (dates.length) {
                            window.location.href = 'day/day-' + dateStr + '.html';
                        }
                    }
                };
            },
            weeks: function () {
                return {
                    enable: expandWeeks(periods.weeks || []),
                    altFormat: 'M j, Y',
                    onChange: function (dates) {
                        if (!dates.length) {
                            return;
                        }
                        var d = dates[dates.length - 1];
                        var monday = new Date(d.getTime());
                        monday.setDate(d.getDate() - ((d.getDay() + 6) % 7));
                        window.location.href = 'week/week-' + iso(monday) + '.html';
                    }
                };
            },
            months: function () {
                var firsts = (periods.months || []).map(function (m) {
                    return m + '-01';
                });
                return {
                    enable: firsts,
                    altFormat: 'F Y',
                    onChange: function (dates, dateStr) {
                        if (dates.length) {
                            window.location.href = 'month/month-' +
                                dateStr.slice(0, 7) + '.html';
                        }
                    }
                };
            },
            years: function () {
                var seen = {};
                var firsts = [];
                (periods.days || []).forEach(function (day) {
                    var year = day.slice(0, 4);
                    if (!seen[year]) {
                        seen[year] = true;
                        firsts.push(year + '-01-01');
                    }
                });
                return {
                    enable: firsts,
                    altFormat: 'Y',
                    onChange: function (dates, dateStr) {
                        if (dates.length) {
                            window.location.href = 'year/year-' +
                                dateStr.slice(0, 4) + '.html';
                        }
                    }
                };
            }
        };

        document.querySelectorAll('input[data-periods]').forEach(function (input) {
            var build = CONFIG[input.getAttribute('data-periods')];
            if (!build) {
                return;
            }
            var opts = build();
            window.flatpickr(input, {
                enable: opts.enable,
                dateFormat: 'Y-m-d',
                altInput: true,
                altFormat: opts.altFormat,
                disableMobile: true,
                onChange: opts.onChange
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
