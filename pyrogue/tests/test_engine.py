import unittest
from pyrogue.engine import GameEngine

class TestEngine(unittest.TestCase):
    def test_engine_initialization(self):
        engine = GameEngine()
        self.assertEqual(engine.remaining_dungeons, 4)
        self.assertEqual(engine.current_depth, 1)
        self.assertFalse(engine.game_over)
        self.assertFalse(engine.victory)

    def test_potion_usage(self):
        engine = GameEngine()
        engine.player.hp = 10
        self.assertTrue(engine.use_hp_potion())
        self.assertEqual(engine.player.hp, 25)
        self.assertEqual(engine.player.hp_potions, 1)

    def test_stairs_descent(self):
        engine = GameEngine()
        initial_remaining = engine.remaining_dungeons
        initial_mp = engine.player.max_mp
        initial_str = engine.player.str_stat
        initial_hp = engine.player.max_hp
        
        engine.descend_stairs()
        
        self.assertEqual(engine.remaining_dungeons, initial_remaining - 1)
        self.assertEqual(engine.player.max_mp, initial_mp + 1)
        self.assertEqual(engine.player.str_stat, initial_str + 2)
        self.assertEqual(engine.player.max_hp, initial_hp + 5)
        self.assertEqual(engine.current_depth, 2)

    def test_direction_tracking_and_fire_ranged(self):
        engine = GameEngine()
        # Move up/down/left/right updates facing direction
        engine.move_player(0, -1)
        self.assertEqual((engine.player.last_dx, engine.player.last_dy), (0, -1))
        engine.move_player(1, 0)
        self.assertEqual((engine.player.last_dx, engine.player.last_dy), (1, 0))

        # Test fire_ranged action
        initial_charges = engine.player.equipped_ranged.charges
        res = engine.fire_ranged()
        self.assertTrue(res)
        self.assertEqual(engine.player.equipped_ranged.charges, initial_charges - 1)

    def test_smart_spell_targeting_and_line_of_sight(self):
        from pyrogue.entities import create_orc, create_goblin
        from pyrogue.tile import make_wall, make_floor

        engine = GameEngine()
        engine.dungeon.monsters.clear()
        for y in range(engine.dungeon.height):
            for x in range(engine.dungeon.width):
                engine.dungeon.set_tile(x, y, make_floor())

        engine.player.x, engine.player.y = 5, 5
        engine.player.last_dx, engine.player.last_dy = 1, 0  # Facing East

        # Orc in front (East, dist 5)
        orc = create_orc(10, 5)
        engine.dungeon.monsters.append(orc)

        # Goblin to North (dist 3, closer but perpendicular)
        goblin = create_goblin(5, 2)
        engine.dungeon.monsters.append(goblin)

        # Facing East: should prioritize Orc in front over closer perpendicular Goblin
        target = engine._find_nearest_monster()
        self.assertEqual(target.name, "Orc")

        # Facing North: should prioritize Goblin in front
        engine.player.last_dx, engine.player.last_dy = 0, -1
        target_north = engine._find_nearest_monster()
        self.assertEqual(target_north.name, "Goblin")

        # Obstruct Goblin with a wall: should ignore Goblin and fallback to visible Orc
        engine.dungeon.set_tile(5, 3, make_wall())
        target_blocked = engine._find_nearest_monster()
        self.assertEqual(target_blocked.name, "Orc")

    def test_boss_cannot_attack_through_walls(self):
        from pyrogue.tile import make_wall

        engine = GameEngine()
        engine.remaining_dungeons = 0
        engine.descend_stairs()

        boss = next(m for m in engine.dungeon.monsters if m.monster_type == 'boss')
        boss.x, boss.y = 20, 9
        engine.player.x, engine.player.y = 10, 9
        # Place wall between boss and player
        engine.dungeon.set_tile(15, 9, make_wall())

        initial_hp = engine.player.hp
        for _ in range(50):
            engine._update_monster_ai(boss)

        self.assertEqual(engine.player.hp, initial_hp)

if __name__ == '__main__':
    unittest.main()
