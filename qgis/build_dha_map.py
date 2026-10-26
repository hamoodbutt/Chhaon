import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (
    QgsApplication, QgsProject, QgsRasterLayer, QgsVectorLayer, QgsRasterShader, QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer, QgsStyle, QgsFillSymbol, QgsSingleSymbolRenderer,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend, QgsLayoutItemScaleBar,
    QgsLayoutItemPicture, QgsLayoutPoint, QgsLayoutSize, QgsLayoutExporter, QgsLegendStyle,
    QgsRectangle, QgsLayoutItemPage, Qgis, QgsMapLayerLegendUtils, QgsCoordinateReferenceSystem,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import Qt

d = os.path.abspath(sys.argv[1]); P = "DHA_2021_2025_M5-6"
app = QgsApplication([], False); app.initQgis()
p = QgsProject.instance(); p.clear()
p.setCrs(QgsCoordinateReferenceSystem("EPSG:32643"))
p.setFileName(os.path.join(d, "Chhaon DHA Map.qgz"))
p.writeEntryBool("Paths", "/Absolute", False)

lst = QgsRasterLayer(os.path.join(d, f"{P}_LST_NDVI_NDBI.tif"), "Land surface temperature (°C)")
ndvi = QgsRasterLayer(os.path.join(d, f"{P}_LST_NDVI_NDBI.tif"), "Vegetation index (NDVI)")
blocks = QgsVectorLayer(os.path.join(d, f"{P}_all_blocks.geojson"), "All 250 m blocks (stats)", "ogr")
top = QgsVectorLayer(os.path.join(d, f"{P}_top10_residential.shp"), "Top 10 hottest residential blocks", "ogr")
bnd = QgsVectorLayer(os.path.join(d, f"{P}_boundary.shp"), "Study area", "ogr")
for l in (lst, ndvi, blocks, top, bnd):
    assert l.isValid(), l.name()

ramp = QgsStyle.defaultStyle().colorRamp("Spectral"); ramp.invert()
LO, HI = 40, 50
crs_ = QgsColorRampShader(LO, HI, ramp, Qgis.ShaderInterpolationMethod.Linear, Qgis.ShaderClassificationMethod.Continuous)
crs_.setColorRampItemList([QgsColorRampShader.ColorRampItem(LO + i * (HI - LO) / 8, ramp.color(i / 8), f"{LO + i*(HI-LO)/8:g}") for i in range(9)])
sh = QgsRasterShader(LO, HI); sh.setRasterShaderFunction(crs_)
r = QgsSingleBandPseudoColorRenderer(lst.dataProvider(), 1, sh); r.setClassificationMin(LO); r.setClassificationMax(HI)
lst.setRenderer(r)

g = QgsStyle.defaultStyle().colorRamp("BrBG") or QgsStyle.defaultStyle().colorRamp("Greens")
c2 = QgsColorRampShader(0, 0.5, g, Qgis.ShaderInterpolationMethod.Linear, Qgis.ShaderClassificationMethod.Continuous)
c2.setColorRampItemList([QgsColorRampShader.ColorRampItem(i * 0.0625, g.color(i / 8), f"{i*0.0625:.2f}") for i in range(9)])
sh2 = QgsRasterShader(0, 0.5); sh2.setRasterShaderFunction(c2)
r2 = QgsSingleBandPseudoColorRenderer(ndvi.dataProvider(), 2, sh2); r2.setClassificationMin(0); r2.setClassificationMax(0.5)
ndvi.setRenderer(r2)

blocks.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
    {"style": "no", "outline_color": "80,80,80,90", "outline_width": "0.1"})))
bnd.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
    {"style": "no", "outline_color": "30,30,30,255", "outline_width": "0.5", "outline_style": "dash"})))
top.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(
    {"style": "no", "outline_color": "220,0,0,255", "outline_width": "0.7", "joinstyle": "miter"})))
s = QgsPalLayerSettings(); s.isExpression = True; s.fieldName = 'to_string(to_int("rank"))'
s.placement = Qgis.LabelPlacement.AroundPoint; s.dist = 0.4
s.placementSettings().setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapIfRequired)
tf = QgsTextFormat(); f = QFont("DejaVu Sans"); f.setBold(True); tf.setFont(f); tf.setSize(8); tf.setColor(QColor("white"))
b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(0.7); b.setColor(QColor(150, 0, 0)); tf.setBuffer(b); s.setFormat(tf)
top.setLabeling(QgsVectorLayerSimpleLabeling(s)); top.setLabelsEnabled(True)

