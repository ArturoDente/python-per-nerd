import unittest
from pyrogue.dungeon_map import generate_dungeon
from pyrogue.constants import CHAR_STAIRS, CHAR_PLAYER

class TestDungeonMap(unittest.TestCase):
    def test_dungeon_generation(self):
        dungeon = generate_dungeon(width=60, height=20, depth=1)
        self.assertTrue(len(dungeon.rooms) > 0)
        self.assertIsNotNone(dungeon.player_start)
        self.assertIsNotNone(dungeon.stairs_pos)
        
        # Check stairs exist on map
        sx, sy = dungeon.stairs_pos
        self.assertEqual(dungeon.get_tile(sx, sy).char, CHAR_STAIRS)

    def test_boss_level_generation(self):
        dungeon = generate_dungeon(width=60, height=20, depth=5, is_boss_level=True)
        self.assertTrue(any(m.monster_type == 'boss' for m in dungeon.monsters))

if __name__ == '__main__':
    unittest.main()
