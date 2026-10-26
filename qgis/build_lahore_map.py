"""Fix Chhaon project styling, build the print layout, export PDF + PNG.
Usage: python3.12 build_layout.py <project.qgz> <out_dir>
"""
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from qgis.core import (
    QgsApplication, QgsProject, QgsRasterShader, QgsColorRampShader,
    QgsSingleBandPseudoColorRenderer, QgsStyle, QgsFillSymbol, QgsSingleSymbolRenderer,
    QgsPalLayerSettings, QgsTextFormat, QgsTextBufferSettings, QgsVectorLayerSimpleLabeling,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemLegend,
    QgsLayoutItemScaleBar, QgsLayoutItemPicture, QgsLayoutPoint, QgsLayoutSize,
    QgsUnitTypes, QgsLayoutExporter, QgsLegendStyle, QgsLayerTreeLayer, QgsRectangle,
    QgsLayoutItemPage, QgsLayoutMeasurement, QgsFontUtils, Qgis, QgsMapLayerLegendUtils,
    QgsCoordinateReferenceSystem,
)
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtCore import Qt

proj_path, out_dir = sys.argv[1], sys.argv[2]
app = QgsApplication([], False)
app.initQgis()
p = QgsProject.instance()
assert p.read(proj_path), "could not read project"

def by_name(sub, exclude=None):
    for l in p.mapLayers().values():
        if sub in l.name() and (not exclude or exclude not in l.name()):
            return l
    return None

lst = by_name("LST_NDVI_NDBI", exclude="copy") or by_name("Land surface")
ndvi = by_name("LST_NDVI_NDBI copy") or by_name("Vegetation")
top = by_name("top25") or by_name("Top 25")
allb = by_name("all_blocks")
for nm, l in [("lst", lst), ("ndvi", ndvi), ("top", top)]:
    assert l is not None and l.isValid(), f"{nm} layer missing/invalid (data files not next to project?)"

# ---- 1. LST: band 1, fixed 32-52, continuous blue->red ramp
ramp = QgsStyle.defaultStyle().colorRamp("Spectral"); ramp.invert()
crs_ = QgsColorRampShader(32, 52, ramp, Qgis.ShaderInterpolationMethod.Linear, Qgis.ShaderClassificationMethod.Continuous)
crs_.setColorRampItemList([QgsColorRampShader.ColorRampItem(32 + i * 2.5, ramp.color(i / 8), f"{32 + i*2.5:g}") for i in range(9)])
crs_.setClip(False)
sh = QgsRasterShader(32, 52); sh.setRasterShaderFunction(crs_)
r = QgsSingleBandPseudoColorRenderer(lst.dataProvider(), 1, sh)
r.setClassificationMin(32); r.setClassificationMax(52)
lst.setRenderer(r); lst.setName("Land surface temperature (°C)")

# ---- 2. NDVI copy: rename, keep style, hide
ndvi.setName("Vegetation index (NDVI)")
root = p.layerTreeRoot()
root.findLayer(ndvi.id()).setItemVisibilityChecked(False)
if allb is not None:
    allb.setName("All blocks (table only)")
    root.findLayer(allb.id()).setItemVisibilityChecked(False)

# ---- 3. Top-25: no fill, red outline, rank labels
sym = QgsFillSymbol.createSimple({"style": "no", "outline_color": "220,0,0,255",
                                  "outline_width": "0.6", "outline_width_unit": "MM",
                                  "joinstyle": "miter"})
top.setRenderer(QgsSingleSymbolRenderer(sym)); top.setName("Top 25 hottest blocks")
fields = [f.name() for f in top.fields()]
rank_field = next((f for f in fields if f.lower() == "rank"), None)
if rank_field:
    s = QgsPalLayerSettings(); s.isExpression = True
    inside = "x(centroid($geometry)) BETWEEN 408750 AND 427000 AND y(centroid($geometry)) BETWEEN 3500750 AND 3513750"
    s.fieldName = ("CASE WHEN @map_id = 'Main map' AND " + inside + " THEN '' "
                   "WHEN @map_id = 'Main map' AND to_int(\"rank\") = 1 THEN '1, 2' "
                   "WHEN @map_id = 'Main map' AND to_int(\"rank\") = 2 THEN '' "
                   "ELSE to_string(to_int(\"rank\")) END")
    s.placement = Qgis.LabelPlacement.OverPoint
    s.placementSettings().setOverlapHandling(Qgis.LabelOverlapHandling.AllowOverlapAtNoCost)
    tf = QgsTextFormat(); tf.setFont(QFont("DejaVu Sans")); tf.setSize(6.5)
    f = tf.font(); f.setBold(True); tf.setFont(f); tf.setColor(QColor("white"))
    b = QgsTextBufferSettings(); b.setEnabled(True); b.setSize(0.6); b.setColor(QColor(150, 0, 0))
    tf.setBuffer(b); s.setFormat(tf)
    top.setLabeling(QgsVectorLayerSimpleLabeling(s)); top.setLabelsEnabled(True)