for l in (lst, ndvi, blocks, bnd, top):
    p.addMapLayer(l, False)
root = p.layerTreeRoot()
for l in (top, bnd, blocks, lst, ndvi):
    root.addLayer(l)
root.findLayer(ndvi.id()).setItemVisibilityChecked(False)
root.findLayer(blocks.id()).setItemVisibilityChecked(False)

lay = QgsPrintLayout(p); lay.initializeDefaults(); lay.setName("Chhaon DHA Priority Map")
lay.pageCollection().page(0).setPageSize("A4", QgsLayoutItemPage.Orientation.Landscape)
MM = Qgis.LayoutUnit.Millimeters
INK, MUTED, ACCENT = QColor(25, 25, 25), QColor(90, 90, 90), QColor(200, 30, 30)

def label(text, x, y, w, h, size, bold=False, color=INK):
    it = QgsLayoutItemLabel(lay); it.setText(text)
    t = QgsTextFormat(); fn = QFont("DejaVu Sans"); fn.setBold(bold); t.setFont(fn); t.setSize(size); t.setColor(color)
    it.setTextFormat(t); it.attemptMove(QgsLayoutPoint(x, y, MM)); it.attemptResize(QgsLayoutSize(w, h, MM))
    lay.addLayoutItem(it); return it

def html(text, x, y, w, h, size=7.5):
    it = QgsLayoutItemLabel(lay); it.setMode(QgsLayoutItemLabel.Mode.ModeHtml)
    it.setText(f"<div style='font-family:DejaVu Sans;font-size:{size}pt;color:#333;line-height:1.3'>{text}</div>")
    it.attemptMove(QgsLayoutPoint(x, y, MM)); it.attemptResize(QgsLayoutSize(w, h, MM)); lay.addLayoutItem(it); return it

label("CHHAON", 10, 7, 180, 12, 24, bold=True, color=ACCENT)
label("Hottest residential blocks in DHA & Lahore Cantonment", 10, 19, 220, 9, 15, bold=True)
label("Landsat 8/9 land surface temperature composite · May–June, 2021–2025 · 250 m blocks", 10, 28, 240, 7, 9.5, color=MUTED)

MAP_W = 205; ext = lst.extent(); MAP_H = round(MAP_W * ext.height() / ext.width(), 1)
mp = QgsLayoutItemMap(lay); mp.setId("Main map")
mp.attemptMove(QgsLayoutPoint(10, 37, MM)); mp.attemptResize(QgsLayoutSize(MAP_W, MAP_H, MM))
mp.setFrameEnabled(True); mp.setFrameStrokeColor(QColor(60, 60, 60))
mp.setCrs(lst.crs()); mp.setLayers([top, bnd, lst]); mp.setKeepLayerSet(True)
lay.addLayoutItem(mp); mp.zoomToExtent(ext)

svg = next((os.path.join(x, "arrows", "NorthArrow_02.svg") for x in QgsApplication.svgPaths()
            if os.path.exists(os.path.join(x, "arrows", "NorthArrow_02.svg"))), None)
if svg:
    na = QgsLayoutItemPicture(lay); na.setPicturePath(svg); na.setLinkedMap(mp)
    na.setNorthMode(QgsLayoutItemPicture.NorthMode.GridNorth)
    na.attemptMove(QgsLayoutPoint(10 + MAP_W - 13, 39, MM)); na.attemptResize(QgsLayoutSize(10, 13, MM))
    na.setBackgroundEnabled(True); na.setBackgroundColor(QColor(255, 255, 255, 200)); lay.addLayoutItem(na)

sb = QgsLayoutItemScaleBar(lay); sb.setStyle("Single Box"); sb.setLinkedMap(mp)
sb.setUnits(Qgis.DistanceUnit.Kilometers); sb.setUnitLabel("km")
sb.setUnitsPerSegment(1); sb.setNumberOfSegments(3); sb.setNumberOfSegmentsLeft(0)
sb.setSegmentSizeMode(Qgis.ScaleBarSegmentSizeMode.Fixed); sb.setHeight(1.8)
sb.setBackgroundEnabled(True); sb.setBackgroundColor(QColor(255, 255, 255, 220))
t = QgsTextFormat(); t.setFont(QFont("DejaVu Sans")); t.setSize(7); sb.setTextFormat(t)
sb.attemptMove(QgsLayoutPoint(12, 37 + MAP_H - 11, MM)); lay.addLayoutItem(sb); sb.update()

