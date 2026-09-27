#encoding UTF-8
## +-------------------------------------------------------------------------+
## |    sensors_status.inc   Sensor Status table for the telemetry page      |
## |    Adapted from the WeeWX Seasons skin (sensors.inc).                   |
## +-------------------------------------------------------------------------+

#import time
#from weeutil.weeutil import option_as_list
#set global $t = $Extras.Translations[$Extras.language]
#set $now = $time.time()
#set $recent = $span($day_delta=30, boundary='midnight')
#set $conn_fields = $option_as_list($Extras.SensorStatus.sensor_connections)
#set $batt_fields = $option_as_list($Extras.SensorStatus.sensor_batteries)
#set $volt_fields = $option_as_list($Extras.SensorStatus.sensor_voltages)

#def get_battery_status($raw)
  #if $raw is None
    <span class="text-muted">$t.status_unknown</span>
  #elif $raw == 1
    <span class="text-warning">$t.status_low</span>
  #else
    <span class="text-success">$t.status_ok</span>
  #end if
#end def

#def get_time_delta($last_ts, $now)
  #if not $last_ts
    $t.never
  #else
    #set $delta = int($now - $last_ts)
    #if $delta < 60
      &nbsp;
    #elif $delta < 3600
      ${int($delta / 60)} $t.minutes_ago
    #elif $delta < 86400
      ${int($delta / 3600)} $t.hours_ago
    #else
      ${int($delta / 86400)} $t.days_ago
    #end if
  #end if
#end def

#try
#set $have_conn = 0
#set $have_batt = 0
#set $have_volt = 0
#for $x in $conn_fields
  #if $getattr($recent, $x).has_data
    #set $have_conn = 1
  #end if
#end for
#for $x in $batt_fields
  #if $getattr($recent, $x).has_data
    #set $have_batt = 1
  #end if
#end for
#for $x in $volt_fields
  #if $getattr($recent, $x).has_data
    #set $have_volt = 1
  #end if
#end for
#if $have_conn or $have_batt or $have_volt
<div class="col-12 col-lg-6 mb-4">
  <div class="card">
    <div class="card-body">
      <h5 class="card-title">$t.sensor_status</h5>
      <div class="table-responsive">
        <table class="table table-sm mb-0">
          <tbody>
            #if $have_conn
            <tr><th colspan="3">$t.connectivity</th></tr>
            #for $x in $conn_fields
              #if $getattr($recent, $x).has_data
              <tr>
                <td>$getVar('obs.label.' + $x)</td>
                <td class="text-right">$getVar('current.' + $x)</td>
                <td class="text-right text-muted">$get_time_delta($getattr($recent, $x).lasttime.raw, $now)</td>
              </tr>
              #end if
            #end for
            #end if
            #if $have_batt
            <tr><th colspan="3">$t.battery_status</th></tr>
            #for $x in $batt_fields
              #if $getattr($recent, $x).has_data
              <tr>
                <td>$getVar('obs.label.' + $x)</td>
                <td class="text-right">$get_battery_status($getVar('current.%s.raw' % $x))</td>
                <td class="text-right text-muted">$get_time_delta($getattr($recent, $x).lasttime.raw, $now)</td>
              </tr>
              #end if
            #end for
            #end if
            #if $have_volt
            <tr><th colspan="3">$t.voltage</th></tr>
            #for $x in $volt_fields
              #if $getattr($recent, $x).has_data
              <tr>
                <td>$getVar('obs.label.' + $x)</td>
                <td class="text-right">$getVar('current.' + $x)</td>
                <td class="text-right text-muted">$get_time_delta($getattr($recent, $x).lasttime.raw, $now)</td>
              </tr>
              #end if
            #end for
            #end if
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
#end if
#except
#pass
#end try
