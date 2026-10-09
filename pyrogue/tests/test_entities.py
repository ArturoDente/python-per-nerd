import unittest
from pyrogue.entities import Player, create_goblin, create_orc, create_demon, create_boss
from pyrogue.items import Weapon

class TestEntities(unittest.TestCase):
    def test_player_initial_stats(self):
        player = Player()
        self.assertEqual(player.hp, 30)
        self.assertEqual(player.max_hp, 30)
        self.assertEqual(player.mp, 10)
        self.assertEqual(player.max_mp, 10)
        self.assertEqual(player.str_stat, 10)
        self.assertEqual(player.spd, 10)
        self.assertIsNotNone(player.equipped_melee)
        self.assertIsNotNone(player.equipped_ranged)
        self.assertEqual(player.hp_potions, 2)
        self.assertEqual(player.mp_potions, 1)

    def test_player_equip_weapon(self):
        player = Player()
        new_sword = Weapon("Greatsword", "melee", weight=12, min_dmg=8, max_dmg=16)
        old_weapon = player.equip_weapon(new_sword)
        self.assertEqual(player.equipped_melee.name, "Greatsword")
        self.assertIn(old_weapon, player.weapons_bag)

    def test_monster_creation(self):
        goblin = create_goblin(1, 1, depth=1)
        self.assertEqual(goblin.char, 'g')
        self.assertTrue(goblin.spd > 10)

        orc = create_orc(1, 1, depth=1)
        self.assertEqual(orc.char, 'O')
        self.assertTrue(orc.spd < 10)

        demon = create_demon(1, 1, depth=1)
        self.assertEqual(demon.char, 'D')

        boss = create_boss(1, 1)
        self.assertEqual(boss.char, 'B')
        self.assertEqual(boss.hp, 60)

if __name__ == '__main__':
    unittest.main()