COLX = 10 + MAP_W + 7; COLW = 287 - COLX
lg = QgsLayoutItemLegend(lay); lg.setLinkedMap(mp); lg.setTitle("Legend")
try:
    lg.setSyncMode(Qgis.LegendSyncMode.Manual)
except Exception:
    lg.setAutoUpdateModel(False)
lr = lg.model().rootGroup(); lr.removeAllChildren()
for l in (lst, top, bnd): lr.addLayer(l)
def lfmt(style, size, bold):
    t = QgsTextFormat(); fn = QFont("DejaVu Sans"); fn.setBold(bold); t.setFont(fn); t.setSize(size)
    lg.rstyle(style).setTextFormat(t)
lfmt(QgsLegendStyle.Style.Title, 11, True); lfmt(QgsLegendStyle.Style.Subgroup, 8.5, True); lfmt(QgsLegendStyle.Style.SymbolLabel, 8, False)
n = lr.findLayer(lst.id()); nodes = lg.model().layerLegendNodes(n)
QgsMapLayerLegendUtils.setLegendNodeOrder(n, [i for i, x in enumerate(nodes) if "Band" not in (x.data(Qt.ItemDataRole.DisplayRole) or "")])
lg.model().refreshLayerLegend(n)
lr.findLayer(top.id()).setName("Top 10 hottest residential\nblocks (1 = hottest)")
lr.findLayer(bnd.id()).setName("Study area")
lg.attemptMove(QgsLayoutPoint(COLX, 37, MM)); lay.addLayoutItem(lg); lg.adjustBoxSize()

areas = (
    "<b>Four hot areas</b><br>The 10 blocks cluster into 4 groups:<br><br>"
    "<b>A</b> · Charr / Fort Villa<br>&nbsp;&nbsp;&nbsp;blocks 1, 3, 10 · 47.2–47.9 °C<br>"
    "<b>B</b> · Cavalry Ground<br>&nbsp;&nbsp;&nbsp;blocks 5, 6, 8 · 47.2 °C, least vegetation<br>"
    "<b>C</b> · Malakpur<br>&nbsp;&nbsp;&nbsp;blocks 2, 7 · 47.2–47.3 °C<br>"
    "<b>D</b> · DHA Phase 7<br>&nbsp;&nbsp;&nbsp;blocks 4, 9 · 47.2 °C<br><br>"
    "<i>Place names: OpenStreetMap</i>"
)
html(areas, COLX, 90, COLW, 60, 8)
notes = (
    "<b>Method.</b> Landsat 8/9 Collection 2 Level-2 scenes (May–June 2021–2025), cloud-masked, median composite in "
    "Google Earth Engine. The study area was split into 250 m × 250 m blocks; blocks were kept only if ≥40% of their area is "
    "residential buildings and ≤20% non-residential (GHSL built-up characteristics, 2018). The 10 hottest by mean LST are outlined.<br>"
    "<b>Finding.</b> Across 1,900 blocks, greener blocks ran cooler: the greenest quarter averaged 43.7 °C vs 46.6 °C for the least green.<br>"
    "<b>Note.</b> Land <i>surface</i> temperature, not air temperature. The rectangular study area covers DHA and "
    "neighbouring parts of Lahore Cantonment. Sites still need checking on the ground.<br>"
    "Chhaon · Hamood, 2026"
)
html(notes, 10, 37 + MAP_H + 3, 277, 30, 7.2)

p.layoutManager().addLayout(lay)
ex = QgsLayoutExporter(lay)
pdf = QgsLayoutExporter.PdfExportSettings(); pdf.dpi = 300
print("pdf", ex.exportToPdf(os.path.join(d, "Chhaon_DHA_Priority_Map.pdf"), pdf))
img = QgsLayoutExporter.ImageExportSettings(); img.dpi = 200
print("png", ex.exportToImage(os.path.join(d, "Chhaon_DHA_Priority_Map.png"), img))
print("saved", p.write())
app.exitQgis()
