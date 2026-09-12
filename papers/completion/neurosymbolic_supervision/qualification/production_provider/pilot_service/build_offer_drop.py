"""Root-only late activation proposal. Reads public grant metadata, creates no grant/call.
Never run inside a provider: original private grant directories remain host-only.
Outputs go to a new review directory; this script does not install into the worker.
"""
import argparse,datetime as dt,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('approved_worker_adapter',Path(__file__).with_name('worker_adapter.py'));W=importlib.util.module_from_spec(spec);spec.loader.exec_module(W)
def load(p):return json.loads(Path(p).read_bytes())
def digest(p):return W.sha(Path(p).read_bytes())
def stage(worker,grants,review_path,review_sha,out):
 worker=Path(worker);W.require(worker.is_absolute()and worker.resolve()==worker,'canonical actual worker required')
 pc=W.client(worker)
 review_raw=pc.read(review_path);W.require(W.sha(review_raw)==review_sha,'scientific review changed');review=json.loads(review_raw)
 W.require(review.get('schema')=='ns028-scientific-pilot-activation-review/v1'and review.get('accepted')is True and review.get('frozen_before_comparison_outcomes')is True and review.get('comparison_scope_frozen')is True and review.get('final_admitted')is False,'reviewed pre-outcome scientific freeze required')
 W.require(review.get('reviewer_kind')=='ai_operator'and review.get('host_package_sha256')==W.HOST_PACKAGE and review.get('planned_cells')==48,'activation authority/scope differs')
 arms=review.get('retained_arms');W.require(type(arms)is list and 2<=len(arms)<=4 and len(set(arms))==len(arms) and 'A'in arms and set(arms)<={'A','B','C','D'},'NS028 requires at least two distinct retained comparison arms, including A')
 if set(arms)!={'A','B','C','D'}:W.require(W.valid_sha(review.get('scientific_arm_removal_amendment_sha256')),'subset requires pre-outcome removal amendment')
 arm_profiles=review.get('retained_arm_profiles')or{};W.require(set(arm_profiles)==set(arms)and review.get('distinct_mechanisms_verified')is True,'actual retained mechanisms need review before the first outcome')
 W.require(all(type(v.get('mechanism_id'))is str and v['mechanism_id']and W.valid_sha(v.get('source_sha256'))and W.valid_sha(v.get('qualification_sha256'))for v in arm_profiles.values())and len({v['mechanism_id']for v in arm_profiles.values()})==len(arms),'arm labels alone do not establish distinct source-bound mechanisms')
 W.require(W.valid_sha(review.get('mechanism_context_profile_sha256'))and W.valid_sha(review.get('worker_source_review_sha256')),'actual mechanism/context and worker integration review required')
 W.require(len(grants)==4,'four exact late pilot grant metadata files required');bindings=[];expiries=[]
 for path in grants:
  raw=pc.read(path);grant=json.loads(raw)
  W.require(grant.get('schema')=='operator-historical-pilot-grant/v1'and grant.get('unit')in W.UNITS and grant.get('arm')=='A'and grant.get('max_provider_calls')==1 and grant.get('authority')=='explicit_operator_pilot_grant_not_campaign_claim','grant scope differs')
  expiry=dt.datetime.fromisoformat(grant['expires_at']);W.require(expiry>dt.datetime.now(dt.timezone.utc),'expired grant: prepare only near actual activation')
  queue=Path(grant['queue']);rel=queue.relative_to(worker);W.require(rel.is_relative_to(pc.PREFIX),'queue does not belong to actual NS028 worker')
  offer_raw=pc.read(queue/'offer.json');offer=json.loads(offer_raw);req=offer['request']
  W.require(req['grant_sha256']==W.sha(raw)and req['grant_id']==grant['grant_id']and req['unit']==grant['unit']and req['amendment_sha256']==grant['amendment_sha256'],'offer/grant identity differs')
  W.require(offer['profile']==grant['profile']and offer['source_sha256']==grant['source_sha256'],'public/private profile differs')
  binding={k:v for k,v in req.items()if k not in ('schema','request_id')};binding.update(queue_relative=str(rel),offer_sha256=W.sha(offer_raw),profile=offer['profile'],source_sha256=grant['source_sha256'],manifest_sha256=grant['manifest_sha256'])
  pc.selected(worker,binding);bindings.append(binding);expiries.append(grant['expires_at'])
 W.require({b['unit']for b in bindings}==W.UNITS and len({b['batch_sha256']for b in bindings})==1,'four cells must match one frozen batch')
 W.require(review.get('batch_sha256')==bindings[0]['batch_sha256'],'reviewed batch differs')
 profile=json.loads(pc.read(worker/W.PAPER/'experiments/production_profile.json'));profile.pop('pilot_host_handoff',None)
 names={str(W.PAPER/'experiments'/n)for n in ('production_gateway.py','run_comparison.py','score_runs.py')}|{str(W.SERVICE/n)for n in ('worker_adapter.py','pilot_client.py')}
 source={n:W.sha(pc.read(worker/n))for n in sorted(names)}
 W.require(review.get('worker_source_files')==source,'review must bind actual post-NS027 integrated source')
 drop={'schema':'ns028-pilot-A-offer-drop/v1','host_package_sha256':W.HOST_PACKAGE,'client_sha256':W.CLIENT_SHA,'scientific_activation_review_sha256':review_sha,'worker_root':str(worker),'base_profile_sha256':W.sha(W.canon(profile)),'worker_source_files':source,'batch_sha256':bindings[0]['batch_sha256'],'planned_cells':48,'final_admitted':False,'bindings':sorted(bindings,key=lambda b:b['unit']),'grant_expiries':expiries}
 template=json.loads(Path(__file__).with_name('pilot_profile.template.json').read_text());template['offer_drop_sha256']=W.sha(W.canon(drop));template['scientific_activation_review_sha256']=review_sha
 profile['pilot_host_handoff']=template
 out=Path(out);out.mkdir(mode=0o700)
 for name,data in [('offer_drop.json',W.canon(drop)),('production_profile.proposed.json',W.canon(profile))]:
  fd=os.open(out/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb')as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
 fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 return {'schema':'ns028-late-offer-drop-staged/v1','installed':False,'grants_created':0,'model_calls':0,'scorer_calls':0,'worker_root':str(worker),'drop_sha256':template['offer_drop_sha256'],'profile_sha256':digest(out/'production_profile.proposed.json'),'review_sha256':review_sha}
def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',type=Path,required=True);p.add_argument('--grant',type=Path,action='append',required=True);p.add_argument('--review',type=Path,required=True);p.add_argument('--review-sha256',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(stage(a.worker,a.grant,a.review,a.review_sha256,a.out),sort_keys=True))
if __name__=='__main__':main()
