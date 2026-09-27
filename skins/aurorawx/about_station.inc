#encoding UTF-8
## +-------------------------------------------------------------------------+
## |    about_station.inc    "About this station" table                      |
## |    Adapted from the WeeWX Seasons skin (about.inc).                     |
## +-------------------------------------------------------------------------+

#set global $t = $Extras.Translations[$Extras.language]
#try
<div class="col-12 col-lg-6 mb-4">
  <div class="card">
    <div class="card-body">
      <h5 class="card-title">$t.about_station</h5>
      <div class="table-responsive">
        <table class="table table-sm mb-0">
          <tbody>
            <tr><td>$t.hardware</td><td class="text-right">$station.hardware</td></tr>
            <tr><td>$t.latitude</td><td class="text-right">$station.latitude[0]&deg; $station.latitude[1]' $station.latitude[2]</td></tr>
            <tr><td>$t.longitude</td><td class="text-right">$station.longitude[0]&deg; $station.longitude[1]' $station.longitude[2]</td></tr>
            <tr><td>$t.altitude</td><td class="text-right">$station.altitude</td></tr>
            <tr><td>$t.server_uptime</td><td class="text-right">$station.os_uptime.long_form</td></tr>
            <tr><td>$t.weewx_uptime</td><td class="text-right">$station.uptime.long_form</td></tr>
            <tr><td>$t.weewx_version</td><td class="text-right">$station.version</td></tr>
            <tr><td>$t.skin</td><td class="text-right">$SKIN_NAME $SKIN_VERSION</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
#except
#pass
#end try
