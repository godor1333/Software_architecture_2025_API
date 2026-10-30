"""Evaluate fixed pretrained models on held-out comma10k images."""
import argparse
import concurrent.futures
import hashlib
import json
import random
import urllib.request
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from app import SegFormerAdapter, detect_lane_markings

ROOT=Path(__file__).resolve().parent
REV='6c205fe4c43cc53b2b1befafb1060d0606555027'
BASE=f'https://raw.githubusercontent.com/commaai/comma10k/{REV}/'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=100)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'data'/'independent')
    args=parser.parse_args();args.data_dir.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(BASE+'files_trainable',timeout=90) as response:
        names=[Path(x).name for x in response.read().decode().splitlines() if x.startswith('masks/')]
    # Files 0000–0009 were used earlier. Select only the project's suggested
    # validation names ending in 9.png, excluding those ten and duplicates.
    candidates=sorted({name for name in names if name.endswith('9.png') and name[:4].isdigit() and int(name[:4])>=10})
    if len(candidates)<args.count: raise ValueError('insufficient candidate images')
    selected=sorted(random.Random(20261029).sample(candidates,args.count))
    def fetch(task):
        group,name=task; path=args.data_dir/group/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            request=urllib.request.Request(BASE+group+'/'+name,headers={'User-Agent':'CourseworkEvaluation/1.0'})
            with urllib.request.urlopen(request,timeout=120) as response: path.write_bytes(response.read())
        return path
    tasks=[(group,name) for name in selected for group in ('imgs','masks')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(fetch,tasks))
    torch.set_num_threads(4)
    model_name='nvidia/segformer-b0-finetuned-cityscapes-1024-1024'
    model=SegFormerAdapter(model_name)
    id2label=model.model.config.id2label
    road_ids=[int(k) for k,v in id2label.items() if str(v).lower()=='road']
    ground_ids=[int(k) for k,v in id2label.items() if str(v).lower() in {'road','sidewalk','parking','rail track'}]
    movable_ids=[int(k) for k,v in id2label.items() if str(v).lower() in {'car','truck','bus','train','motorcycle','bicycle','person','rider'}]
    rows=[]; pooled={key:[0,0] for key in ('road','lane','baseline_road','pipeline_road','pipeline_lane','movable')}
    for idx,name in enumerate(selected,1):
        image_path=args.data_dir/'imgs'/name; mask_path=args.data_dir/'masks'/name
        image=Image.open(image_path).convert('RGB'); target=np.asarray(Image.open(mask_path).convert('RGB'))
        valid=np.any(target != [204,0,255],axis=2)
        truth_road=np.all(target==[64,32,32],axis=2)
        truth_lane=np.all(target==[255,0,0],axis=2)
        model_labels=model.predict_labels(image)
        prediction=np.isin(model_labels,road_ids)
        lane=detect_lane_markings(image,prediction)
        pipeline_ground=np.isin(model_labels,ground_ids)
        pipeline_lane=detect_lane_markings(image,pipeline_ground)
        pipeline_road=pipeline_ground & ~pipeline_lane
        movable=np.isin(model_labels,movable_ids)
        truth_movable=np.all(target==[0,255,102],axis=2)
        rgb=np.asarray(image); r,g,b=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
        baseline_road=~(((r>170)&(g<110)&(b<110)) | ((r>190)&(g>140)&(b<80)) | ((r>215)&(g>215)&(b>215)) | ((b>150)&(r<110)))
        values={}
        for key,truth,pred in [('road',truth_road,prediction),('lane',truth_lane,lane),('baseline_road',truth_road,baseline_road),('pipeline_road',truth_road,pipeline_road),('pipeline_lane',truth_lane,pipeline_lane),('movable',truth_movable,movable)]:
            intersection=int((truth & pred & valid).sum()); union=int(((truth | pred) & valid).sum())
            pooled[key][0]+=intersection;pooled[key][1]+=union
            values[key+'_iou']=round(intersection/union,4) if union else None
        rows.append({'image':name,'image_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),
                     'mask_sha256':hashlib.sha256(mask_path.read_bytes()).hexdigest(),**values})
        if idx%10==0: print(f'Evaluated {idx}/{len(selected)}',flush=True)
    def mean_iou(key):
        values=[row[key+'_iou'] for row in rows if row[key+'_iou'] is not None]
        return round(float(np.mean(values)),4) if values else None
    result={'dataset':'commaai/comma10k','revision':REV,'model':model_name,'samples':len(rows),'seed':20261029,
            'selection':'random subset of validation filenames ending in 9.png, excluding first ten prior samples',
            'road_mean_image_iou':mean_iou('road'),'road_pooled_iou':round(pooled['road'][0]/pooled['road'][1],4),
            'lane_mean_image_iou':mean_iou('lane'),'lane_pooled_iou':round(pooled['lane'][0]/pooled['lane'][1],4),
            'baseline_road_mean_image_iou':mean_iou('baseline_road'),'baseline_road_pooled_iou':round(pooled['baseline_road'][0]/pooled['baseline_road'][1],4),
            'pipeline_road_mean_image_iou':mean_iou('pipeline_road'),'pipeline_road_pooled_iou':round(pooled['pipeline_road'][0]/pooled['pipeline_road'][1],4),
            'pipeline_lane_mean_image_iou':mean_iou('pipeline_lane'),'pipeline_lane_pooled_iou':round(pooled['pipeline_lane'][0]/pooled['pipeline_lane'][1],4),
            'movable_mean_image_iou':mean_iou('movable'),'movable_pooled_iou':round(pooled['movable'][0]/pooled['movable'][1],4) if pooled['movable'][1] else None,
            'movable_annotation':'Combined vehicles, people and animals; not a per-class evaluation.',
            'excluded_pixels':'own car','rows':rows,
            'limitations':'No known overlap with earlier tuning sample; model training overlap with comma10k is unknown; image sources are dashboard rather than drone cameras.'}
    (ROOT/'artifacts'/'independent_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
