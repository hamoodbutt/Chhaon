var START      = '2021-01-01';
var END        = '2025-12-31';
var BLOCK      = 250;
var TOP_N      = 10;
var MIN_RES    = 0.4;
var MAX_NONRES = 0.2;
var FOLDER     = 'GEE_Chhaon_DHA';
var PREFIX     = 'DHA_2021_2025_M5-6';

var aoi = (typeof dha !== 'undefined') ? dha : ee.Geometry.Rectangle([74.36, 31.44, 74.50, 31.52]);
Map.centerObject(aoi, 13);

function prep(img) {
  var qa = img.select('QA_PIXEL');
  var clear = qa.bitwiseAnd(1 << 1).eq(0)
      .and(qa.bitwiseAnd(1 << 2).eq(0))
      .and(qa.bitwiseAnd(1 << 3).eq(0))
      .and(qa.bitwiseAnd(1 << 4).eq(0));
  var sr   = img.select('SR_B.').multiply(0.0000275).add(-0.2);
  var lst  = img.select('ST_B10').multiply(0.00341802).add(149.0)
                .subtract(273.15).rename('LST');
  var ndvi = sr.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI');
  var ndbi = sr.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI');
  return lst.addBands(ndvi).addBands(ndbi).updateMask(clear);
}

var landsat = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
  .filterBounds(aoi)
  .filterDate(START, END)
  .filter(ee.Filter.calendarRange(5, 6, 'month'))
  .map(prep);
print('Landsat scenes used', landsat.size());

var comp = landsat.median().clip(aoi);

var ghs    = ee.Image('JRC/GHSL/P2023A/GHS_BUILT_C/2018').select('built_characteristics').unmask(0);
var res    = ghs.gte(11).and(ghs.lte(15)).rename('res').clip(aoi);
var nonres = ghs.gte(21).and(ghs.lte(25)).rename('nonres').clip(aoi);

var grid  = aoi.coveringGrid(ee.Projection('EPSG:32643').atScale(BLOCK));
var stack = comp.addBands(res).addBands(nonres);
var stats = stack.reduceRegions({
  collection: grid,
  reducer: ee.Reducer.mean().combine(ee.Reducer.count(), '', true),
  scale: 30,
  crs: 'EPSG:32643'
});

var fullBlockPixels = (BLOCK * BLOCK) / (30 * 30);
var candidates = stats
  .filter(ee.Filter.gte('LST_count', fullBlockPixels * 0.6))
  .filter(ee.Filter.gte('res_mean', MIN_RES))
  .filter(ee.Filter.lte('nonres_mean', MAX_NONRES));

print('Blocks in area', grid.size());
print('Residential blocks that qualify', candidates.size());

var topList = candidates.sort('LST_mean', false).limit(TOP_N).toList(TOP_N);
var ranked = ee.FeatureCollection(
  ee.List.sequence(0, topList.size().subtract(1)).map(function (i) {
    var f = ee.Feature(topList.get(i));
    var c = f.geometry().centroid(1).transform('EPSG:4326', 1).coordinates();
    return ee.Feature(f.geometry(), {
      rank:      ee.Number(i).add(1),
      LST_mean:  f.get('LST_mean'),
      NDVI_mean: f.get('NDVI_mean'),
      NDBI_mean: f.get('NDBI_mean'),
      res_frac:  f.get('res_mean'),
      lat:       c.get(1),
      lon:       c.get(0)
    });
  })
);
print('Top ' + TOP_N + ' hottest residential blocks', ranked);

Map.addLayer(comp.select('LST'), {min: 38, max: 50,
  palette: ['2b83ba', 'abdda4', 'ffffbf', 'fdae61', 'd7191c']}, 'LST (°C)');
Map.addLayer(comp.select('NDVI'), {min: 0, max: 0.6,
  palette: ['bf9b6b', 'f2eab4', '7cb342', '1b5e20']}, 'NDVI', false);
Map.addLayer(res.selfMask(), {palette: ['ffffff']}, 'Residential buildings', false);
Map.addLayer(ee.Image().paint(ranked, 0, 2), {palette: ['ff0000']}, 'Top ' + TOP_N + ' blocks');

Export.image.toDrive({
  image: comp.toFloat(), description: PREFIX + '_LST_NDVI_NDBI', folder: FOLDER,
  region: aoi, scale: 30, crs: 'EPSG:32643', maxPixels: 1e10
});
Export.table.toDrive({
  collection: ranked, description: PREFIX + '_top10_residential', folder: FOLDER, fileFormat: 'SHP'
});
Export.table.toDrive({
  collection: stats, description: PREFIX + '_all_blocks', folder: FOLDER, fileFormat: 'GeoJSON'
});
Export.table.toDrive({
  collection: ee.FeatureCollection([ee.Feature(aoi, {name: 'DHA'})]),
  description: PREFIX + '_boundary', folder: FOLDER, fileFormat: 'SHP'
});
