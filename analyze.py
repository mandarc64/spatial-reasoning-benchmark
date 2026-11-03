"""Draw the article figures directly from PostGIS outputs; no generated imagery."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

ROOT = Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                     'axes.spines.right':False,'savefig.facecolor':'white'})

def figures():
    rows=json.loads((ROOT/'airport_example.json').read_text())
    fig,(ax,bars)=plt.subplots(1,2,figsize=(12,5.5),gridspec_kw={'width_ratios':[1.05,1]})
    fig.suptitle('“Nearest” and “within 100 km” ask different questions',fontsize=18,fontweight='bold',x=.06,ha='left')
    ax.scatter([r['lon'] for r in rows],[r['lat'] for r in rows],s=55,
               c=['#087e8b' if r['distance_m']<=100000 else '#b8c1ca' for r in rows],zorder=3)
    for r in rows:
        offset={'KBUR':(-45,16),'KLAX':(10,-17)}.get(r['ident'],(5,5))
        ax.annotate(r['ident'],(r['lon'],r['lat']),xytext=offset,textcoords='offset points',fontsize=9)
    ax.scatter([-118.3],[34.1],marker='*',s=200,color='#e67e22',label='Reference (−118.3°, 34.1°)',zorder=4)
    ax.set(xlabel='Longitude (degrees)',ylabel='Latitude (degrees)',title='Four closest airports in the frozen 40-airport candidate set')
    ax.set_aspect(1/np.cos(np.deg2rad(34.1)))
    ax.margins(y=.15)
    ax.grid(alpha=.15); ax.legend(loc='best',fontsize=8,frameon=False)
    colors=['#087e8b' if r['distance_m']<=100000 else '#b8c1ca' for r in rows]
    y=np.arange(len(rows)); km=np.array([r['distance_m']/1000 for r in rows])
    bars.barh(y,km,color=colors,height=.66)
    bars.set_yticks(y,[r['ident'] for r in rows]); bars.invert_yaxis()
    bars.axvline(100,ls='--',color='#e67e22',lw=1.5,label='100 km threshold')
    for j,d in enumerate(km): bars.text(d+max(km)*.018,j,f'{d:.1f}',va='center',fontsize=9)
    bars.set(xlabel='PostGIS spheroidal distance (km)',title='One nearest result; a radius query can return several')
    bars.set_xlim(0,max(km)*1.22); bars.legend(frameon=False,fontsize=9)
    fig.text(.06,.025,'Source: OurAirports frozen subset. Distances: ST_Distance(geography). Candidate set is deliberately limited; no wildfire data.',fontsize=9,color='#4f5b66')
    fig.tight_layout(rect=[0,.07,1,.91]); fig.savefig(ROOT/'figure_1_airport_distances.png',dpi=200); plt.close(fig)

    rows=json.loads((ROOT/'predicate_diagnostics.json').read_text())
    fields=['contains','covers','intersects','within_1m']
    matrix=np.array([[int(r[f]) for f in fields] for r in rows])
    fig,(scene,heat)=plt.subplots(1,2,figsize=(12,5.4),gridspec_kw={'width_ratios':[.9,1.5]})
    fig.suptitle('A boundary point changes the answer',fontsize=19,fontweight='bold',x=.055,ha='left')
    scene.fill([0,10,10,0],[0,0,10,10],facecolor='#e4f1f2',edgecolor='#087e8b',lw=2)
    pts=[(5,5),(0,5),(-.5,5),(-2,5)]
    for (x,y),label,textpos in zip(pts,['Interior','Boundary','Outside, 0.5 m','Outside, 2 m'],[(5.4,6),(1,2.5),(-2.9,9),(-3.6,7.2)]):
        scene.scatter([x],[y],s=35,color='#152f45',zorder=3)
        scene.annotate(label,(x,y),xytext=textpos,textcoords='data',fontsize=9,arrowprops={'arrowstyle':'-','color':'#526676','lw':.8})
    scene.set(xlim=(-4,12),ylim=(-1,11),xlabel='Synthetic x (m)',ylabel='Synthetic y (m)',title='Exact synthetic geometry (SRID 3857)')
    scene.set_aspect('equal'); scene.grid(alpha=.1)
    heat.imshow(matrix,cmap=ListedColormap(['#edf0f3','#087e8b']),vmin=0,vmax=1,aspect='auto')
    heat.set_xticks(range(4),['Contains','Covers','Intersects','DWithin\n≤ 1 m'])
    heat.set_yticks(range(4),[r['label'] for r in rows]); heat.tick_params(length=0,pad=8)
    for i in range(4):
        for j in range(4): heat.text(j,i,'TRUE' if matrix[i,j] else 'FALSE',ha='center',va='center',color='white' if matrix[i,j] else '#405366',fontweight='bold')
    for spine in heat.spines.values(): spine.set_visible(False)
    heat.set_title('Actual PostGIS predicate outputs',pad=18)
    fig.text(.055,.025,'Source: predicate_diagnostics.json, computed by PostGIS. These are geometry results, not LLM evaluation scores.',fontsize=9,color='#4f5b66')
    fig.tight_layout(rect=[0,.07,1,.91]); fig.savefig(ROOT/'figure_2_boundary_predicates.png',dpi=200); plt.close(fig)
    counts={}
    with (ROOT/'ground_truth_results.csv').open(newline='',encoding='utf-8') as f:
        for r in csv.DictReader(f): counts[r['task']]=counts.get(r['task'],0)+1
    assert len(counts)==8 and set(counts.values())=={30},counts
    (ROOT/'benchmark_summary.json').write_text(json.dumps({'questions_per_task':counts,'total':sum(counts.values()),'llm_evaluation':'pending; zero model calls'},indent=2)+'\n')
    print('Wrote two figures from real PostGIS outputs; all eight tasks contain 30 questions.')

if __name__=='__main__': figures()
