"""Download ten named public comma10k samples and evaluate road segmentation."""
import json
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
from app import SegFormerAdapter, PALETTE, segment, detect_lane_markings

ROOT=Path(__file__).resolve().parent
BASE='https://raw.githubusercontent.com/commaai/comma10k/master/'
FILES=[
 '0000_0085e9e41513078a_2018-08-19--13-26-08_11_864.png',
 '0001_a23b0de0bc12dcba_2018-06-24--00-29-19_17_79.png',
 '0002_e8e95b54ed6116a6_2018-09-05--22-04-33_2_608.png',
 '0003_97a4ec76e41e8853_2018-09-29--22-46-37_5_585.png',
 '0004_2ac95059f70d76eb_2018-05-12--17-46-52_56_371.png',
 '0005_836d09212ac1b8fa_2018-06-15--15-57-15_23_345.png',
 '0006_0c5c849415c7dba2_2018-08-12--10-26-26_5_1159.png',
 '0007_b5e785c1fc446ed0_2018-06-14--08-27-35_78_873.png',
 '0008_b8727c7398d117f5_2018-10-22--15-38-24_71_990.png',
 '0009_ef53f1ffea65e93c_2018-07-26--03-48-48_14_191.png',
]
model_name='nvidia/segformer-b0-finetuned-cityscapes-1024-1024'
model=SegFormerAdapter(model_name)
road_ids=[int(k) for k,v in model.model.config.id2label.items() if str(v).lower()=='road']
rows=[]
for name in FILES:
    folder=ROOT/'data'/'comma10k'; folder.mkdir(parents=True,exist_ok=True)
    for group in ('imgs','masks'):
        target=folder/group/name; target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            with urllib.request.urlopen(BASE+group+'/'+name,timeout=60) as response: target.write_bytes(response.read())
    image=Image.open(folder/'imgs'/name).convert('RGB')
    target=np.asarray(Image.open(folder/'masks'/name).convert('RGB'))
    truth=np.all(target == [64,32,32],axis=2)
    valid=np.any(target != [204,0,255],axis=2)
    pred=np.isin(model.predict_labels(image),road_ids)
    lane_truth=np.all(target == [255,0,0],axis=2)
    lane_pred=detect_lane_markings(image,pred)
    baseline=np.all(np.asarray(segment(image)[0]) == PALETTE['road'],axis=2)
    def iou(p):
        intersection=np.logical_and(np.logical_and(p,truth),valid).sum()
        union=np.logical_and(np.logical_or(p,truth),valid).sum()
        return round(float(intersection/union),4) if union else None
    lane_union=np.logical_and(np.logical_or(lane_truth,lane_pred),valid).sum()
    lane_intersection=np.logical_and(np.logical_and(lane_truth,lane_pred),valid).sum()
    row={'image':name,'segformer_road_iou':iou(pred),'baseline_road_iou':iou(baseline),'lane_iou':round(float(lane_intersection/lane_union),4) if lane_union else None}
    rows.append(row); print(json.dumps(row),flush=True)
lane_values=[r['lane_iou'] for r in rows if r['lane_iou'] is not None]
result={'dataset':'comma10k','dataset_source':BASE,'model':model_name,'samples':len(rows),'metric':'mean per-image IoU','segformer_mean_road_iou':round(float(np.mean([r['segformer_road_iou'] for r in rows])),4),'baseline_mean_road_iou':round(float(np.mean([r['baseline_road_iou'] for r in rows])),4),'opencv_mean_lane_iou':round(float(np.mean(lane_values)),4) if lane_values else None,'exclude':'own-car pixels','samples_detail':rows,'limitations':'ten selected images; OpenCV lane heuristic tuned using the first image; the reported set is not independent'}
(ROOT/'artifacts'/'comma10k_10_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
