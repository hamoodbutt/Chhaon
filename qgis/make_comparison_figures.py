import numpy as np, json, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle
d=np.load('figdata.npz'); rgb=d['rgb']; a=np.where(rgb.sum(2)==0,0,255).astype('uint8'); rgb=np.dstack([rgb,a]); gs=d['gs']; lst=d['lst']; gl=d['gl']; polys=json.load(open('polys.json'))
def ext(gt,shape): return [gt[0], gt[0]+gt[1]*shape[1], gt[3]+gt[5]*shape[0], gt[3]]
E_rgb=ext(gs,rgb.shape); E_lst=ext(gl,lst.shape)
groups={'A':('Charr / Fort Villa',[1,3,10]),'B':('Cavalry Ground',[5,6,8]),'C':('Malakpur',[2,7]),'D':('DHA Phase 7',[4,9])}
P={p['rank']:np.array(p['xy']) for p in polys}
cmap=plt.get_cmap('Spectral_r')
def outlines(ax, lw=1.6, lab=True, fs=8):
    for r,xy in P.items():
        ax.add_patch(Polygon(xy,closed=True,fill=False,ec='#e00000',lw=lw))
        if lab:
            cx,cy=xy[:,0].mean(),xy[:,1].max()
            ax.text(cx,cy+25,str(r),ha='center',va='bottom',fontsize=fs,color='white',weight='bold',
                    bbox=dict(boxstyle='round,pad=0.15',fc='#a00000',ec='none'),clip_on=True)
def setup(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_color('#555'); s.set_linewidth(.6)
def scalebar(ax,x0,y0,km=0.5,fs=7,col='white'):
    ax.add_patch(Rectangle((x0,y0),km*1000,30,fc=col,ec='black',lw=.5))
    ax.text(x0+km*500,y0+60,f'{km:g} km',ha='center',va='bottom',fontsize=fs,color=col,weight='bold')

fig,axes=plt.subplots(4,2,figsize=(8.5,15.5),dpi=170)
H=1100
for i,(k,(name,ranks)) in enumerate(groups.items()):
    pts=np.vstack([P[r] for r in ranks]); cx,cy=pts[:,0].mean(),pts[:,1].mean()
    cx=min(max(cx,E_rgb[0]+H+20),E_rgb[1]-H-20); cy=min(max(cy,E_rgb[2]+H*0.75+20),E_rgb[3]-H*0.75-20)
    for j,ax in enumerate(axes[i]):
        if j==0:
            im=ax.imshow(lst,extent=E_lst,cmap=cmap,vmin=40,vmax=50,interpolation='bilinear')
        else:
            ax.imshow(rgb,extent=E_rgb,interpolation='bilinear')
        outlines(ax)
        ax.set_xlim(cx-H,cx+H); ax.set_ylim(cy-H*0.75,cy+H*0.75); setup(ax)
        scalebar(ax,cx-H+120,cy-H*0.75+110, col='black' if j==0 else 'white')
    temps=f"blocks {', '.join(map(str,ranks))}"
    axes[i][0].set_title(f"{k} · {name}  —  heat",loc='left',fontsize=10,weight='bold')
    axes[i][1].set_title("satellite view",loc='left',fontsize=10,color='#444')
fig.suptitle("Chhaon — what the hottest residential blocks actually look like",x=0.03,ha='left',fontsize=13,weight='bold',y=0.995)
fig.text(0.03,0.972,"Left: Landsat land surface temperature, May–June 2021–2025 (blue 40 °C → red 50 °C).  Right: Sentinel-2 true colour, Oct 2025–Mar 2026.\nRed squares: the 10 hottest 250 m residential blocks, numbered by rank (1 = hottest).",fontsize=7.8,color='#444',va='top')
cax=fig.add_axes([0.62,0.012,0.33,0.008]); cb=fig.colorbar(im,cax=cax,orientation='horizontal'); cb.set_label('Land surface temperature (°C)',fontsize=7.5); cb.ax.tick_params(labelsize=7)
fig.text(0.03,0.006,"Data: USGS Landsat 8/9 · ESA Copernicus Sentinel-2 · place names © OpenStreetMap · Chhaon / Hamood 2026",fontsize=6.5,color='#666')
plt.subplots_adjust(left=0.03,right=0.97,top=0.945,bottom=0.035,hspace=0.18,wspace=0.04)
plt.savefig('Chhaon_DHA_Heat_vs_Satellite.png'); plt.close()

fig,axes=plt.subplots(1,2,figsize=(14,5.4),dpi=170)
im=axes[0].imshow(lst,extent=E_lst,cmap=cmap,vmin=40,vmax=50,interpolation='bilinear')
axes[1].imshow(rgb,extent=E_rgb,interpolation='bilinear')
for ax in axes:
    outlines(ax,lw=1.3,fs=7); ax.set_xlim(E_rgb[0],E_rgb[1]); ax.set_ylim(E_rgb[2],E_rgb[3]); setup(ax)
    for k,(name,ranks) in groups.items():
        pts=np.vstack([P[r] for r in ranks]);
        ax.text(pts[:,0].min()-120,pts[:,1].mean(),k,ha='right',va='center',fontsize=12,weight='bold',color='white',
                bbox=dict(boxstyle='circle,pad=0.25',fc='#222',ec='white',lw=.8))
scalebar(axes[0],E_lst[0]+500,E_lst[2]+500,km=2,col='black',fs=8); scalebar(axes[1],E_lst[0]+500,E_lst[2]+500,km=2,fs=8)
axes[0].set_title("Summer land surface temperature (Landsat, May–June 2021–2025)",loc='left',fontsize=10,weight='bold')
axes[1].set_title("Satellite view (Sentinel-2 true colour)",loc='left',fontsize=10,weight='bold')
cb=fig.colorbar(im,ax=axes[0],fraction=0.03,pad=0.01); cb.set_label('°C',fontsize=8); cb.ax.tick_params(labelsize=7)
fig.text(0.01,0.01,"A Charr / Fort Villa · B Cavalry Ground · C Malakpur · D DHA Phase 7   |   Red squares: 10 hottest 250 m residential blocks   |   Data: USGS Landsat, ESA Sentinel-2, © OpenStreetMap",fontsize=7.5,color='#444')
plt.tight_layout(rect=[0,0.03,1,1]); plt.savefig('Chhaon_DHA_Overview_Heat_vs_Satellite.png'); plt.close()
print('ok')
