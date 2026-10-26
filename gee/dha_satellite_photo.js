var aoi = ee.Geometry.Rectangle([74.36, 31.44, 74.50, 31.52]);

var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(aoi)
  .filterDate('2025-10-01', '2026-03-31')
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
  .median()
  .clip(aoi);

var photo = s2.visualize({bands: ['B4', 'B3', 'B2'], min: 100, max: 2200, gamma: 1.2});

Map.centerObject(aoi, 13);
Map.addLayer(photo, {}, 'Sentinel-2 true colour');

Export.image.toDrive({
  image: photo,
  description: 'DHA_Sentinel2_true_colour',
  folder: 'GEE_Chhaon_DHA',
  region: aoi,
  scale: 10,
  crs: 'EPSG:32643',
  maxPixels: 1e10
});
