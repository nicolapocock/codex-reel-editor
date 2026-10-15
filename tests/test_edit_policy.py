import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/reel-editor/scripts'))
from edit_policy import prepare_edit, sound_name
class RenderPolicyTests(unittest.TestCase):
 def test_fixed_captions_override_old_gesture_positions_without_mutation(self):
  d={'captions':[{'x':610,'y':1270,'size':70,'words':[]}],'cards':[]}
  out=prepare_edit(d,{})
  self.assertNotIn('y',out['captions'][0]);self.assertEqual(d['captions'][0]['y'],1270)
 def test_explicit_moving_captions_opt_out(self):
  d={'captionStyle':{'fixedPosition':False},'captions':[{'y':400}],'cards':[]}
  self.assertEqual(prepare_edit(d,{})['captions'][0]['y'],400)
 def test_single_line_and_width(self):
  c=prepare_edit({'cards':[{'type':'title','text':'my ai / reel editor','single_line':True,'size':230}]},{})['cards'][0]
  self.assertEqual(c['text'],'my ai reel editor');self.assertLessEqual(c['size']*len(c['text'])*.66,900)
 def test_no_manual_head_clipping(self):
  with self.assertRaisesRegex(ValueError,'hair/face'):prepare_edit({'cards':[{'type':'guide_scroll','subject_style':'clip-path:polygon(...)'}]}, {})
 def test_sound_aliases(self):
  self.assertEqual(sound_name('coin'),'chime');self.assertEqual(sound_name('sparkle'),'chime');self.assertEqual(sound_name('click'),'snap')
 def test_bad_times(self):
  with self.assertRaises(ValueError):prepare_edit({'cards':[{'type':'tag','start':2,'end':1}]},{})
if __name__=='__main__':unittest.main()
