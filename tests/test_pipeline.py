"""Fictional regression fixtures. These tests are not a real-user accuracy benchmark."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from twinlight_core.common import ROOT,ContractError,load,save,digest,safe_script_json,privacy_findings,local_asset
from twinlight_core.history import normalize,make_chunks,timestamp
from twinlight_core.evidence import verify,anchor
from twinlight_core.compiler import compile_profile,check_approval
from twinlight_core.layout import make_layout
from twinlight_core.art import validate_layers,asset_digest
from twinlight_core.site import placeholder_layers,build
from twinlight_core.extraction import merge_chunks
from PIL import Image

class Pipeline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  self.h=load(ROOT/'examples/demo/history.json');self.a=load(ROOT/'examples/demo/analysis.json')
 def raw(self,value):save(self.p/'input.json',value);return self.p/'input.json'
 def reject(self,a=None,h=None):
  with self.assertRaises(ContractError):verify(h or self.h,a or self.a)
 def receipt(self):
  return {'schema_version':'1.0','analysis_digest':digest(self.a),'art_digest':None,'approved_by':'fixture-reviewer','scope':'local_preview','confirmed_at':'2026-10-02T00:00:00Z','acknowledgments':{k:True for k in ['reviewed_personal_facts','reviewed_public_copy','understands_source_coverage','permits_selected_output']}}
 def test_demo_verified(self):self.assertEqual(verify(self.h,self.a)['accounted_user_messages'],10)
 def test_not_claim_semantic_truth(self):self.assertFalse(verify(self.h,self.a)['semantic_truth_verified_by_code'])
 def test_generic_normalization_reproducible(self):
  h=normalize(ROOT/'examples/demo/history-input.json','generic',scope='provided_subset');self.assertEqual(h,self.h)
 def test_missing_dates_not_inferred(self):self.assertEqual(self.h['coverage']['unknown_dates'],1);self.assertFalse(self.h['coverage']['account_history_complete'])
 def test_ambiguous_timezone(self):
  with self.assertRaises(ContractError):timestamp('2025-01-01T11:00:00')
 def test_epoch_and_timezone(self):self.assertEqual(timestamp(0),'1970-01-01T00:00:00Z');self.assertEqual(timestamp('2025-01-01T08:00:00+08:00'),'2025-01-01T00:00:00Z')
 def test_bool_not_timestamp(self):
  with self.assertRaises(ContractError):timestamp(True)
 def test_chatgpt_active_branch(self):
  def msg(i,text):return {'id':i,'author':{'role':'user'},'content':{'parts':[text]},'create_time':None}
  raw=[{'id':'c','current_node':'new','mapping':{'root':{'parent':None,'message':None},'old':{'parent':'root','message':msg('old','旧分支')},'new':{'parent':'root','message':msg('new','选定分支')}}}]
  h=normalize(self.raw(raw),'auto');self.assertEqual(len(h['messages']),1);self.assertEqual(h['messages'][0]['text'],'选定分支');self.assertEqual(h['coverage']['omitted'][0]['reason'],'inactive_branch')
 def test_chatgpt_missing_ambiguous_branch(self):
  raw=[{'id':'c','mapping':{'r':{'parent':None},'a':{'parent':'r'},'b':{'parent':'r'}}}]
  with self.assertRaises(ContractError):normalize(self.raw(raw),'chatgpt')
 def test_chatgpt_cycle(self):
  with self.assertRaises(ContractError):normalize(self.raw([{'id':'c','current_node':'a','mapping':{'a':{'parent':'a'}}}]),'chatgpt')
 def test_claude_text_blocks_and_images(self):
  raw=[{'uuid':'c','chat_messages':[{'uuid':'m','sender':'human','created_at':None,'content':[{'type':'text','text':'你好'},{'type':'image','source':{}},{'type':'text','text':'观察记录'}]}]}]
  h=normalize(self.raw(raw),'auto');self.assertEqual(h['messages'][0]['text'],'你好\n观察记录');self.assertEqual(h['coverage']['unread_nontext_parts'],1)
 def test_duplicate_ids_conflicting(self):
  raw={'messages':[{'id':'x','conversation_id':'c','role':'user','text':t} for t in ['a','b']]}
  with self.assertRaises(ContractError):normalize(self.raw(raw),'generic')
 def test_duplicate_ids_equal_deduplicated(self):
  m={'id':'x','conversation_id':'c','role':'user','text':'a'};h=normalize(self.raw({'messages':[m,m]}),'generic');self.assertEqual(len(h['messages']),1)
 def test_unknown_role(self):
  with self.assertRaises(ContractError):normalize(self.raw({'messages':[{'id':'m','conversation_id':'c','role':'alien','text':'a'}]}),'generic')
 def test_duplicate_json_key(self):
  p=self.p/'a.json';p.write_text('{"a":1,"a":2}')
  with self.assertRaises(ContractError):load(p)
 def test_nan_rejected(self):
  p=self.p/'a.json';p.write_text('{"a":NaN}')
  with self.assertRaises(ContractError):load(p)
 def test_exact_quotes(self):self.a['facts'][0]['evidence'][0]['quote']+='错';self.reject()
 def test_offsets(self):self.a['facts'][0]['evidence'][0]['start']=1;self.reject()
 def test_wrong_quote_hash(self):self.a['facts'][0]['evidence'][0]['text_sha256']='0'*64;self.reject()
 def test_history_snapshot_changed(self):self.h['messages'][0]['text']='different';self.reject()
 def test_analysis_stale(self):self.a['history_digest']='1'*64;self.reject()
 def test_assistant_not_personal_evidence(self):
  m=next(m for m in self.h['messages'] if m['role']=='assistant');self.a['facts'][0]['evidence']=[anchor(m,m['text'])];self.reject()
 def test_plan_not_achievement_status(self):
  f=next(f for f in self.a['facts'] if f['kind']=='plan');f['status']='current';self.reject()
 def test_question_not_current_ability(self):
  f=next(f for f in self.a['facts'] if f['kind']=='question');f['status']='current';self.reject()
 def test_third_party_not_user(self):self.a['facts'][0]['speech_context']='third_party';self.reject()
 def test_unresolved_fact_not_published(self):self.a['facts'][0]['review']='needs_confirmation';self.reject()
 def test_memory_only_not_verbatim(self):
  self.h['coverage']['scope']='memory_only';self.h['history_digest']=digest({'messages':self.h['messages'],'coverage':self.h['coverage']});self.a['history_digest']=self.h['history_digest'];self.reject()
 def test_every_message_accounted(self):self.a['message_dispositions'].pop();self.reject()
 def test_sensitive_not_public(self):self.a['facts'][0]['sensitivity']='sensitive';self.reject()
 def test_conflicting_current_state(self):
  fs=[f for f in self.a['facts'] if f['status']=='current'];fs[0]['conflict_key']=fs[1]['conflict_key']='job';self.reject()
 def test_supersede_cycle(self):
  a,b=self.a['facts'][:2];a['supersedes']=[b['id']];b['supersedes']=[a['id']];self.reject()
 def test_persona_references_closed(self):self.a['card']['basis_fact_ids']=[];self.reject()
 def test_reference_photo_needs_consent(self):self.a['card']['portrait_mode']='user_reference';self.reject()
 def test_ssr_constant(self):self.a['card']['rarity']='SR';self.reject()
 def test_provider_mismatch(self):self.a['summary_meta']['provider']='anthropic';self.reject()
 def test_claude_author(self):
  self.a['summary_meta'].update(provider='anthropic',display_name='Claude');self.assertTrue(verify(self.h,self.a)['ok'])
 def test_provider_not_inferred_from_history(self):
  self.a['summary_meta'].update(provider='unknown',display_name=None,attribution_source='unknown');p,_,_=compile_profile(self.h,self.a);self.assertIsNone(p['summary_meta']['display_name'])
 def test_compile_no_original_quotes(self):
  p,_,_=compile_profile(self.h,self.a);self.assertNotIn('text_sha256',json.dumps(p));self.assertEqual(p['chapters'][0]['quotes'],[])
 def test_sensitive_copy_gate(self):
  self.a['themes'][0]['headline']['text']='请联系 demo@example.com'
  with self.assertRaises(ContractError):compile_profile(self.h,self.a)
 def test_redaction_errors_dont_echo_secret(self):self.assertEqual(privacy_findings('demo@example.com'),[{'path':'$','kind':'email'}])
 def test_script_escape(self):s=safe_script_json({'x':'</script>\u2028&'});self.assertNotIn('</script>',s);self.assertNotIn('\u2028',s);self.assertIn('\\u003c',s)
 def test_layout_repeated_exact(self):self.assertEqual(make_layout(self.a,self.h),make_layout(self.a,self.h))
 def test_layout_input_order_does_not_matter(self):
  x=make_layout(self.a,self.h);self.a['themes'].reverse()
  for t in self.a['themes']:t['topics'].reverse()
  self.assertEqual(x,make_layout(self.a,self.h))
 def test_existing_layout_locked_on_add(self):
  x=make_layout(self.a,self.h);t=copy.deepcopy(self.a['themes'][0]);t['id']='another-theme';self.a['themes'].append(t);y=make_layout(self.a,self.h,x)
  self.assertTrue(all(s in y['stars'] for s in x['stars']));self.assertTrue(all(s in y['topics'] for s in x['topics']))
 def test_layout_wrong_owner(self):
  x=make_layout(self.a,self.h);self.a['owner']['id']='another-person'
  with self.assertRaises(ContractError):make_layout(self.a,self.h,x)
 def test_main_star_count_not_five(self):self.assertEqual(len(make_layout(self.a,self.h)['stars']),3)
 def test_no_invented_theme_when_empty(self):
  self.a['themes']=[]
  with self.assertRaises(ContractError):make_layout(self.a,self.h)
 def test_max_eight_themes(self):
  self.a['themes']=[{**self.a['themes'][0],'id':f'theme-{i}'} for i in range(9)]
  with self.assertRaises(ContractError):make_layout(self.a,self.h)
 def test_chunks_cover_chars_exactly(self):
  m=make_chunks(self.h,self.p/'chunks',1000);text={x['id']:'' for x in self.h['messages']}
  for e in m['chunks']:
   for s in load(self.p/'chunks'/e['path'])['segments']:text[s['message_id']]+=s['text']
  self.assertEqual(text,{x['id']:x['text'] for x in self.h['messages']})
 def test_chunk_merge_missing_not_success(self):
  m=self.p/'chunks';make_chunks(self.h,m,1000);results=self.p/'results';results.mkdir()
  with self.assertRaises(ContractError):merge_chunks(self.h,self.a,m/'manifest.json',results)
 def test_asset_path_escape(self):
  with self.assertRaises(ContractError):local_asset(self.p,'../outside.png')
 def test_asset_remote_rejected(self):
  with self.assertRaises(ContractError):local_asset(self.p,'https://example.com/photo.png')
 def test_asset_symlink_escape(self):
  (self.p/'link').symlink_to('/etc/hosts')
  with self.assertRaises(ContractError):local_asset(self.p,'link')
 def test_placeholder_real_alpha_but_not_approved(self):
  m=placeholder_layers(self.p/'art','a'*64);r=validate_layers(m,'a'*64);self.assertEqual(r['art_status'],'placeholder');self.assertGreater(r['layers']['subject']['transparent_fraction'],.1)
 def test_art_wrong_persona(self):
  m=placeholder_layers(self.p/'art','a'*64)
  with self.assertRaises(ContractError):validate_layers(m,'b'*64)
 def test_opaque_fake_alpha(self):
  m=placeholder_layers(self.p/'art','a'*64);Image.new('RGB',(600,800),'white').save(m.parent/'subject.png')
  with self.assertRaises(ContractError):validate_layers(m)
 def test_empty_subject_rejected(self):
  m=placeholder_layers(self.p/'art','a'*64);Image.new('RGBA',(600,800)).save(m.parent/'subject.png')
  with self.assertRaises(ContractError):validate_layers(m)
 def test_equal_depth_fails(self):
  m=placeholder_layers(self.p/'art','a'*64);j=load(m);j['depths']['effects']=j['depths']['subject'];save(m,j)
  with self.assertRaises(ContractError):validate_layers(m)
 def test_asset_hash_changes(self):
  m=placeholder_layers(self.p/'art','a'*64);d=asset_digest(m);im=Image.open(m.parent/'effects.png');im.putpixel((30,30),(255,255,255,255));im.save(m.parent/'effects.png');self.assertNotEqual(d,asset_digest(m))
 def test_stale_approval_rejected(self):
  r=self.receipt();self.a['owner']['display_name']='改名'
  with self.assertRaises(ContractError):check_approval(self.a,r)
 def test_local_build(self):
  r=build(self.h,self.a,self.p/'site');self.assertFalse(r['share_allowed']);self.assertTrue((self.p/'site/index.html').exists());self.assertNotIn('sensitive_excluded',r['audit']);self.assertNotIn('needs_confirmation',r['audit'])
 def test_all_branches_marked_unreconciled(self):
  raw=[{'id':'c','mapping':{'a':{'parent':None,'message':{'id':'a','author':{'role':'user'},'content':{'parts':['hi']}}}}}]
  h=normalize(self.raw(raw),'chatgpt','all');self.assertEqual(h['messages'][0]['branch'],'all-unreconciled')


class Integration(Pipeline):
 # Use just this class's explicit methods, not inherited test methods, below.
 def test_chunk_merge_success(self):
  chunks=self.p/'chunks';m=make_chunks(self.h,chunks,1000);res=self.p/'results';res.mkdir()
  self.assertEqual(len(m['chunks']),1)
  e=m['chunks'][0];save(res/'one.json',{'chunk_path':e['path'],'chunk_sha256':e['sha256'],'history_digest':self.h['history_digest'],'facts':self.a['facts'],'message_dispositions':self.a['message_dispositions']})
  draft=merge_chunks(self.h,self.a,chunks/'manifest.json',res);self.assertEqual(len(draft['facts']),8);self.assertIsNone(draft['card']);self.assertEqual(draft['themes'],[])
 def test_share_receipt_binds_art(self):
  profile,_,_=compile_profile(self.h,self.a);m=placeholder_layers(self.p/'art',profile['persona']['persona_digest']);j=load(m);j['art_status']='approved';save(m,j)
  receipt=self.receipt();receipt.update(scope='share',art_digest=asset_digest(m));r=build(self.h,self.a,self.p/'site',layers=m,approval=receipt);self.assertTrue(r['share_allowed'])
  im=Image.open(m.parent/'subject.png');im.putpixel((10,10),(255,255,255,255));im.save(m.parent/'subject.png')
  with self.assertRaises(ContractError):build(self.h,self.a,self.p/'site2',layers=m,approval=receipt)
 def test_eight_by_eight_capacity(self):
  theme=self.a['themes'][0];self.a['themes']=[]
  for i in range(8):
   t=copy.deepcopy(theme);t['id']=f'theme-{i}';topic=t['topics'][0];t['topics']=[{**copy.deepcopy(topic),'id':f'planet-{j}'} for j in range(8)];self.a['themes'].append(t)
  profile,layout,_=compile_profile(self.h,self.a);self.assertEqual(len(layout['stars']),8);self.assertEqual(len(layout['topics']),64)
  self.assertLess(len(json.dumps(profile,ensure_ascii=False).encode()),524288)
 def test_one_star_without_planets(self):
  self.a['themes']=self.a['themes'][:1];self.a['themes'][0]['topics']=[];profile,layout,_=compile_profile(self.h,self.a);self.assertEqual(len(layout['stars']),1);self.assertEqual(layout['topics'],[])

# Avoid reporting the inherited regression suite twice as extra coverage.
def load_tests(loader,tests,pattern):
 suite=unittest.TestSuite();suite.addTests(loader.loadTestsFromTestCase(Pipeline))
 for name in Integration.__dict__:
  if name.startswith('test_'):suite.addTest(Integration(name))
 return suite

if __name__=='__main__':unittest.main()
