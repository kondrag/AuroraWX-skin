#encoding UTF-8
## +-------------------------------------------------------------------------+
## |    js.inc                   Common javascript code for all templates    |
## +-------------------------------------------------------------------------+

## jQuery
<script type="text/javascript" src="js/jquery.min.js"></script>
## Bootstrap tooltips / JS
<script type="text/javascript" src="js/popper.min.js"></script>
<script type="text/javascript" src="js/bootstrap.min.js"></script>
## MDB core JavaScript
<script type="text/javascript" src="js/mdb.min.js"></script>
## Vendor JS
#if $Extras.language == "en"
<script src="js/vendor/moment.min.js"></script>
#else
<script src="js/vendor/moment-with-locales.min.js"></script>
<script type="text/javascript">moment.locale('$Extras.language')</script>
#end if
<script src="js/vendor/apexcharts/apexcharts.min.js"></script>
## NeoWX Material App
<script type="text/javascript" src="js/app.js"></script>

## Global apexcharts config
<script type="text/javascript">
    var config_mode = '${Extras.Appearance.mode}';
    var theme_mode = 'light';
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        theme_mode = 'dark';
    }
    // Override mode by config
    if(config_mode != "auto") {
        theme_mode = config_mode;
    }

    window.Apex = {
        theme: {
            mode: theme_mode,
            palette: '$Extras.Charts.palette'
        },
        dataLabels: {
            enabled: false
        },
        stroke: {
            curve: '$Extras.Charts.stroke_curve',
            width: $Extras.Charts.stroke_width
        },
        markers: {
            size: $Extras.Charts.markers_size,
        },
        chart: {
            height: $Extras.Charts.height,
            stacked: false,
            zoom: {
                type: 'x',
                enabled: true,
                autoScaleYaxis: true
            },
            toolbar: {
                autoSelected: 'zoom',
                export: {
                    csv: {
                        headerCategory: 'DateTime',
                        dateFormatter(timestamp) {
                            return moment.unix(timestamp).toISOString()
                        }
                    }
                }
            },
            locales: [
                #include raw "js/vendor/apexcharts/locales/" + $Extras.language + ".json"
            ],
            defaultLocale: '$Extras.language',
            animations: {
                enabled: false
            },
        },
    }
</script>

## Period selector dropdowns (day/week/month pages)
## Populated client-side from periods.js (generated every report run), which
## the pages carrying a selector load themselves. The <select> declares
## data-periods (AuroraPeriods key), data-prefix (filename prefix),
## data-parse (moment parse format) and data-fmt (moment display format).
## On archive pages the option matching the current page URL is preselected.
<script type="text/javascript">
    (function () {
        var selects = document.querySelectorAll('select[data-periods]');
        if (!selects.length) return;
        var current = location.pathname.split('/').pop();
        for (var s = 0; s < selects.length; s++) {
            var sel = selects[s];
            var list = (window.AuroraPeriods || {})[sel.getAttribute('data-periods')] || [];
            var prefix = sel.getAttribute('data-prefix');
            var parse = sel.getAttribute('data-parse');
            var fmt = sel.getAttribute('data-fmt');
            for (var i = list.length - 1; i >= 0; i--) {
                var val = list[i];
                var opt = document.createElement('option');
                opt.value = prefix + val + '.html';
                opt.text = moment(val, parse).format(fmt);
                if (opt.value === current) opt.selected = true;
                sel.appendChild(opt);
            }
        }
    })();
</script>