for l in (lst, ndvi, top):
    l.triggerRepaint()

# ---- 4. Layout (A4 landscape)
lm = p.layoutManager()
old = lm.layoutByName("Chhaon Priority Map")
if old: lm.removeLayout(old)
lay = QgsPrintLayout(p); lay.initializeDefaults(); lay.setName("Chhaon Priority Map")
lay.pageCollection().page(0).setPageSize("A4", QgsLayoutItemPage.Orientation.Landscape)
MM = Qgis.LayoutUnit.Millimeters
INK, MUTED, ACCENT = QColor(25, 25, 25), QColor(90, 90, 90), QColor(200, 30, 30)

def label(text, x, y, w, h, size, bold=False, color=INK, wrap=True):
    it = QgsLayoutItemLabel(lay); it.setText(text)
    tf = QgsTextFormat(); fnt = QFont("DejaVu Sans"); fnt.setBold(bold)
    tf.setFont(fnt); tf.setSize(size); tf.setColor(color)
    it.setTextFormat(tf)
    it.attemptMove(QgsLayoutPoint(x, y, MM)); it.attemptResize(QgsLayoutSize(w, h, MM))
    lay.addLayoutItem(it); return it

label("CHHAON", 10, 7, 180, 12, 24, bold=True, color=ACCENT)
label("Lahore Urban Heat & Tree-Planting Priorities", 10, 19, 200, 9, 15, bold=True)
label("Landsat land surface temperature composite · May–June, 2021–2025", 10, 28, 200, 7, 9.5, color=MUTED)

# map
mp = QgsLayoutItemMap(lay)
MAP_H = 165; MAP_W = round(MAP_H * lst.extent().width() / lst.extent().height(), 1)
mp.attemptMove(QgsLayoutPoint(10, 37, MM)); mp.attemptResize(QgsLayoutSize(MAP_W, MAP_H, MM))
mp.setFrameEnabled(True); mp.setFrameStrokeColor(QColor(60, 60, 60))
mp.setBackgroundColor(QColor(245, 245, 245))
mp.setLayers([top, lst]); mp.setKeepLayerSet(True); mp.setId('Main map')
ext = QgsRectangle(lst.extent())
mp.setCrs(lst.crs())
lay.addLayoutItem(mp)
from qgis.core import QgsCoordinateTransform
if mp.crs() != lst.crs():
    ext = QgsCoordinateTransform(lst.crs(), mp.crs(), p).transformBoundingBox(ext)
mp.zoomToExtent(ext)
mp.setScale(mp.scale() * 1.01)

# north arrow (top-right of map)
na = QgsLayoutItemPicture(lay)
svg = next((os.path.join(d, "arrows", "NorthArrow_02.svg") for d in QgsApplication.svgPaths()
            if os.path.exists(os.path.join(d, "arrows", "NorthArrow_02.svg"))), None)
if svg:
    na.setPicturePath(svg); na.setLinkedMap(mp); na.setNorthMode(QgsLayoutItemPicture.NorthMode.GridNorth)
    na.attemptMove(QgsLayoutPoint(10 + MAP_W - 14, 40, MM)); na.attemptResize(QgsLayoutSize(11, 15, MM))
    na.setBackgroundEnabled(True); na.setFrameEnabled(False); na.setBackgroundColor(QColor(255, 255, 255, 200))
    lay.addLayoutItem(na)

# scale bar (bottom-left of map)
sb = QgsLayoutItemScaleBar(lay); sb.setStyle("Single Box"); sb.setLinkedMap(mp)
sb.setUnits(Qgis.DistanceUnit.Kilometers); sb.setUnitLabel("km")
sb.setUnitsPerSegment(2); sb.setNumberOfSegments(3); sb.setNumberOfSegmentsLeft(0)
sb.setSegmentSizeMode(Qgis.ScaleBarSegmentSizeMode.Fixed); sb.setHeight(2)
sb.setBackgroundEnabled(True); sb.setBackgroundColor(QColor(255, 255, 255, 220))
tf = QgsTextFormat(); tf.setFont(QFont("DejaVu Sans")); tf.setSize(7.5); sb.setTextFormat(tf)
sb.attemptMove(QgsLayoutPoint(13, 190, MM))
lay.addLayoutItem(sb); sb.update()

# legend (right column)
lg = QgsLayoutItemLegend(lay); lg.setLinkedMap(mp); lg.setAutoUpdateModel(False)
lg.setTitle("Legend")
lroot = lg.model().rootGroup(); lroot.removeAllChildren()
lroot.addLayer(lst); lroot.addLayer(top)
def lfmt(style, size, bold):
    tf = QgsTextFormat(); f = QFont("DejaVu Sans"); f.setBold(bold); tf.setFont(f); tf.setSize(size)
    lg.rstyle(style).setTextFormat(tf)
