import unittest
from pyrogue.entities import Player, create_goblin
from pyrogue.combat import CombatEngine
from pyrogue.tile import make_water, make_spikes, make_fire
from pyrogue.magic import SPELL_HEAL, SPELL_MAGIC_MISSILE

class TestCombat(unittest.TestCase):
    def test_combat_resolution(self):
        combat = CombatEngine()
        player = Player()
        goblin = create_goblin(0, 0)
        
        # Player strikes goblin
        initial_hp = goblin.hp
        combat.player_attack_monster(player, goblin)
        self.assertTrue(goblin.hp < initial_hp)

    def test_traps_and_status(self):
        combat = CombatEngine()
        player = Player()
        
        # Spikes trap
        combat.process_traps_and_status(player, make_spikes())
        self.assertEqual(player.hp, 25)  # 30 - 5
        
        # Fire trap
        combat.process_traps_and_status(player, make_fire())
        self.assertEqual(player.fire_turns, 2)  # 3 turns initialized, 1 turn deducted on step
        
        # Water extinguishes fire
        combat.process_traps_and_status(player, make_water())
        self.assertEqual(player.fire_turns, 0)

    def test_spells(self):
        combat = CombatEngine()
        player = Player()
        player.hp = 10
        combat.cast_spell(SPELL_HEAL, player)
        self.assertTrue(player.hp > 10)
        self.assertEqual(player.mp, 6)  # 10 - 4

    def test_ranged_attack(self):
        from pyrogue.dungeon_map import DungeonMap
        from pyrogue.tile import make_floor, make_wall
        combat = CombatEngine()
        player = Player(x=2, y=2)
        dungeon = DungeonMap(width=10, height=10)
        for y in range(10):
            for x in range(10):
                dungeon.set_tile(x, y, make_floor())

        goblin = create_goblin(5, 2)
        dungeon.monsters.append(goblin)

        initial_charges = player.equipped_ranged.charges
        initial_hp = goblin.hp

        # Fire East (dx=1, dy=0)
        action, monster = combat.player_fire_ranged(player, dungeon, dx=1, dy=0)
        self.assertTrue(action)
        self.assertEqual(monster, goblin)
        self.assertTrue(goblin.hp < initial_hp)
        self.assertEqual(player.equipped_ranged.charges, initial_charges - 1)

    def test_ranged_attack_wall_block(self):
        from pyrogue.dungeon_map import DungeonMap
        from pyrogue.tile import make_floor, make_wall
        combat = CombatEngine()
        player = Player(x=2, y=2)
        dungeon = DungeonMap(width=10, height=10)
        for y in range(10):
            for x in range(10):
                dungeon.set_tile(x, y, make_floor())

        # Place wall at (4, 2) and goblin behind wall at (6, 2)
        dungeon.set_tile(4, 2, make_wall())
        goblin = create_goblin(6, 2)
        dungeon.monsters.append(goblin)

        initial_hp = goblin.hp
        action, monster = combat.player_fire_ranged(player, dungeon, dx=1, dy=0)
        self.assertTrue(action)
        self.assertIsNone(monster)
        self.assertEqual(goblin.hp, initial_hp)

    def test_ranged_no_ammo(self):
        from pyrogue.dungeon_map import DungeonMap
        combat = CombatEngine()
        player = Player(x=2, y=2)
        player.equipped_ranged.charges = 0
        dungeon = DungeonMap(width=10, height=10)

        action, monster = combat.player_fire_ranged(player, dungeon, dx=1, dy=0)
        self.assertFalse(action)
        self.assertIsNone(monster)

if __name__ == '__main__':
    unittest.main()
