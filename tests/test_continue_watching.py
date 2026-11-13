import unittest
from anistream.library import continue_items, history_items, record_progress, series_metadata


class ContinueWatchingTests(unittest.TestCase):
    def setUp(self):
        self.state = {'favorites':{}, 'history':{}, 'positions':{}, 'durations':{}}
        self.item = {'path':'/media/example', 'title':'Ejemplo', 'image':'', 'description':'Serie'}

    def test_progress_is_available_to_resume_without_modifying_metadata(self):
        record_progress(self.state, self.item, 3, 105, 1440, watched_at=1)
        cards = continue_items(self.state)
        self.assertEqual(cards[0]['episode'],3)
        self.assertEqual(cards[0]['_resume_position'],105)
        self.assertEqual(cards[0]['_resume_duration'],1440)
        self.assertNotIn('_resume_position', self.state['history'][self.item['path']])

    def test_unstarted_and_completed_episodes_are_not_continue_cards(self):
        self.assertFalse(record_progress(self.state,self.item,1,0,1440))
        self.assertEqual(continue_items(self.state),[])
        record_progress(self.state,self.item,1,1400,1440)
        self.assertEqual(continue_items(self.state),[])
        self.assertEqual(len(history_items(self.state)),1)

    def test_unknown_duration_can_be_resumed(self):
        record_progress(self.state,self.item,1,35)
        self.assertEqual(len(continue_items(self.state)),1)

    def test_most_recent_played_series_first_and_one_card_per_series(self):
        other = dict(self.item,path='/media/other')
        record_progress(self.state,self.item,1,10,1440,watched_at=1)
        record_progress(self.state,other,1,20,1440,watched_at=2)
        record_progress(self.state,self.item,2,30,1440,watched_at=3)
        cards=continue_items(self.state)
        self.assertEqual([i['path'] for i in cards],[self.item['path'],other['path']])
        self.assertEqual(cards[0]['episode'],2)

    def test_finished_latest_episode_does_not_restore_an_old_episode(self):
        record_progress(self.state,self.item,1,50,1440)
        record_progress(self.state,self.item,2,1430,1440)
        self.assertEqual(continue_items(self.state),[])

    def test_existing_libraries_without_timestamps_still_work(self):
        self.state['history'][self.item['path']]=dict(self.item,episode=4)
        self.state['positions'][self.item['path']]={'4':60}
        self.assertEqual(continue_items(self.state)[0]['episode'],4)

    def test_favorites_store_only_series_metadata(self):
        card=dict(self.item,episode=3,_resume_position=120,_resume_duration=1440)
        self.assertEqual(series_metadata(card),self.item)

if __name__=='__main__':unittest.main()