lfmt(QgsLegendStyle.Style.Title, 12, True); lfmt(QgsLegendStyle.Style.Subgroup, 9.5, True)
lfmt(QgsLegendStyle.Style.SymbolLabel, 8.5, False)
lst_node = lroot.findLayer(lst.id())
nodes = lg.model().layerLegendNodes(lst_node)
keep = [i for i, n in enumerate(nodes) if "Band" not in (n.data(Qt.ItemDataRole.DisplayRole) or "")]
QgsMapLayerLegendUtils.setLegendNodeOrder(lst_node, keep)
lg.model().refreshLayerLegend(lst_node)
lst_node.setName("Land surface temperature (°C)")
top_node = lroot.findLayer(top.id()); top_node.setName("Top 25 hottest blocks (numbered by rank, 1 = hottest)")
lg.attemptMove(QgsLayoutPoint(10 + MAP_W + 10, 37, MM))
lay.addLayoutItem(lg); lg.adjustBoxSize()

COLX = 10 + MAP_W + 10; COLW = 287 - COLX

# ---- detail inset for the north-west cluster
INSET_RECT = QgsRectangle(408750, 3500250, 427000, 3513150)
label("Detail: north-west hotspot cluster (21 of the 25 blocks)", COLX, 72, COLW, 5, 8.5, bold=True)
im = QgsLayoutItemMap(lay); im.setId("Inset")
im.attemptMove(QgsLayoutPoint(COLX, 78, MM)); im.attemptResize(QgsLayoutSize(COLW, 80, MM))
im.setFrameEnabled(True); im.setFrameStrokeColor(QColor(60, 60, 60))
im.setCrs(lst.crs()); im.setLayers([top, lst]); im.setKeepLayerSet(True)
lay.addLayoutItem(im); im.zoomToExtent(INSET_RECT)
ov = mp.overview(); ov.setLinkedMap(im)
ov.setFrameSymbol(QgsFillSymbol.createSimple({"style": "no", "outline_color": "20,20,20,255",
                                                "outline_width": "0.4", "outline_style": "dash"}))
isb = QgsLayoutItemScaleBar(lay); isb.setStyle("Single Box"); isb.setLinkedMap(im)
isb.setUnits(Qgis.DistanceUnit.Kilometers); isb.setUnitLabel("km")
isb.setUnitsPerSegment(1); isb.setNumberOfSegments(3); isb.setNumberOfSegmentsLeft(0)
isb.setSegmentSizeMode(Qgis.ScaleBarSegmentSizeMode.Fixed); isb.setHeight(1.5)
isb.setBackgroundEnabled(True); isb.setBackgroundColor(QColor(255, 255, 255, 220))
tf = QgsTextFormat(); tf.setFont(QFont("DejaVu Sans")); tf.setSize(6.5); isb.setTextFormat(tf)
isb.attemptMove(QgsLayoutPoint(COLX + COLW - 30, 149, MM)); lay.addLayoutItem(isb); isb.update()

notes = (
    "<b>How to read this map.</b> Colours show mean land surface temperature (LST), May–June 2021–2025: "
    "blue = cooler, red = hotter. Red outlines mark the 25 hottest 500 m grid blocks, numbered by rank. "
    "The dashed box on the main map shows the area of the detail map.<br>"
    "<b>Important.</b> This is land <i>surface</i> temperature, not air temperature. Outlined blocks are candidates "
    "for further investigation; tree-planting suitability (space, access, water, ownership) has not been verified on the ground.<br>"
    "<b>Data &amp; method.</b> Landsat LST, NDVI and NDBI layers (30 m pixels) composited in Google Earth Engine. "
    "The city was divided into 13,926 blocks of 500 m × 500 m (UTM 43N); mean LST, NDVI and NDBI were computed per block. "
    "Outlined blocks have mean LST of 50.5–53.1 °C. Map produced in QGIS.<br>"
    "Chhaon · Hamood, 2026"
)
nl = QgsLayoutItemLabel(lay); nl.setMode(QgsLayoutItemLabel.Mode.ModeHtml); nl.setText(
    f"<div style='font-family:DejaVu Sans;font-size:7pt;color:#333;line-height:1.25'>{notes}</div>")
nl.attemptMove(QgsLayoutPoint(COLX, 161, MM)); nl.attemptResize(QgsLayoutSize(COLW, 42, MM))
lay.addLayoutItem(nl)

lm.addLayout(lay)

# ---- 5. Export
os.makedirs(out_dir, exist_ok=True)
ex = QgsLayoutExporter(lay)
pdf = QgsLayoutExporter.PdfExportSettings(); pdf.dpi = 300; pdf.rasterizeWholeImage = False
r1 = ex.exportToPdf(os.path.join(out_dir, "Chhaon_Lahore_Heat_Priority_Map.pdf"), pdf)
img = QgsLayoutExporter.ImageExportSettings(); img.dpi = 200
r2 = ex.exportToImage(os.path.join(out_dir, "Chhaon_Lahore_Heat_Priority_Map.png"), img)
print("pdf", r1, "png", r2, "rank field", rank_field, "fields", fields, "crs", p.crs().authid(), "scale", round(mp.scale()))

assert p.write(os.path.join(out_dir, "Chhaon_Heat_Map.qgz"))
app.exitQgis()
