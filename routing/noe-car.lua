-- Simulator profile: base speeds, not live traffic or emergency-driving advice.
-- Extend the car profile shipped with the selected OSRM image.
package.path = '/opt/?.lua;' .. package.path
local car = dofile('/opt/car.lua')
local original_setup = car.setup
local original_way = car.process_way
car.setup = function()
  local p = original_setup()
  local speeds = p.speeds.highway or p.speeds
  speeds.motorway = 130
  speeds.trunk = 100
  speeds.primary = 50
  speeds.secondary = 50
  speeds.tertiary = 50
  speeds.unclassified = 50
  speeds.residential = 50
  -- Ramps, service roads, surfaces, turn/access restrictions stay in car.lua.
  p.speed_reduction = 1.0
  p.maxspeed_table_default.urban = 50
  p.maxspeed_table_default.rural = 100
  p.maxspeed_table_default.trunk = 100
  p.maxspeed_table_default.motorway = 130
  p.maxspeed_table['at:urban'] = 50
  p.maxspeed_table['at:rural'] = 100
  p.maxspeed_table['at:trunk'] = 100
  p.maxspeed_table['at:motorway'] = 130
  return p
end
car.process_way = function(profile, way, result, relations)
  original_way(profile, way, result, relations)
  local highway = way:get_value_by_key('highway') or ''
  local ref = way:get_value_by_key('ref') or ''
  -- Austrian S-roads can be mapped as highway=motorway as well as trunk.
  local expressway = ref:match('^S%s*%d') or ref:match(';%s*S%s*%d')
  local cap = highway == 'motorway' and (expressway and 100 or 130)
           or highway == 'trunk' and 100 or nil
  if cap then
    for _, direction in ipairs({'forward', 'backward'}) do
      local speed_key, rate_key = direction .. '_speed', direction .. '_rate'
      local speed = result[speed_key]
      if speed and speed > cap then
        if result[rate_key] and result[rate_key] > 0 then
          result[rate_key] = result[rate_key] * cap / speed
        end
        result[speed_key] = cap
      end
    end
  end
end
return car
