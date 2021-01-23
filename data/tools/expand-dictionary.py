#!/usr/bin/env python3
# encoding: utf-8

import sys, os, re, argparse, string, copy, difflib, time, gzip, codecs
from wesnoth.wmltools3 import *
from wesnoth.wmliterator3 import *
from collections import defaultdict

# Changes meant to be done on maps and .cfg lines.
mapchanges = (
    ("^Voha", "^Voa"),
    ("^Voh",  "^Vo"),
    ("^Vhms", "^Vhha"),
    ("^Vhm",  "^Vhh"),
    ("^Vcha", "^Vca"),
    ("^Vch",  "^Vc"),
    ("^Vcm",  "^Vc"),
    ("Ggf,",  "Gg^Emf"),
    ("Qv,",  "Mv"),
    )

# Base terrain aliasing changes.
aliaschanges = (
    # 1.11.8:
    ("Ch",   "Ct"),
    ("Ds",   "Dt"),
    ("Hh",   "Ht"),
    ("Mm",   "Mt"),
    ("Ss",   "St"),
    ("Uu",   "Ut"),
    ("Ww",   "Wst"),
    ("Wo",   "Wdt"),
    ("Wwr",  "Wrt"),
    ("^Uf",  "Uft"),
    # Vi -> Vit in 1.11.8, Vit -> Vt in 1.11.9.
    ("Vit",  "Vt"),
    # 1.11.9:
    ("Vi",   "Vt"),
    )

# Global changes meant to be done on all lines.  Suppressed by noconvert.
linechanges = (
        ("canrecruit=1", "canrecruit=yes"),
        ("canrecruit=0", "canrecruit=no"),
        # Fix a common typo
        ("agression=", "aggression="),
        # These changed just after 1.5.0
        ("[special_filter]", "[filter_attack]"),
        ("[wml_filter]", "[filter_wml]"),
        ("[unit_filter]", "[filter]"),
        ("[secondary_unit_filter]", "[filter_second]"),
        ("[attack_filter]", "[filter_attack]"),
        ("[secondary_attack_filter]", "[filter_second_attack]"),
        ("[special_filter_second]", "[filter_second_attack]"),
        ("[/special_filter]", "[/filter_attack]"),
        ("[/wml_filter]", "[/filter_wml]"),
        ("[/unit_filter]", "[/filter]"),
        ("[/secondary_unit_filter]", "[/filter_second]"),
        ("[/attack_filter]", "[/filter_attack]"),
        ("[/secondary_attack_filter]", "[/filter_second_attack]"),
        ("[/special_filter_second]", "[/filter_second_attack]"),
        ("grassland=", "flat="),
        ("tundra=", "frozen="),
        ("cavewall=", "impassable="),
        ("canyon=", "unwalkable="),
        # This changed after 1.5.2
        ("advanceto=", "advances_to="),
        # This changed after 1.5.5, to enable mechanical spellchecking
        ("sabre", "saber"),
        ("nr-sad.ogg", "sad.ogg"),
        # Changed after 1.5.7
        ("[debug_message]", "[wml_message]"),
        ("[/debug_message]", "[/wml_message]"),
        # Changed just before 1.5.9
        ("portraits/Alex_Jarocha-Ernst/drake-burner.png",
         "portraits/drakes/burner.png"),
        ("portraits/Alex_Jarocha-Ernst/drake-clasher.png",
         "portraits/drakes/clasher.png"),
        ("portraits/Alex_Jarocha-Ernst/drake-fighter.png",
         "portraits/drakes/fighter.png"),
        ("portraits/Alex_Jarocha-Ernst/drake-glider.png",
         "portraits/drakes/glider.png"),
        ("portraits/Alex_Jarocha-Ernst/ghoul.png",
         "portraits/undead/ghoul.png"),
        ("portraits/Alex_Jarocha-Ernst/mermaid-initiate.png",
         "portraits/merfolk/initiate.png"),
        ("portraits/Alex_Jarocha-Ernst/merman-fighter.png",
         "portraits/merfolk/fighter.png"),
        ("portraits/Alex_Jarocha-Ernst/merman-hunter.png",
         "portraits/merfolk/hunter.png"),
        ("portraits/Alex_Jarocha-Ernst/naga-fighter.png",
         "portraits/nagas/fighter.png"),
        ("portraits/Alex_Jarocha-Ernst/nagini-fighter.png",
         "portraits/nagas/fighter+female.png"),
        ("portraits/Alex_Jarocha-Ernst/orcish-assassin.png",
         "portraits/orcs/assassin.png"),
        ("portraits/Emilien_Rotival/human-general.png",
         "portraits/humans/general.png"),
        ("portraits/Emilien_Rotival/human-heavyinfantry.png",
         "portraits/humans/heavy-infantry.png"),
        ("portraits/Emilien_Rotival/human-ironmauler.png",
         "portraits/humans/iron-mauler.png"),
        ("portraits/Emilien_Rotival/human-lieutenant.png",
         "portraits/humans/lieutenant.png"),
        ("portraits/Emilien_Rotival/human-marshal.png",
         "portraits/humans/marshal.png"),
        ("portraits/Emilien_Rotival/human-peasant.png",
         "portraits/humans/peasant.png"),
        ("portraits/Emilien_Rotival/human-pikeman.png",
         "portraits/humans/pikeman.png"),
        ("portraits/Emilien_Rotival/human-royalguard.png",
         "portraits/humans/royal-guard.png"),
        ("portraits/Emilien_Rotival/human-sergeant.png",
         "portraits/humans/sergeant.png"),
        ("portraits/Emilien_Rotival/human-spearman.png",
         "portraits/humans/spearman.png"),
        ("portraits/Emilien_Rotival/human-swordsman.png",
         "portraits/humans/swordsman.png"),
        ("portraits/Emilien_Rotival/transparent/human-general.png",
         "portraits/humans/transparent/general.png"),
        ("portraits/Emilien_Rotival/transparent/human-heavyinfantry.png",
         "portraits/humans/transparent/heavy-infantry.png"),
        ("portraits/Emilien_Rotival/transparent/human-ironmauler.png",
         "portraits/humans/transparent/iron-mauler.png"),
        ("portraits/Emilien_Rotival/transparent/human-lieutenant.png",
         "portraits/humans/transparent/lieutenant.png"),
        ("portraits/Emilien_Rotival/transparent/human-marshal.png",
         "portraits/humans/transparent/marshal.png"),
        ("portraits/Emilien_Rotival/transparent/human-marshal-2.png",
         "portraits/humans/transparent/marshal-2.png"),
        ("portraits/Emilien_Rotival/transparent/human-peasant.png",
         "portraits/humans/transparent/peasant.png"),
        ("portraits/Emilien_Rotival/transparent/human-pikeman.png",
         "portraits/humans/transparent/pikeman.png"),
        ("portraits/Emilien_Rotival/transparent/human-royalguard.png",
         "portraits/humans/transparent/royal-guard.png"),
        ("portraits/Emilien_Rotival/transparent/human-sergeant.png",
         "portraits/humans/transparent/sergeant.png"),
        ("portraits/Emilien_Rotival/transparent/human-spearman.png",
         "portraits/humans/transparent/spearman.png"),
        ("portraits/Emilien_Rotival/transparent/human-swordsman.png",
         "portraits/humans/transparent/swordsman.png"),
        ("portraits/James_Woo/assassin.png",
         "portraits/humans/assassin.png"),
        ("portraits/James_Woo/dwarf-guard.png",
         "portraits/dwarves/guard.png"),
        ("portraits/James_Woo/orc-warlord.png",
         "portraits/orcs/warlord.png"),
        ("portraits/James_Woo/orc-warlord2.png",
         "portraits/orcs/warlord2.png"),
        ("portraits/James_Woo/orc-warlord3.png",
         "portraits/orcs/warlord3.png"),
        ("portraits/James_Woo/orc-warlord4.png",
         "portraits/orcs/warlord4.png"),
        ("portraits/James_Woo/orc-warlord5.png",
         "portraits/orcs/warlord5.png"),
        ("portraits/James_Woo/troll.png",
         "portraits/trolls/troll.png"),
        ("portraits/Jason_Lutes/human-bandit.png",
         "portraits/humans/bandit.png"),
        ("portraits/Jason_Lutes/human-grand-knight.png",
         "portraits/humans/grand-knight.png"),
        ("portraits/Jason_Lutes/human-halberdier.png",
         "portraits/humans/halberdier.png"),
        ("portraits/Jason_Lutes/human-highwayman.png",
         "portraits/humans/highwayman.png"),
        ("portraits/Jason_Lutes/human-horseman.png",
         "portraits/humans/horseman.png"),
        ("portraits/Jason_Lutes/human-javelineer.png",
         "portraits/humans/javelineer.png"),
        ("portraits/Jason_Lutes/human-knight.png",
         "portraits/humans/knight.png"),
        ("portraits/Jason_Lutes/human-lancer.png",
         "portraits/humans/lancer.png"),
        ("portraits/Jason_Lutes/human-paladin.png",
         "portraits/humans/paladin.png"),
        ("portraits/Jason_Lutes/human-thug.png",
         "portraits/humans/thug.png"),
        ("portraits/Kitty/elvish-archer.png",
         "portraits/elves/archer.png"),
        ("portraits/Kitty/elvish-archer+female.png",
         "portraits/elves/archer+female.png"),
        ("portraits/Kitty/elvish-captain.png",
         "portraits/elves/captain.png"),
        ("portraits/Kitty/elvish-druid.png",
         "portraits/elves/druid.png"),
        ("portraits/Kitty/elvish-fighter.png",
         "portraits/elves/fighter.png"),
        ("portraits/Kitty/elvish-hero.png",
         "portraits/elves/hero.png"),
        ("portraits/Kitty/elvish-high-lord.png",
         "portraits/elves/high-lord.png"),
        ("portraits/Kitty/elvish-lady.png",
         "portraits/elves/lady.png"),
        ("portraits/Kitty/elvish-lord.png",
         "portraits/elves/lord.png"),
        ("portraits/Kitty/elvish-marksman.png",
         "portraits/elves/marksman.png"),
        ("portraits/Kitty/elvish-marksman+female.png",
         "portraits/elves/marksman+female.png"),
        ("portraits/Kitty/elvish-ranger.png",
         "portraits/elves/ranger.png"),
        ("portraits/Kitty/elvish-ranger+female.png",
         "portraits/elves/ranger+female.png"),
        ("portraits/Kitty/elvish-scout.png",
         "portraits/elves/scout.png"),
        ("portraits/Kitty/elvish-shaman.png",
         "portraits/elves/shaman.png"),
        ("portraits/Kitty/elvish-shyde.png",
         "portraits/elves/shyde.png"),
        ("portraits/Kitty/elvish-sorceress.png",
         "portraits/elves/sorceress.png"),
        ("portraits/Kitty/human-dark-adept.png",
         "portraits/humans/dark-adept.png"),
        ("portraits/Kitty/human-dark-adept+female.png",
         "portraits/humans/dark-adept+female.png"),
        ("portraits/Kitty/human-mage.png",
         "portraits/humans/mage.png"),
        ("portraits/Kitty/human-mage+female.png",
         "portraits/humans/mage+female.png"),
        ("portraits/Kitty/human-mage-arch.png",
         "portraits/humans/mage-arch.png"),
        ("portraits/Kitty/human-mage-arch+female.png",
         "portraits/humans/mage-arch+female.png"),
        ("portraits/Kitty/human-mage-light.png",
         "portraits/humans/mage-light.png"),
        ("portraits/Kitty/human-mage-light+female.png",
         "portraits/humans/mage-light+female.png"),
        ("portraits/Kitty/human-mage-red.png",
         "portraits/humans/mage-red.png"),
        ("portraits/Kitty/human-mage-red+female.png",
         "portraits/humans/mage-red+female.png"),
        ("portraits/Kitty/human-mage-silver.png",
         "portraits/humans/mage-silver.png"),
        ("portraits/Kitty/human-mage-silver+female.png",
         "portraits/humans/mage-silver+female.png"),
        ("portraits/Kitty/human-mage-white.png",
         "portraits/humans/mage-white.png"),
        ("portraits/Kitty/human-mage-white+female.png",
         "portraits/humans/mage-white+female.png"),
        ("portraits/Kitty/human-necromancer.png",
         "portraits/humans/necromancer.png"),
        ("portraits/Kitty/human-necromancer+female.png",
         "portraits/humans/necromancer+female.png"),
        ("portraits/Kitty/troll-whelp.png",
         "portraits/trolls/whelp.png"),
        ("portraits/Kitty/undead-lich.png",
         "portraits/undead/lich.png"),
        ("portraits/Kitty/transparent/elvish-archer.png",
         "portraits/elves/transparent/archer.png"),
        ("portraits/Kitty/transparent/elvish-archer+female.png",
         "portraits/elves/transparent/archer+female.png"),
        ("portraits/Kitty/transparent/elvish-captain.png",
         "portraits/elves/transparent/captain.png"),
        ("portraits/Kitty/transparent/elvish-druid.png",
         "portraits/elves/transparent/druid.png"),
        ("portraits/Kitty/transparent/elvish-fighter.png",
         "portraits/elves/transparent/fighter.png"),
        ("portraits/Kitty/transparent/elvish-hero.png",
         "portraits/elves/transparent/hero.png"),
        ("portraits/Kitty/transparent/elvish-high-lord.png",
         "portraits/elves/transparent/high-lord.png"),
        ("portraits/Kitty/transparent/elvish-lady.png",
         "portraits/elves/transparent/lady.png"),
        ("portraits/Kitty/transparent/elvish-lord.png",
         "portraits/elves/transparent/lord.png"),
        ("portraits/Kitty/transparent/elvish-marksman.png",
         "portraits/elves/transparent/marksman.png"),
        ("portraits/Kitty/transparent/elvish-marksman+female.png",
         "portraits/elves/transparent/marksman+female.png"),
        ("portraits/Kitty/transparent/elvish-ranger.png",
         "portraits/elves/transparent/ranger.png"),
        ("portraits/Kitty/transparent/elvish-ranger+female.png",
         "portraits/elves/transparent/ranger+female.png"),
        ("portraits/Kitty/transparent/elvish-scout.png",
         "portraits/elves/transparent/scout.png"),
        ("portraits/Kitty/transparent/elvish-shaman.png",
         "portraits/elves/transparent/shaman.png"),
        ("portraits/Kitty/transparent/elvish-shyde.png",
         "portraits/elves/transparent/shyde.png"),
        ("portraits/Kitty/transparent/elvish-sorceress.png",
         "portraits/elves/transparent/sorceress.png"),
        ("portraits/Kitty/transparent/human-dark-adept.png",
         "portraits/humans/transparent/dark-adept.png"),
        ("portraits/Kitty/transparent/human-dark-adept+female.png",
         "portraits/humans/transparent/dark-adept+female.png"),
        ("portraits/Kitty/transparent/human-mage.png",
         "portraits/humans/transparent/mage.png"),
        ("portraits/Kitty/transparent/human-mage+female.png",
         "portraits/humans/transparent/mage+female.png"),
        ("portraits/Kitty/transparent/human-mage-arch.png",
         "portraits/humans/transparent/mage-arch.png"),
        ("portraits/Kitty/transparent/human-mage-arch+female.png",
         "portraits/humans/transparent/mage-arch+female.png"),
        ("portraits/Kitty/transparent/human-mage-light.png",
         "portraits/humans/transparent/mage-light.png"),
        ("portraits/Kitty/transparent/human-mage-light+female.png",
         "portraits/humans/transparent/mage-light+female.png"),
        ("portraits/Kitty/transparent/human-mage-red.png",
         "portraits/humans/transparent/mage-red.png"),
        ("portraits/Kitty/transparent/human-mage-red+female.png",
         "portraits/humans/transparent/mage-red+female.png"),
        ("portraits/Kitty/transparent/human-mage-silver.png",
         "portraits/humans/transparent/mage-silver.png"),
        ("portraits/Kitty/transparent/human-mage-silver+female.png",
         "portraits/humans/transparent/mage-silver+female.png"),
        ("portraits/Kitty/transparent/human-mage-white.png",
         "portraits/humans/transparent/mage-white.png"),
        ("portraits/Kitty/transparent/human-mage-white+female.png",
         "portraits/humans/transparent/mage-white+female.png"),
        ("portraits/Kitty/transparent/human-necromancer.png",
         "portraits/humans/transparent/necromancer.png"),
        ("portraits/Kitty/transparent/human-necromancer+female.png",
         "portraits/humans/transparent/necromancer+female.png"),
        ("portraits/Kitty/transparent/troll-whelp.png",
         "portraits/trolls/transparent/whelp.png"),
        ("portraits/Kitty/transparent/undead-lich.png",
         "portraits/undead/transparent/lich.png"),
        ("portraits/Nicholas_Kerpan/human-poacher.png",
         "portraits/humans/poacher.png"),
        ("portraits/Nicholas_Kerpan/human-thief.png",
         "portraits/humans/thief.png"),
        ("portraits/Other/brown-lich.png",
         "portraits/undead/brown-lich.png"),
        ("portraits/Other/cavalryman.png",
         "portraits/humans/cavalryman.png"),
        ("portraits/Other/human-masterbowman.png",
         "portraits/humans/master-bowman.png"),
        ("portraits/Other/scorpion.png",
         "portraits/monsters/scorpion.png"),
        ("portraits/Other/sea-serpent.png",
         "portraits/monsters/sea-serpent.png"),
        ("portraits/Pekka_Aikio/human-bowman.png",
         "portraits/humans/bowman.png"),
        ("portraits/Pekka_Aikio/human-longbowman.png",
         "portraits/humans/longbowman.png"),
        ("portraits/Philip_Barber/dwarf-dragonguard.png",
         "portraits/dwarves/dragonguard.png"),
        ("portraits/Philip_Barber/dwarf-fighter.png",
         "portraits/dwarves/fighter.png"),
        ("portraits/Philip_Barber/dwarf-lord.png",
         "portraits/dwarves/lord.png"),
        ("portraits/Philip_Barber/dwarf-thunderer.png",
         "portraits/dwarves/thunderer.png"),
        ("portraits/Philip_Barber/saurian-augur.png",
         "portraits/saurians/augur.png"),
        ("portraits/Philip_Barber/saurian-skirmisher.png",
         "portraits/saurians/skirmisher.png"),
        ("portraits/Philip_Barber/undead-death-knight.png",
         "portraits/undead/death-knight.png"),
        ("portraits/Philip_Barber/transparent/dwarf-dragonguard.png",
         "portraits/dwarves/transparent/dragonguard.png"),
        ("portraits/Philip_Barber/transparent/dwarf-fighter.png",
         "portraits/dwarves/transparent/fighter.png"),
        ("portraits/Philip_Barber/transparent/dwarf-lord.png",
         "portraits/dwarves/transparent/lord.png"),
        ("portraits/Philip_Barber/transparent/dwarf-thunderer.png",
         "portraits/dwarves/transparent/thunderer.png"),
        ("portraits/Philip_Barber/transparent/saurian-augur.png",
         "portraits/saurians/transparent/augur.png"),
        ("portraits/Philip_Barber/transparent/saurian-skirmisher.png",
         "portraits/saurians/transparent/skirmisher.png"),
        ("portraits/Philip_Barber/transparent/undead-death-knight.png",
         "portraits/undead/transparent/death-knight.png"),
        # Changed just before 1.5.11
        ("titlescreen/landscapebattlefield.jpg",
         "story/landscape-battlefield.jpg"),
        ("titlescreen/landscapebridge.jpg",
         "story/landscape-bridge.jpg"),
        ("titlescreen/landscapecastle.jpg",
         "story/landscape-castle.jpg"),
        ("LABEL_PERSISTANT", "LABEL_PERSISTENT"),
        # Changed just before 1.5.13
        ("targetting", "targeting"),
        # Changed just after 1.7 fork
        ("[stone]", "[petrify]"),
        ("[unstone]", "[unpetrify]"),
        ("[/stone]", "[/petrify]"),
        ("[/unstone]", "[/unpetrify]"),
        ("WEAPON_SPECIAL_STONE", "WEAPON_SPECIAL_PETRIFY"),
        ("SPECIAL_NOTE_STONE", "SPECIAL_NOTE_PETRIFY"),
        (".stoned", ".petrified"),
        ("stoned=", "petrified="),
        # Changed at rev 37390
        ("swing=", "value_second="),
        # Changed just before 1.7.3
        ("Drake Gladiator", "Drake Thrasher"),
        ("gladiator-", "thrasher-"),
        ("Drake Slasher", "Drake Arbiter"),
        ("slasher-", "arbiter-"),
        # Changes after 1.7.5
        ("portraits/nagas/fighter+female.png", "portraits/nagas/fighter.png"),
        # Changes after 1.8rc1
        ("portraits/orcs/warlord.png", "portraits/orcs/transparent/warlord.png"),
        #("portraits/orcs/warlord2.png","portraits/orcs/transparent/warlord.png"), // see 1.11.5
        ("portraits/orcs/warlord3.png","portraits/orcs/transparent/grunt-2.png"),
        #("portraits/orcs/warlord4.png","portraits/orcs/transparent/grunt-2.png"), // see 1.11.5
        ("portraits/orcs/warlord5.png","portraits/orcs/transparent/grunt-3.png"),
        # Changes just before 1.9.0
        ("flat/grass-r8", "flat/grass6"),
        ("flat/grass-r7", "flat/grass5"),
        ("flat/grass-r6", "flat/grass6"),
        ("flat/grass-r5", "flat/grass5"),
        ("flat/grass-r4", "flat/grass4"),
        ("flat/grass-r3", "flat/grass3"),
        ("flat/grass-r2", "flat/grass2"),
        ("flat/grass-r1", "flat/grass1"),
        ("second_value=", "value_second="), # Correct earlier wmllint error
        (".stones", ".petrifies"),
        ("stones=", "petrifies="),
        # Changes just before 1.9.1
        ("[colour_adjust]", "[color_adjust]"),
        ("[/colour_adjust]", "[/color_adjust]"),
        ("colour=", "color="),
        ("colour_lock=", "color_lock="),
        # Changes just before 1.9.2
        ("[removeitem]", "[remove_item]"),
        ("[/removeitem]", "[/remove_item]"),
        # Changes just before 1.11.0
        ("viewing_side", "side"),
        ("duration=level", "duration=scenario"), # Note: this may be removed after 1.11.2, so an actual duration=level can be implemented
        # Changed before 1.11.5 to incorporate 1.9.0 portraits
        ("portraits/orcs/warlord2.png","portraits/orcs/transparent/grunt-5.png"),
        ("portraits/orcs/warlord4.png","portraits/orcs/transparent/grunt-6.png"),

        # Changed before 1.11.8
        ("misc/schedule-dawn.png","misc/time-schedules/default/schedule-dawn.png"),
        ("misc/schedule-morning.png","misc/time-schedules/default/schedule-morning.png"),
        ("misc/schedule-afternoon.png","misc/time-schedules/default/schedule-afternoon.png"),
        ("misc/schedule-dusk.png","misc/time-schedules/default/schedule-dusk.png"),
        ("misc/schedule-firstwatch.png","misc/time-schedules/default/schedule-firstwatch.png"),
        ("misc/schedule-secondwatch.png","misc/time-schedules/default/schedule-secondwatch.png"),

        ("misc/schedule-indoors.png","misc/time-schedules/schedule-indoors.png"),
        ("misc/schedule-underground.png","misc/time-schedules/schedule-underground.png"),
        ("misc/schedule-underground-illum.png","misc/time-schedules/schedule-underground-illum.png"),

        ("misc/tod-schedule-24hrs.png","misc/time-schedules/tod-schedule-24hrs.png"),

        # Changed before 1.13.0 to fix frames for ragged flags
        ('FLAG_VARIANT ragged','FLAG_VARIANT6 ragged'),
        ('FLAG_VARIANT "ragged"','FLAG_VARIANT6 ragged'),

        # Changed in 1.11.15.
        ("fight_on_without_leader=yes","defeat_condition=no_units_left"),
        ("fight_on_without_leader=no","defeat_condition=no_leader_left"),
        ("remove_from_carryover_on_leaders_loss=yes","remove_from_carryover_on_defeat=yes"),
        ("remove_from_carryover_on_leaders_loss=no","remove_from_carryover_on_defeat=no"),

        # Changed in 1.13.2.
        ("[advance]","[advancement]"),
        ("[/advance]","[/advancement]"),
        ("{ABILITY_LEADERSHIP_LEVEL_1}", "{ABILITY_LEADERSHIP}"),
        ("{ABILITY_LEADERSHIP_LEVEL_2}", "{ABILITY_LEADERSHIP}"),
        ("{ABILITY_LEADERSHIP_LEVEL_3}", "{ABILITY_LEADERSHIP}"),
        ("{ABILITY_LEADERSHIP_LEVEL_4}", "{ABILITY_LEADERSHIP}"),
        ("{ABILITY_LEADERSHIP_LEVEL_5}", "{ABILITY_LEADERSHIP}"),
        ("misc/icon-amla-tough.png","icons/amla-default.png"),

        # Changed in 1.13.4: removal of small portraits with black background
        ("portraits/drakes/transparent/blademaster.png", "portraits/drakes/blademaster.png"),
        ("portraits/drakes/transparent/burner.png", "portraits/drakes/burner.png"),
        ("portraits/drakes/transparent/clasher.png", "portraits/drakes/clasher.png"),
        ("portraits/drakes/transparent/enforcer.png", "portraits/drakes/enforcer.png"),
        ("portraits/drakes/transparent/fighter.png", "portraits/drakes/fighter.png"),
        ("portraits/drakes/transparent/flameheart.png", "portraits/drakes/flameheart.png"),
        ("portraits/drakes/transparent/glider.png", "portraits/drakes/glider.png"),
        ("portraits/drakes/transparent/hurricane.png", "portraits/drakes/hurricane.png"),
        ("portraits/drakes/transparent/inferno.png", "portraits/drakes/inferno.png"),
        ("portraits/drakes/transparent/warden.png", "portraits/drakes/warden.png"),
        ("portraits/dwarves/transparent/dragonguard.png", "portraits/dwarves/dragonguard.png"),
        ("portraits/dwarves/transparent/explorer.png", "portraits/dwarves/explorer.png"),
        ("portraits/dwarves/transparent/fighter-2.png", "portraits/dwarves/fighter-2.png"),
        ("portraits/dwarves/transparent/fighter.png", "portraits/dwarves/fighter.png"),
        ("portraits/dwarves/transparent/gryphon-rider.png", "portraits/dwarves/gryphon-rider.png"),
        ("portraits/dwarves/transparent/guard.png", "portraits/dwarves/guard.png"),
        ("portraits/dwarves/transparent/lord.png", "portraits/dwarves/lord.png"),
        ("portraits/dwarves/transparent/runemaster.png", "portraits/dwarves/runemaster.png"),
        ("portraits/dwarves/transparent/scout.png", "portraits/dwarves/scout.png"),
        ("portraits/dwarves/transparent/sentinel.png", "portraits/dwarves/sentinel.png"),
        ("portraits/dwarves/transparent/thunderer.png", "portraits/dwarves/thunderer.png"),
        ("portraits/dwarves/transparent/ulfserker.png", "portraits/dwarves/ulfserker.png"),
        ("portraits/elves/transparent/archer+female.png", "portraits/elves/archer+female.png"),
        ("portraits/elves/transparent/archer.png", "portraits/elves/archer.png"),
        ("portraits/elves/transparent/captain.png", "portraits/elves/captain.png"),
        ("portraits/elves/transparent/druid.png", "portraits/elves/druid.png"),
        ("portraits/elves/transparent/fighter.png", "portraits/elves/fighter.png"),
        ("portraits/elves/transparent/hero.png", "portraits/elves/hero.png"),
        ("portraits/elves/transparent/high-lord.png", "portraits/elves/high-lord.png"),
        ("portraits/elves/transparent/lady.png", "portraits/elves/lady.png"),
        ("portraits/elves/transparent/lord.png", "portraits/elves/lord.png"),
        ("portraits/elves/transparent/marksman+female.png", "portraits/elves/marksman+female.png"),
        ("portraits/elves/transparent/marksman.png", "portraits/elves/marksman.png"),
        ("portraits/elves/transparent/ranger+female.png", "portraits/elves/ranger+female.png"),
        ("portraits/elves/transparent/ranger.png", "portraits/elves/ranger.png"),
        ("portraits/elves/transparent/scout.png", "portraits/elves/scout.png"),
        ("portraits/elves/transparent/shaman.png", "portraits/elves/shaman.png"),
        ("portraits/elves/transparent/shyde.png", "portraits/elves/shyde.png"),
        ("portraits/elves/transparent/sorceress.png", "portraits/elves/sorceress.png"),
        ("portraits/elves/transparent/sylph.png", "portraits/elves/sylph.png"),
        ("portraits/goblins/transparent/direwolver.png", "portraits/goblins/direwolver.png"),
        ("portraits/goblins/transparent/impaler.png", "portraits/goblins/impaler.png"),
        ("portraits/goblins/transparent/pillager.png", "portraits/goblins/pillager.png"),
        ("portraits/goblins/transparent/rouser-2.png", "portraits/goblins/rouser-2.png"),
        ("portraits/goblins/transparent/rouser.png", "portraits/goblins/rouser.png"),
        ("portraits/goblins/transparent/spearman-2.png", "portraits/goblins/spearman-2.png"),
        ("portraits/goblins/transparent/spearman.png", "portraits/goblins/spearman.png"),
        ("portraits/goblins/transparent/wolf-rider.png", "portraits/goblins/wolf-rider.png"),
        ("portraits/humans/transparent/assassin+female.png", "portraits/humans/assassin+female.png"),
        ("portraits/humans/transparent/assassin.png", "portraits/humans/assassin.png"),
        ("portraits/humans/transparent/bandit.png", "portraits/humans/bandit.png"),
        ("portraits/humans/transparent/bowman.png", "portraits/humans/bowman.png"),
        ("portraits/humans/transparent/cavalier.png", "portraits/humans/cavalier.png"),
        ("portraits/humans/transparent/cavalryman.png", "portraits/humans/cavalryman.png"),
        ("portraits/humans/transparent/dark-adept+female.png", "portraits/humans/dark-adept+female.png"),
        ("portraits/humans/transparent/dark-adept.png", "portraits/humans/dark-adept.png"),
        ("portraits/humans/transparent/duelist.png", "portraits/humans/duelist.png"),
        ("portraits/humans/transparent/fencer.png", "portraits/humans/fencer.png"),
        ("portraits/humans/transparent/footpad+female.png", "portraits/humans/footpad+female.png"),
        ("portraits/humans/transparent/footpad.png", "portraits/humans/footpad.png"),
        ("portraits/humans/transparent/general.png", "portraits/humans/general.png"),
        ("portraits/humans/transparent/grand-knight-2.png", "portraits/humans/grand-knight-2.png"),
        ("portraits/humans/transparent/grand-knight.png", "portraits/humans/grand-knight.png"),
        ("portraits/humans/transparent/halberdier.png", "portraits/humans/halberdier.png"),
        ("portraits/humans/transparent/heavy-infantry.png", "portraits/humans/heavy-infantry.png"),
        ("portraits/humans/transparent/horseman.png", "portraits/humans/horseman.png"),
        ("portraits/humans/transparent/huntsman.png", "portraits/humans/huntsman.png"),
        ("portraits/humans/transparent/iron-mauler.png", "portraits/humans/iron-mauler.png"),
        ("portraits/humans/transparent/javelineer.png", "portraits/humans/javelineer.png"),
        ("portraits/humans/transparent/knight.png", "portraits/humans/knight.png"),
        ("portraits/humans/transparent/lancer.png", "portraits/humans/lancer.png"),
        ("portraits/humans/transparent/lieutenant.png", "portraits/humans/lieutenant.png"),
        ("portraits/humans/transparent/longbowman.png", "portraits/humans/longbowman.png"),
        ("portraits/humans/transparent/mage-arch+female.png", "portraits/humans/mage-arch+female.png"),
        ("portraits/humans/transparent/mage-arch.png", "portraits/humans/mage-arch.png"),
        ("portraits/humans/transparent/mage+female.png", "portraits/humans/mage+female.png"),
        ("portraits/humans/transparent/mage-light+female.png", "portraits/humans/mage-light+female.png"),
        ("portraits/humans/transparent/mage-light.png", "portraits/humans/mage-light.png"),
        ("portraits/humans/transparent/mage.png", "portraits/humans/mage.png"),
        ("portraits/humans/transparent/mage-red+female.png", "portraits/humans/mage-red+female.png"),
        ("portraits/humans/transparent/mage-red.png", "portraits/humans/mage-red.png"),
        ("portraits/humans/transparent/mage-silver+female.png", "portraits/humans/mage-silver+female.png"),
        ("portraits/humans/transparent/mage-silver.png", "portraits/humans/mage-silver.png"),
        ("portraits/humans/transparent/mage-white+female.png", "portraits/humans/mage-white+female.png"),
        ("portraits/humans/transparent/mage-white.png", "portraits/humans/mage-white.png"),
        ("portraits/humans/transparent/marshal-2.png", "portraits/humans/marshal-2.png"),
        ("portraits/humans/transparent/marshal.png", "portraits/humans/marshal.png"),
        ("portraits/humans/transparent/master-at-arms.png", "portraits/humans/master-at-arms.png"),
        ("portraits/humans/transparent/master-bowman.png", "portraits/humans/master-bowman.png"),
        ("portraits/humans/transparent/necromancer+female.png", "portraits/humans/necromancer+female.png"),
        ("portraits/humans/transparent/necromancer.png", "portraits/humans/necromancer.png"),
        ("portraits/humans/transparent/outlaw+female.png", "portraits/humans/outlaw+female.png"),
        ("portraits/humans/transparent/outlaw.png", "portraits/humans/outlaw.png"),
        ("portraits/humans/transparent/paladin.png", "portraits/humans/paladin.png"),
        ("portraits/humans/transparent/peasant.png", "portraits/humans/peasant.png"),
        ("portraits/humans/transparent/pikeman.png", "portraits/humans/pikeman.png"),
        ("portraits/humans/transparent/ranger.png", "portraits/humans/ranger.png"),
        ("portraits/humans/transparent/royal-guard.png", "portraits/humans/royal-guard.png"),
        ("portraits/humans/transparent/ruffian.png", "portraits/humans/ruffian.png"),
        ("portraits/humans/transparent/sergeant.png", "portraits/humans/sergeant.png"),
        ("portraits/humans/transparent/spearman-2.png", "portraits/humans/spearman-2.png"),
        ("portraits/humans/transparent/spearman.png", "portraits/humans/spearman.png"),
        ("portraits/humans/transparent/swordsman-2.png", "portraits/humans/swordsman-2.png"),
        ("portraits/humans/transparent/swordsman-3.png", "portraits/humans/swordsman-3.png"),
        ("portraits/humans/transparent/swordsman.png", "portraits/humans/swordsman.png"),
        ("portraits/humans/transparent/thief+female.png", "portraits/humans/thief+female.png"),
        ("portraits/humans/transparent/thief.png", "portraits/humans/thief.png"),
        ("portraits/humans/transparent/thug.png", "portraits/humans/thug.png"),
        ("portraits/humans/transparent/trapper.png", "portraits/humans/trapper.png"),
        ("portraits/humans/transparent/woodsman.png", "portraits/humans/woodsman.png"),
        ("portraits/khalifate/transparent/hakim.png", "portraits/khalifate/hakim.png"),
        ("portraits/merfolk/transparent/enchantress.png", "portraits/merfolk/enchantress.png"),
        ("portraits/merfolk/transparent/fighter.png", "portraits/merfolk/fighter.png"),
        ("portraits/merfolk/transparent/hoplite.png", "portraits/merfolk/hoplite.png"),
        ("portraits/merfolk/transparent/hunter.png", "portraits/merfolk/hunter.png"),
        ("portraits/merfolk/transparent/initiate-2.png", "portraits/merfolk/initiate-2.png"),
        ("portraits/merfolk/transparent/initiate.png", "portraits/merfolk/initiate.png"),
        ("portraits/merfolk/transparent/netcaster.png", "portraits/merfolk/netcaster.png"),
        ("portraits/merfolk/transparent/priestess.png", "portraits/merfolk/priestess.png"),
        ("portraits/merfolk/transparent/spearman.png", "portraits/merfolk/spearman.png"),
        ("portraits/merfolk/transparent/triton.png", "portraits/merfolk/triton.png"),
        ("portraits/monsters/transparent/bat.png", "portraits/monsters/bat.png"),
        ("portraits/monsters/transparent/deep-tentacle.png", "portraits/monsters/deep-tentacle.png"),
        ("portraits/monsters/transparent/giant-mudcrawler.png", "portraits/monsters/giant-mudcrawler.png"),
        ("portraits/monsters/transparent/gryphon.png", "portraits/monsters/gryphon.png"),
        ("portraits/monsters/transparent/ogre.png", "portraits/monsters/ogre.png"),
        ("portraits/monsters/transparent/scorpion.png", "portraits/monsters/scorpion.png"),
        ("portraits/monsters/transparent/sea-serpent.png", "portraits/monsters/sea-serpent.png"),
        ("portraits/monsters/transparent/yeti.png", "portraits/monsters/yeti.png"),
        ("portraits/monsters/transparent/young-ogre.png", "portraits/monsters/young-ogre.png"),
        ("portraits/nagas/transparent/fighter.png", "portraits/nagas/fighter.png"),
        ("portraits/nagas/transparent/myrmidon.png", "portraits/nagas/myrmidon.png"),
        ("portraits/orcs/transparent/archer.png", "portraits/orcs/archer.png"),
        ("portraits/orcs/transparent/assassin.png", "portraits/orcs/assassin.png"),
        ("portraits/orcs/transparent/crossbowman.png", "portraits/orcs/crossbowman.png"),
        ("portraits/orcs/transparent/grunt-2.png", "portraits/orcs/grunt-2.png"),
        ("portraits/orcs/transparent/grunt-3.png", "portraits/orcs/grunt-3.png"),
        ("portraits/orcs/transparent/grunt-4.png", "portraits/orcs/grunt-4.png"),
        ("portraits/orcs/transparent/grunt-5.png", "portraits/orcs/grunt-5.png"),
        ("portraits/orcs/transparent/grunt-6.png", "portraits/orcs/grunt-6.png"),
        ("portraits/orcs/transparent/grunt.png", "portraits/orcs/grunt.png"),
        ("portraits/orcs/transparent/leader-2.png", "portraits/orcs/ruler-2.png"),
        ("portraits/orcs/transparent/leader.png", "portraits/orcs/ruler.png"),
        ("portraits/orcs/transparent/slayer.png", "portraits/orcs/slayer.png"),
        ("portraits/orcs/transparent/slurbow.png", "portraits/orcs/slurbow.png"),
        ("portraits/orcs/transparent/sovereign.png", "portraits/orcs/sovereign.png"),
        ("portraits/orcs/transparent/warlord.png", "portraits/orcs/warlord.png"),
        ("portraits/orcs/transparent/warrior.png", "portraits/orcs/warrior.png"),
        ("portraits/saurians/transparent/augur.png", "portraits/saurians/augur.png"),
        ("portraits/saurians/transparent/skirmisher.png", "portraits/saurians/skirmisher.png"),
        ("portraits/trolls/transparent/troll-hero-alt.png", "portraits/trolls/troll-hero-alt.png"),
        ("portraits/trolls/transparent/troll-hero.png", "portraits/trolls/troll-hero.png"),
        ("portraits/trolls/transparent/troll.png", "portraits/trolls/troll.png"),
        ("portraits/trolls/transparent/troll-rocklobber.png", "portraits/trolls/troll-rocklobber.png"),
        ("portraits/trolls/transparent/troll-shaman.png", "portraits/trolls/troll-shaman.png"),
        ("portraits/trolls/transparent/troll-warrior.png", "portraits/trolls/troll-warrior.png"),
        ("portraits/trolls/transparent/whelp.png", "portraits/trolls/whelp.png"),
        ("portraits/undead/transparent/ancient-lich.png", "portraits/undead/ancient-lich.png"),
        ("portraits/undead/transparent/archer.png", "portraits/undead/archer.png"),
        ("portraits/undead/transparent/banebow.png", "portraits/undead/banebow.png"),
        ("portraits/undead/transparent/bone-shooter.png", "portraits/undead/bone-shooter.png"),
        ("portraits/undead/transparent/brown-lich.png", "portraits/undead/brown-lich.png"),
        ("portraits/undead/transparent/deathblade.png", "portraits/undead/deathblade.png"),
        ("portraits/undead/transparent/death-knight.png", "portraits/undead/death-knight.png"),
        ("portraits/undead/transparent/draug-2.png", "portraits/undead/draug-2.png"),
        ("portraits/undead/transparent/draug.png", "portraits/undead/draug.png"),
        ("portraits/undead/transparent/ghost.png", "portraits/undead/ghost.png"),
        ("portraits/undead/transparent/ghoul.png", "portraits/undead/ghoul.png"),
        ("portraits/undead/transparent/lich.png", "portraits/undead/lich.png"),
        ("portraits/undead/transparent/nightgaunt.png", "portraits/undead/nightgaunt.png"),
        ("portraits/undead/transparent/revenant.png", "portraits/undead/revenant.png"),
        ("portraits/undead/transparent/shadow.png", "portraits/undead/shadow.png"),
        ("portraits/undead/transparent/skeleton.png", "portraits/undead/skeleton.png"),
        ("portraits/undead/transparent/soulless.png", "portraits/undead/soulless.png"),
        ("portraits/undead/transparent/spectre.png", "portraits/undead/spectre.png"),
        ("portraits/undead/transparent/walking-corpse.png", "portraits/undead/walking-corpse.png"),
        ("portraits/undead/transparent/wraith.png", "portraits/undead/wraith.png"),
        ("portraits/woses/transparent/ancient-wose.png", "portraits/woses/ancient-wose.png"),
        ("portraits/woses/transparent/wose.png", "portraits/woses/wose.png"),

        # Consistency change for the Heavy Infantryman idle frames
        ("units/human-loyalists/heavy-infantry-idle-1.png", "units/human-loyalists/heavyinfantry-idle-1.png"),
        ("units/human-loyalists/heavy-infantry-idle-2.png", "units/human-loyalists/heavyinfantry-idle-2.png"),
        ("units/human-loyalists/heavy-infantry-idle-3.png", "units/human-loyalists/heavyinfantry-idle-3.png"),
        ("units/human-loyalists/heavy-infantry-idle-4.png", "units/human-loyalists/heavyinfantry-idle-4.png"),
        ("units/human-loyalists/heavy-infantry-idle-5.png", "units/human-loyalists/heavyinfantry-idle-5.png"),
        ("units/human-loyalists/heavy-infantry-idle-6.png", "units/human-loyalists/heavyinfantry-idle-6.png"),
        ("units/human-loyalists/heavy-infantry-idle-7.png", "units/human-loyalists/heavyinfantry-idle-7.png"),
        ("units/human-loyalists/heavy-infantry-idle-8.png", "units/human-loyalists/heavyinfantry-idle-8.png"),
        ("units/human-loyalists/heavy-infantry-idle-9.png", "units/human-loyalists/heavyinfantry-idle-9.png"),

        # renamed khalifate to dunefolk
        ("id=khalifate", "id=dunefolk"),
        ("movement_type=khalifatefoot", "movement_type=dunefoot"),
        ("movement_type=khalifatearmoredfoot", "movement_type=dunearmoredfoot"),
        ("movement_type=khalifatehorse", "movement_type=dunehorse"),
        ("movement_type=khalifatearmoredhorse", "movement_type=dunearmoredhorse"),
        ("race=khalifate", "race=dunefolk"),
        ("{KHALIFATE_NAMES}", "{DUNEFOLK_NAMES}"),
        ("portraits/khalifate/hakim.png", "portraits/dunefolk/hakim.png"),
        ("units/khalifate/arif.png", "units/dunefolk/arif.png"),
        ("units/khalifate/batal.png", "units/dunefolk/batal.png"),
        ("units/khalifate/elder-falcon.png", "units/dunefolk/elder-falcon.png"),
        ("units/khalifate/elder-falcon.png", "units/dunefolk/elder-falcon.png"),
        ("units/khalifate/faris.png", "units/dunefolk/faris.png"),
        ("units/khalifate/ghazi.png", "units/dunefolk/ghazi.png"),
        ("units/khalifate/hadaf.png", "units/dunefolk/hadaf.png"),
        ("units/khalifate/hakim.png", "units/dunefolk/hakim.png"),
        ("units/khalifate/jawal.png", "units/dunefolk/jawal.png"),
        ("units/khalifate/jundi.png", "units/dunefolk/jundi.png"),
        ("units/khalifate/khaiyal.png", "units/dunefolk/khaiyal.png"),
        ("units/khalifate/khalid.png", "units/dunefolk/khalid.png"),
        ("units/khalifate/mighwar.png", "units/dunefolk/mighwar.png"),
        ("units/khalifate/monawish.png", "units/dunefolk/monawish.png"),
        ("units/khalifate/mudafi.png", "units/dunefolk/mudafi.png"),
        ("units/khalifate/mufariq.png", "units/dunefolk/mufariq.png"),
        ("units/khalifate/muharib.png", "units/dunefolk/muharib.png"),
        ("units/khalifate/naffat.png", "units/dunefolk/naffat.png"),
        ("units/khalifate/qanas.png", "units/dunefolk/qanas.png"),
        ("units/khalifate/qatif-al-nar.png", "units/dunefolk/qatif-al-nar.png"),
        ("units/khalifate/rami.png", "units/dunefolk/rami.png"),
        ("units/khalifate/rasikh.png", "units/dunefolk/rasikh.png"),
        ("units/khalifate/saree.png", "units/dunefolk/saree.png"),
        ("units/khalifate/shuja.png", "units/dunefolk/shuja.png"),
        ("units/khalifate/tabib.png", "units/dunefolk/tabib.png"),
        ("units/khalifate/tineen.png", "units/dunefolk/tineen.png"),
        ("era_khalifate", "era_dunefolk"),
        ("era_khalifate_heroes", "era_dunefolk_heroes"),

        # renamed dunefolk units
        # images
        ("units/dunefolk/arif.png", "units/dunefolk/soldier.png"),
        ("units/dunefolk/batal.png", "units/dunefolk/wayfarer.png"),
        ("units/dunefolk/faris.png", "units/dunefolk/sunderer.png"),
        ("units/dunefolk/ghazi.png", "units/dunefolk/swordsman.png"),
        ("units/dunefolk/hadaf.png", "units/dunefolk/marauder.png"),
        ("units/dunefolk/hakim.png", "units/dunefolk/herbalist.png"),
        ("units/dunefolk/jawal.png", "units/dunefolk/windbolt.png"),
        ("units/dunefolk/jundi.png", "units/dunefolk/rover.png"),
        ("units/dunefolk/khaiyal.png", "units/dunefolk/piercer.png"),
        ("units/dunefolk/khalid.png", "units/dunefolk/warmaster.png"),
        ("units/dunefolk/mighwar.png", "units/dunefolk/harrier.png"),
        ("units/dunefolk/monawish.png", "units/dunefolk/skirmisher.png"),
        ("units/dunefolk/mudafi.png", "units/dunefolk/spearguard.png"),
        ("units/dunefolk/mufariq.png", "units/dunefolk/cataphract.png"),
        ("units/dunefolk/muharib.png", "units/dunefolk/explorer.png"),
        ("units/dunefolk/naffat.png", "units/dunefolk/burner.png"),
        ("units/dunefolk/qanas.png", "units/dunefolk/raider.png"),
        ("units/dunefolk/qatif-al-nar.png", "units/dunefolk/scorcher.png"),
        ("units/dunefolk/rami.png", "units/dunefolk/rider.png"),
        ("units/dunefolk/rasikh.png", "units/dunefolk/spearmaster.png"),
        ("units/dunefolk/saree.png", "units/dunefolk/horse-archer.png"),
        ("units/dunefolk/shuja.png", "units/dunefolk/blademaster.png"),
        ("units/dunefolk/tabib.png", "units/dunefolk/apothecary.png"),
        ("units/dunefolk/tineen.png", "units/dunefolk/firetrooper.png"),
        ("images/portraits/dunefolk/hakim.png", "images/portraits/dunefolk/herbalist.png"),

        # second round of renaming
        ("units/dunefolk/ranger.png", "units/dunefolk/wayfarer.png"),
        ("units/dunefolk/windrider.png", "units/dunefolk/windbolt.png"),
        ("units/dunefolk/swiftrider.png", "units/dunefolk/horse-archer.png"),
        ("units/nagas/slasher.png", "units/nagas/dirkfang.png"),
        ("units/nagas/bladewhirler.png", "units/nagas/ophidian.png"),

        # unit ids
        ("Arif", "Dune Soldier"),
        ("Ghazi", "Dune Swordsman"),
        ("Shuja", "Dune Blademaster"),
        ("Khalid", "Dune Paragon"),
        ("Mudafi", "Dune Spearguard"),
        ("Rasikh", "Dune Spearmaster"),
        ("Hakim", "Dune Herbalist"),
        ("Tabib", "Dune Apothecary"),
        ("Jundi", "Dune Rover"),
        ("Monawish", "Dune Strider"),
        ("Mighwar", "Dune Harrier"),
        ("Muharib", "Dune Explorer"),
        ("Batal", "Dune Wayfarer"),
        ("Khaiyal", "Dune Rider"),
        ("Faris", "Dune Sunderer"),
        ("Mufariq", "Dune Cataphract"),
        ("Qanas", "Dune Raider"),
        ("Hadaf", "Dune Marauder"),
        ("Naffat", "Dune Burner"),
        ("Qatif-al-nar", "Dune Scorcher"),
        ("Qatif_al_nar", "Dune Scorcher"),
        ("Tineen", "Dune Firetrooper"),
        ("Rami", "Dune Rider"),
        ("Saree", "Dune Horse Archer"),
        ("Jawal", "Dune Windbolt"),

        # second round of renaming
        ("Dune Ranger", "Dune Wayfarer"),
        ("Dune Swiftrider", "Dune Horse Archer"),
        ("Dune Windrider", "Dune Windbolt"),
        ("Dune Piercer", "Dune Rider"),
        ("Naga Slasher", "Naga Dirkfang"),
        ("Naga Bladewhirler", "Naga Ophidian"),

        # Changed in 1.15.0: separate portrait for leader
        ("portraits/orcs/leader.png", "portraits/orcs/ruler.png"),
        ("portraits/orcs/leader-2.png", "portraits/orcs/ruler-2.png")

        )

# helper function to reduce code duplication and allow easy checking
# of amendment tags ([+tag] syntax)

def has_opening_tag(line, tag):
    """Check whether a line contains an opening tag or the corresponding
amendment tag, internally using string concatenation. Returns a boolean."""
    return (("[" + tag + "]") in line) or (("[+" + tag + "]") in line)

def validate_on_pop(tagstack, closer, filename, lineno):
    "Validate the stack at the time a new close tag is seen."
    (tag, attributes, subtags) = tagstack[-1]
    # append the closer to the subtags of the parent tag
    # don't do it if we're closing a root tag
    if len(tagstack) > 1:
        tagstack[-2][2].append(closer)
    ancestors = [x[0] for x in tagstack]
    if verbose >= 3:
        print('"%s", line %d: closing %s I see %s with %s' % (filename, lineno, closer, tag, attributes))
    # Detect a malformation that will cause the game to barf while attempting
    # to deserialize an empty unit.  The final "and attributes" is a blatant
    # hack; some campaigns like to generate entire side declarations with
    # macros.
    if "scenario" in ancestors and closer == "side" and "type" not in attributes and \
       ("no_leader" not in attributes or attributes["no_leader"] != "yes") and \
       attributes.get("controller") != "null" and \
       "multiplayer" not in ancestors and "leader" not in subtags and attributes:
        print('"%s", line %d: [side] without type attribute' % (filename, lineno))
    # This assumes that conversion will always happen in units/ files.
    if "units" not in filename and closer == "unit" and "race" in attributes:
        print('"%s", line %d: [unit] needs hand fixup to [unit_type]' % \
              (filename, lineno))
    if closer in ["campaign", "race"] and "id" not in attributes:
        print('"%s", line %d: %s requires an ID attribute but has none' % \
              (filename, lineno, closer))
    if closer == "terrain" and attributes.get("heals") in ("true", "false"):
        print('"%s", line %d: heals attribute no longer takes a boolean' % \
              (filename, lineno))
    if closer == "unit" and attributes.get("id") is not None and attributes.get("type") is not None and attributes.get("side") is None and not "side" in ancestors:
        print('"%s", line %d: unit declaration without side attribute' % \
              (filename, lineno))
    if closer == "theme" and "id" not in attributes:
        if "name" in attributes:
            print('"%s", line %d: using [theme]name= instead of [theme]id= is deprecated' % (filename, lineno))
        else:
            print('"%s", line %d: [theme] needs an id attribute' % (filename, lineno))
    # Check for user-visible themes that lack a UI name or description.
    if closer == "theme" and ("hidden" not in attributes or attributes["hidden"] not in ("yes", "true")):
        for attr in ("name", "description"):
            if attr not in attributes:
                print('"%s", line %d: [theme] needs a %s attribute unless hidden=yes' % \
                      (filename, lineno, attr))
    if closer == "filter_side":
        ancestor = False
        if "gold" in ancestors:
            ancestor = "gold"
        elif "modify_ai" in ancestors:
            ancestor = "modify_ai"
        if ancestor:
            print('"%s", line %d: %s should have an inline SSF instead of using [filter_side]' % \
                  (filename, lineno, ancestor))
    if closer == "effect":
        if attributes.get("unit_type") is not None:
            print('"%s", line %d: use [effect][filter]type= instead of [effect]unit_type=' % \
                  (filename, lineno))
        if attributes.get("unit_gender") is not None:
            print('"%s", line %d: use [effect][filter]gender= instead of [effect]unit_gender=' % \
                  (filename, lineno))
    if missingside and closer in ["set_recruit", "allow_recruit", "disallow_recruit", "store_gold"] and "side" not in attributes:
        print('"%s", line %d: %s without "side" attribute is now applied to all sides' % \
              (filename, lineno, closer))
    if closer == "variation" and "variation_id" not in attributes:
        print('"%s", line %d: [variation] is missing required variation_id attribute' % \
              (filename, lineno))

def within(tag):
    "Did the specified tag lead one of our enclosing contexts?"
    if type(tag) == type(()): # Can take a list.
        for t in tag:
            if within(t):
                return True
        else:
            return False
    else:
        return tag in [x[0] for x in tagstack]

def under(tag):
    "Did the specified tag lead the latest context?"
    if type(tag) == type(()): # Can take a list.
        for t in tag:
            if within(t):
                return True
        else:
            return False
    elif tagstack:
        return tag == tagstack[-1][0]
    else:
        return False

def standard_unit_filter():
    "Are we within the syntactic context of a standard unit filter?"
    # It's under("message") rather than within("message") because
    # [message] can contain [option] markup with menu item description=
    # attributes that should not be altered.
    return within(("filter", "filter_second",
                   "filter_adjacent", "filter_opponent",
                   "unit_filter", "secondary_unit_filter",
                   "special_filter", "special_filter_second",
                   "neighbor_unit_filter",
                   "recall", "teleport", "kill", "unstone", "store_unit",
                   "have_unit", "scroll_to_unit", "role",
                   "hide_unit", "unhide_unit",
                   "protect_unit", "target", "avoid")) \
                   or under("message")

# Sanity checking

# Associations for the ability sanity checks.
# Please note that a special note can be associated with multiple abilities
# but any given ability can be associated with only one special note
# Some notes are handled directly in the global_sanity_check() function
notepairs = [
    ("{ABILITY_HEALS}", "{NOTE_HEALS}"),
    ("{ABILITY_EXTRA_HEAL}", "{NOTE_EXTRA_HEAL}"),
    ("{ABILITY_UNPOISON}", "{NOTE_UNPOISON}"),
    ("{ABILITY_CURES}", "{NOTE_CURES}"),
    ("{ABILITY_REGENERATES}", "{NOTE_REGENERATES}"),
    ("{ABILITY_SELF_HEAL}", "{NOTE_SELF_HEAL}"),
    ("{ABILITY_STEADFAST}", "{NOTE_STEADFAST}"),
    ("{ABILITY_LEADERSHIP}", "{NOTE_LEADERSHIP}"),
    ("{ABILITY_SKIRMISHER}", "{NOTE_SKIRMISHER}"),
    ("{ABILITY_ILLUMINATES}", "{NOTE_ILLUMINATES}"),
    ("{ABILITY_TELEPORT}", "{NOTE_TELEPORT}"),
    ("{ABILITY_AMBUSH}", "{NOTE_AMBUSH}"),
    ("{ABILITY_NIGHTSTALK}", "{NOTE_NIGHTSTALK}"),
    ("{ABILITY_CONCEALMENT}", "{NOTE_CONCEALMENT}"),
    ("{ABILITY_SUBMERGE}", "{NOTE_SUBMERGE}"),
    ("{ABILITY_FEEDING}", "{NOTE_FEEDING}"),
    ("{ABILITY_INSPIRE}", "{NOTE_INSPIRE}"),
    ("{ABILITY_INITIATIVE}", "{NOTE_INITIATIVE}"),
    ("{ABILITY_DISTRACT}", "{NOTE_DISTRACT}"),
    ("{ABILITY_DISENGAGE}", "{NOTE_DISENGAGE}"),
    ("{ABILITY_FORMATION}", "{NOTE_FORMATION}"),
    ("{WEAPON_SPECIAL_BERSERK}", "{NOTE_BERSERK}"),
    ("{WEAPON_SPECIAL_BACKSTAB}", "{NOTE_BACKSTAB}"),
    ("{WEAPON_SPECIAL_PLAGUE", "{NOTE_PLAGUE}"), # No } deliberately
    ("{WEAPON_SPECIAL_SLOW}", "{NOTE_SLOW}"),
    ("{WEAPON_SPECIAL_PETRIFY}", "{NOTE_PETRIFY}"),
    ("{WEAPON_SPECIAL_MARKSMAN}", "{NOTE_MARKSMAN}"),
    ("{WEAPON_SPECIAL_MAGICAL}", "{NOTE_MAGICAL}"),
    ("{WEAPON_SPECIAL_SWARM}", "{NOTE_SWARM}"),
    ("{WEAPON_SPECIAL_CHARGE}", "{NOTE_CHARGE}"),
    ("{WEAPON_SPECIAL_DRAIN}", "{NOTE_DRAIN}"),
    ("{WEAPON_SPECIAL_FIRSTSTRIKE}", "{NOTE_FIRSTSTRIKE}"),
    ("{WEAPON_SPECIAL_POISON}", "{NOTE_POISON}"),
    ("{WEAPON_SPECIAL_STUN}", "{NOTE_STUN}"),
    ("{WEAPON_SPECIAL_SHOCK}", "{NOTE_SHOCK}"),
    ("{WEAPON_SPECIAL_DAZE}", "{NOTE_DAZE}"),
    ]

# This dictionary will pair macros with the characters they recall or create,
# but must be populated by the magic comment, "#wmllint: who ... is ...".
whopairs = {}

# This dictionary pairs macros with the id field of the characters they recall
# or create, and is populated by the comment, "wmllint: whofield <macro> <#>."
whomacros = {}

# This dictionary pairs the ids of stored units with their variable name.
storedids = {}

# This list of the standard recruitable usage types can be appended with the
# magic comment, "#wmllint: usagetype[s]".
usage_types = ["scout", "fighter", "mixed fighter", "archer", "healer"]

# Since 1.13, UMC authors can define their own conditional tags in Lua
# This list can be populated by using the magic comment
# # wmllint: conditional tag <tag_name>
# It will be then used by local_sanity_check()
custom_conditionals = []

# These are accumulated by sanity_check() and examined by consistency_check()
unit_types = []
derived_units = []
usage = {}
sides = []
advances = []
movetypes = []
unit_movetypes = []
races = []
unit_races = []
nextrefs = []
scenario_to_filename = {}

# Attributes that should have translation marks
def is_translatable(key):
    translatables = (
        "abbrev", "base_names", "cannot_use_message", "caption", "current_player",
        "currently_doing_description", "description", "description_inactive",
        "editor_name", "end_text", "difficulty_descriptions", "female_message",
        "female_name_inactive", "female_names", "female_text", "help_text",
        "help_topic_text", "label", "male_message", "male_names", "male_text",
        "message", "name", "name_inactive", "new_game_title", "note",
        "option_description", "option_name", "order", "plural_name", "prefix",
        "reason", "set_description", "source", "story", "summary", "victory_string",
        "defeat_string", "gold_carryover_string", "notes_string", "text", "title",
        "title2", "tooltip", "translator_comment", "user_team_name", "side_name"
        )
    return key in translatables or (key.startswith(("type_", "range_")) and key != "type_adv_tree")

# This is a list of mainline campaigns, used to convert UMC from
# "data/campaigns" to "data/add-ons" while not clobbering mainline.
mainline = ("An_Orcish_Incursion",
            "Dead_Water",
            "Delfadors_Memoirs",
            "Descent_Into_Darkness",
            "Eastern_Invasion",
            "Heir_To_The_Throne",
            "Legend_of_Wesmere",
            "Liberty",
            "Northern_Rebirth",
            "Sceptre_of_Fire",
            "Secrets_of_the_Ancients",
            "Son_Of_The_Black_Eye",
            "The_Hammer_of_Thursagan",
            "The_Rise_Of_Wesnoth",
            "The_South_Guard",
            "tutorial",
            "Two_Brothers",
            "Under_the_Burning_Suns",
            )

spellcheck_these = (\
    "cannot_use_message=",
    "caption=",
    "description=",
    "description_inactive=",
    "editor_name=",
    "end_text=",
    "help_topic_text=",
    "message=",
    "note=",
    "story=",
    "summary=",
    "text=",
    "title=",
    "title2=",
    "tooltip=",
    "user_team_name=",
    )

# Declare a few common English contractions and ejaculations that pyenchant
# inexplicably knows nothing of.
declared_spellings = {"GLOBAL":["I'm", "I've", "I'd", "I'll",
                                "heh", "ack", "advisor", "learnt", "amidst",
                                # Fantasy/SF/occult jargon that we need
                                "aerie",
                                "aeon",
                                "aide-de-camp",
                                "axe",
                                "ballista",
                                "bided",
                                "crafters",
                                "glaive",
                                "glyphs",
                                "greatsword",
                                "hells",
                                "hellspawn",
                                "hurrah",
                                "morningstar",
                                "newfound",
                                "numbskulls",
                                "overmatched",
                                "sorceries",
                                "spearman",
                                "stygian",
                                "teleport",
                                "teleportation",
                                "teleported",
                                "terraform",
                                "unavenged",
                                "wildlands",
                                # game jargon
                                "melee", "arcane", "day/night", "gameplay",
                                "hitpoint", "hitpoints", "FFA", "multiplayer",
                                "playtesting", "respawn", "respawns",
                                "WML", "HP", "XP", "AI", "ZOC", "YW",
                                "L0", "L1", "L2", "L3", "MC",
                                # archaisms
                                "faugh", "hewn", "leapt", "dreamt", "spilt",
                                "grandmam", "grandsire", "grandsires",
                                "scry", "scrying", "scryed", "woodscraft",
                                "princeling", "wilderlands", "ensorcels",
                                "unlooked", "naphtha", "naïve", "onwards",
                                # Sceptre of Fire gets spelled with -re.
                                "sceptre",
                                ]}

pango_conversions = (("~", "<b>", "</b>"),
                     ("@", "<span color='green'>", "</span>"),
                     ("#", "<span color='red'>", "</span>"),
                     ("*", "<span size='large'>", "</span>"),
                     ("`", "<span size='small'>", "</span>"),
                     )

def pangostrip(message):
    "Strip Pango markup out of a string."
    # This is all known Pango convenience tags
    for tag in ("b", "big", "i", "s", "sub", "sup", "small", "tt", "u"):
        message = message.replace("<%s>" % tag, "").replace("</%s>" % tag, "")
    # Now remove general span tags
    message = re.sub("</?span[^>]*>", "", message)
    # And Pango specials;
    message = re.sub("&[a-z]+;", "", message)
    return message

def pangoize(message, filename, line):
    "Pango conversion of old-style Wesnoth markup."
    if '&' in message:
        amper = message.find('&')
        if message[amper:amper+1].isspace():
            message = message[:amper] + "&amp;" + message[amper+1:]
    rgb = re.search("(?:<|&lt;)([0-9]+),([0-9]+),([0-9]+)(?:>|&gt;)", message)
    if rgb:
        r, g, b = (min(255, int(c)) for c in rgb.groups())
        hexed = '%02x%02x%02x' % (r, g, b)
        print('"%s", line %d: color spec (%s) requires manual fix (<span color=\'#%s\'>, </span>).' % (filename, line, rgb.group(), hexed))
    # Hack old-style Wesnoth markup
    for (oldstyle, newstart, newend) in pango_conversions:
        if oldstyle not in message:
            continue
        where = message.find(oldstyle)
        if message[where - 1] != '"': # Start of string only
            continue
        if message.strip()[-1] != '"':
            print('"%s", line %d: %s highlight at start of multiline string requires manual fix.' % (filename, line, oldstyle))
            continue
        if '+' in message:
            print('"%s", line %d: %s highlight in composite string requires manual fix.' % (filename, line, oldstyle))
            continue
        # This is the common, simple case we can fix automatically
        message = message[:where] + newstart + message[where + 1:]
        endq = message.rfind('"')
        message = message[:endq] + newend + message[endq:]
    # Check for unescaped < and >
    if "<" in message or ">" in message:
        reduced = pangostrip(message)
        if "<" in reduced or ">" in reduced:
            if message == reduced: # No pango markup
                here = message.find('<')
                if message[here:here+4] != "&lt;":
                    message = message[:here] + "&lt;" + message[here+1:]
                here = message.find('>')
                if message[here:here+4] != "&gt;":
                    message = message[:here] + "&gt;" + message[here+1:]
            else:
                print('"%s", line %d: < or > in pango string requires manual fix.' % (filename, line))
    return message

class WmllintIterator(WmlIterator):
    "Fold an Emacs-compatible error reporter into WmlIterator."
    def printError(self, *misc):
        """Emit an error locator compatible with Emacs compilation mode."""
        if not hasattr(self, 'lineno') or self.lineno == -1:
            print('"%s":' % self.fname, file=sys.stderr)
        else:
            print('"%s", line %d:' % (self.fname, self.lineno+1), end=" ", file=sys.stderr)
        for item in misc:
            print(item, end=" ", file=sys.stderr)
        print("", file=sys.stderr) #terminate line

def local_sanity_check(filename, nav, key, prefix, value, comment):
    "Sanity checks that don't require file context or globals."
    errlead = '"%s", line %d: ' %  (filename, nav.lineno+1)
    ancestors = nav.ancestors()
    in_definition = "#define" in ancestors
    in_call = [x for x in ancestors if x.startswith("{")]
    ignored = "wmllint: ignore" in nav.text
    parent = None
    if ancestors:
        parent = ancestors[-1]
        ancestors = ancestors[:-1]
    # Magic comment for adding custom conditional tags
    # Placed here rather than in global_sanity_check(), because
    # local_sanity_check() is used first
    # Do not use square braces while listing the new tags
    # they'll be automatically added by the code below
    # this is done to prevent possible interactions with other parts of the code
    m = re.search("# *wmllint: conditional tag +(.*)", nav.text)
    if m:
        for new_conditional in m.group(1).split(","):
            custom_conditionals.append("[" + new_conditional.strip() + "]")
    # Check for things marked translated that aren't strings or name generators
    if "_" in nav.text and not ignored:
        m = re.search(r'[=(]\s*_\s+("|<<)?', nav.text)
        if m and not m.group(1):
            print(errlead + 'translatability mark before non-string')
    # Most tags are not allowed with [part]
    if ("[part]" in ancestors or parent == "[part]") and isOpener(nav.element):
        # FIXME: this should be part of wmliterator's functionality
        if isExtender(nav.element):
            actual_tag = "[" + nav.element[2:]
        else:
            actual_tag = nav.element
        if actual_tag not in ("[part]", "[background_layer]", "[image]", "[insert_tag]",
                              "[if]", "[then]", "[elseif]", "[else]", "[switch]", "[case]",
                              "[variable]", "[deprecated_message]", "[wml_message]"):
            print(errlead + '%s not permitted within [part] tag' % nav.element)
    # Most tags are not permitted inside [if]
    if (len(ancestors) >= 1 and parent == "[if]") or \
       (len(ancestors) >= 2 and parent == "#ifdef" and ancestors[-1] == "[if]"):
        if isOpener(nav.element) and nav.element not in ("[and]",
                           "[else]", "[elseif]", "[frame]", "[have_location]",
                           "[have_unit]", "[not]", "[or]", "[then]", "[lua]",
                           "[variable]", "[true]", "[false]", "[found_item]",
                           "[proceed_to_next_scenario]") \
                           and not nav.element.endswith("_frame]") \
                           and not nav.element.startswith("[filter") and \
                           nav.element not in custom_conditionals:
            print(errlead + 'illegal child of [if]:', nav.element)
    # Check for fluky credit parts
    if parent == "[entry]":
        if key == "email" and " " in value:
            print(errlead + 'space in email name')
    # Check for various things that shouldn't be outside an [ai] tag
    if not in_definition and not in_call and "[ai]" not in nav.ancestors() and not ignored:
        if key in ("number_of_possible_recruits_to_force_recruit",
                   "recruitment_ignore_bad_movement",
                   "recruitment_ignore_bad_combat",
                   "recruitment_pattern",
                   "villages_per_scout", "leader_value", "village_value",
                   "aggression", "caution", "attack_depth", "grouping", "advancements"):
            print(errlead + key + " outside [ai] scope")
    # Bad [recruit] attribute
    if parent in ("[allow_recruit]", "[disallow_recruit]") and key == "recruit":
        print(errlead + "recruit= should be type=")
    # Check [binary_path] and [textdomain] paths
    if parent == '[textdomain]' and key == 'path' and '/translations' not in value:
        print(errlead + 'no reference to "/translations" directory in textdomain path')
    if parent == '[binary_path]' and key == 'path':
        if '/external' in value or '/public' in value:
            print(errlead + '"/external" or "/public" image directories should no longer be used')
    # Accumulate data to check for missing next scenarios
    if parent == '[campaign]':
        if key == "first_scenario" and value != "null":
            nextrefs.append((filename, nav.lineno, value))
    if parent == '[scenario]' or parent == None:
        if key == "next_scenario" and value != "null":
            nextrefs.append((filename, nav.lineno, value))
        if key == 'id':
            scenario_to_filename[value] = filename

def global_sanity_check_events(filename, lines):
    """Part of global_sanity_check which finds each [event] tag.

    To handle nested events, this is an multi-pass implementation. This
    function will make one complete pass itself. Each subfunction called is
    given its own copy of the iterator, to do its own pass on the contents of
    the event without changing the iterator for this function.
    """
    deathcheck = True
    for nav in WmllintIterator(lines, filename):
        if "wmllint: deathcheck off" in nav.text:
            deathcheck = False
        elif "wmllint: deathcheck on" in nav.text:
            deathcheck = True
        # Now the tests. These run even when the opening tag is on a line which
        # turns that specific check off, in case the check is re-enabled before
        # the closing tag.
        if "[event]" in nav.text:
            sanity_check_speaks_in_death_event(nav.copy(), deathcheck)

def sanity_check_speaks_in_death_event(opening_tag, deathcheck):
    """Detect units that speak in their death events

    Given an iterator pointing to an [event]'s opening tag, check whether it's
    a die event, and if so check whether the already-dead unit speaks during
    it.

    This will move the iterator that is passed into it, the caller should make
    a copy if required.

    opening_tag -- an iterator on the [event] tag's line
    deathcheck -- the status of the global "deathcheck on/off" flag at
    the start of this event
    """
    filter_subject = None
    die_event = False
    if not opening_tag.hasNext():
        # Either this is an empty tag, or the closing tag must be
        # missing. There will be a separate error reported for that.
        return
    opening_tag.__next__()
    event_scope = opening_tag.iterScope()
    base_depth = len(event_scope.ancestors())

    # First pass - find out if the event is a death event, and if it has a
    # filter. Here the base_depth is used to ignore nested events and other
    # tags that have a [filter] subtag.
    for nav in event_scope.copy():
        ancestors = nav.ancestors()
        if len(ancestors) == base_depth + 1:
            fields = parse_attribute(nav.text)
            if fields:
                (key, prefix, value, comment) = fields
                if key == 'name' and value == 'die':
                    die_event = True
        if len(ancestors) == base_depth + 2:
            if ancestors[-1] == "[filter]":
                fields = parse_attribute(nav.text)
                if fields:
                    (key, prefix, value, comment) = fields
                    if key == 'id':
                        filter_subject = value

    # Second pass - check if the subject speaks in this event. This will
    # descend in to nested events, but as the unit is already dead it shouldn't
    # speak in those either.
    if die_event and filter_subject:
        for nav in event_scope:
            if "wmllint: deathcheck off" in nav.text:
                deathcheck = False
                continue
            elif "wmllint: deathcheck on" in nav.text:
                deathcheck = True
            parent = nav.ancestors()[-1]
            if parent == "[message]":
                # Who is speaking?
                fields = parse_attribute(nav.text)
                if fields:
                    (key, prefix, value, comment) = fields
                    if key in ("id", "speaker"):
                        if deathcheck and ((value == filter_subject) or (value == "unit")):
                            print('"%s", line %d: %s speaks in his/her "die" event rather than "last breath"' \
                                  % (nav.fname, nav.lineno+1, value))

def global_sanity_check(filename, lines):
    "Perform sanity and consistency checks on input files."
    # Sanity-check abilities and traits against notes macros.
    # Note: This check is disabled on units derived via [base_unit].
    # Also, build dictionaries of unit movement types and races
    in_unit_type = None
    notecheck = True
    trait_note = dict(notepairs)
    # it's possible that a note might be associated with two abilities
    # use a multimap-like data structure for this reason
    note_trait = defaultdict(list) # {p[1]:p[0] for p in notepairs}
    for pair in notepairs:
        note_trait[pair[1]].append(pair[0])
    unit_id = ""
    base_unit = ""
    for nav in WmllintIterator(lines, filename):
        if "wmllint: notecheck off" in nav.text:
            notecheck = False
            continue
        elif "wmllint: notecheck on" in nav.text:
            notecheck = True
        #print("Element = %s, text = %s" % (nav.element, repr(nav.text)))
        if nav.element == "[unit_type]":
            unit_race = ""
            unit_id = ""
            base_unit = ""
            traits = []
            notes = []
            has_special_notes = False
            in_unit_type = nav.lineno + 1
            hitpoints_specified = False
            unit_usage = ""
            temp_movetypes = []
            temp_races = []
            temp_advances = []
            arcane_note_needed = False
            spirit_note_needed = False
            defense_cap_note_needed = False
            continue
        elif nav.element == "[/unit_type]":
            #print('"%s", %d: unit has traits %s and notes %s' \
            #      % (filename, in_unit_type, traits, notes))
            if unit_id and unit_usage:
                usage[unit_id] = unit_usage
            if unit_id and temp_movetypes:
                for movetype in temp_movetypes:
                    # movetype, race and advance are 3-element tuples, expand them
                    unit_movetypes.append((unit_id, *movetype))
            if unit_id and temp_races:
                for race in temp_races:
                    unit_races.append((unit_id, *race))
            if unit_id and temp_advances:
                for advance in temp_advances:
                    advances.append((unit_id, *advance)) 
            if unit_id and base_unit:
                derived_units.append((filename, nav.lineno + 1, unit_id, base_unit))
            if unit_id and not base_unit:
                missing_notes = []
                if arcane_note_needed and "{NOTE_ARCANE}" not in notes:
                    missing_notes.append("{NOTE_ARCANE}")
                if spirit_note_needed and "{NOTE_SPIRIT}" not in notes:
                    missing_notes.append("{NOTE_SPIRIT}")
                if defense_cap_note_needed and "{NOTE_DEFENSE_CAP}" not in notes:
                    missing_notes.append("{NOTE_DEFENSE_CAP}")
                for trait in traits:
                    tn = trait_note[trait]
                    if tn not in notes and tn not in missing_notes:
                        missing_notes.append(tn)
                missing_traits = []
                if (not arcane_note_needed) and "{NOTE_ARCANE}" in notes:
                    missing_traits.append("type=arcane")
                if (not spirit_note_needed) and "{NOTE_SPIRIT}" in notes:
                    missing_traits.append("movement_type=undeadspirit")
                if (not defense_cap_note_needed) and "{NOTE_DEFENSE_CAP}" in notes:
                    missing_traits.append("movement_type=mounted or [defense] tag")
                for note in notes:
                    for nt in note_trait[note]: # defaultdict makes nt a list, not a string!
                        if nt in traits:
                            break
                    else: # this is done only if there isn't at least one trait matching the note
                        for nt in note_trait[note]:
                            if nt not in missing_traits:
                                missing_traits.append(nt)
                # If the unit didn't specify hitpoints, there is some wacky
                # stuff going on (possibly pseudo-[base_unit] behavior via
                # macro generation) so disable some of the consistency checks.
                if not hitpoints_specified:
                    continue
                if notecheck and missing_notes:
                    print('"%s", line %d: unit %s is missing notes %s' \
                          % (filename, in_unit_type, unit_id, " ".join(missing_notes)))
                if missing_traits:
                    print('"%s", line %d: unit %s is missing traits %s' \
                          % (filename, in_unit_type, unit_id, " ".join(missing_traits)))
                if notecheck and not (notes or traits) and has_special_notes:
                    print('"%s", line %d: unit %s has superfluous {NOTE_*}' \
                         % (filename, in_unit_type, unit_id))
                if "[theme]" not in nav.ancestors() and "[base_unit]" not in nav.ancestors() and not unit_race:
                    print('"%s", line %d: unit %s has no race' \
                         % (filename, in_unit_type, unit_id))
            in_unit_type = None
            traits = []
            notes = []
            unit_id = ""
            base_unit = ""
            has_special_notes = False
            unit_race = None
            unit_usage = ""
            temp_movetypes = []
            temp_races = []
            temp_advances = []
            arcane_note_needed = False
            spirit_note_needed = False
            defense_cap_note_needed = False
        # the glob pattern matches any WML tag starting with filter, including [filter] itself
        if '[unit_type]' in nav.ancestors() and not nav.glob_ancestors("[[]filter*[]]"):
            try:
                (key, prefix, value, comment) = parse_attribute(nav.text)
                if key == "id":
                    if value[0] == "_":
                        value = value[1:].strip()
                    if not unit_id and "[base_unit]" not in nav.ancestors():
                        unit_id = value
                        unit_types.append(unit_id)
                    if not base_unit and "[base_unit]" in nav.ancestors():
                        base_unit = value
                elif key == "hitpoints":
                    hitpoints_specified = True
                elif key == "usage":
                    unit_usage = value
                elif key == "movement_type":
                    if '{' not in value:
                        temp_movetypes.append((filename, nav.lineno + 1, value))
                    if value == "undeadspirit":
                        spirit_note_needed = True
                    elif value == "mounted":
                        defense_cap_note_needed = True
                elif key == "race":
                    if '{' not in value:
                        unit_race = value
                        temp_races.append((filename, nav.lineno + 1, unit_race))
                elif key == "advances_to":
                    advancements = value
                    if advancements.strip() != "null":
                        temp_advances.append((filename, nav.lineno + 1, advancements))
                elif key == "type" and value == "arcane" and "[attack]" in nav.ancestors():
                    arcane_note_needed = True
                elif "[defense]" in nav.ancestors() and re.match(r"\-\d+",value):
                    defense_cap_note_needed = True
            except TypeError:
                pass
            precomment = nav.text
            if '#' in nav.text:
                precomment = nav.text[:nav.text.find("#")]
            if "{NOTE" in precomment:
                has_special_notes = True
            # these special cases are handled better outside of notepairs
            for note in ("{NOTE_DEFENSE_CAP}","{NOTE_SPIRIT}","{NOTE_ARCANE}"):
                if note in precomment:
                    notes.append(note)
            for (p, q) in notepairs:
                if p in precomment:
                    traits.append(p)
                if q in precomment:
                    notes.append(q)

    # Sanity-check all the [event] tags
    global_sanity_check_events(filename, lines)

    # Collect information on defined movement types and races
    for nav in WmllintIterator(lines, filename):
        above = nav.ancestors()
        if above and above[-1] in ("[movetype]", "[race]"):
            try:
                (key, prefix, value, comment) = parse_attribute(nav.text)
                if above[-1] == "[movetype]" and key == 'name':
                    movetypes.append(value)
                if above[-1] == "[race]" and key == 'id':
                    races.append(value)
            except TypeError:
                pass
    # Sanity-check recruit and recruitment_pattern.
    # This code has a limitation; if there are multiple instances of
    # recruit and recruitment_pattern (as can happen if these lists
    # vary by EASY/NORMAL/HARD level) this code will only record the
    # last of each for later consistency checking.
    in_side = False
    in_ai = in_subunit = False
    recruit = {}
    in_generator = False
    sidecount = 0
    recruitment_pattern = {}
    ifdef_stack = [None]
    for num, line in enumerate((l.strip() for l in lines), start=1):
        if line.startswith("#ifdef") or line.startswith("#ifhave") or line.startswith("#ifver"):
            ifdef_stack.append(line.split()[1])
            continue
        if line.startswith("#ifndef") or line.startswith("#ifnhave") or line.startswith("#ifnver"):
            ifdef_stack.append("!" + line.split()[1])
            continue
        if line.startswith("#else"):
            if ifdef_stack[-1].startswith("!"):
                ifdef_stack.append(ifdef_stack[-1][1:])
            else:
                ifdef_stack.append("!" + ifdef_stack[-1])
            continue
        if line.startswith("#endif"):
            ifdef_stack.pop()
            continue
        precomment = line.split("#")[0]
        if "[generator]" in precomment:
            in_generator = True
            continue
        elif "[/generator]" in precomment:
            in_generator = False
            continue
        # do not use has_opening_tag() here, otherwise a [+side] tag
        # will make the sidecount variable incorrect
        elif "[side]" in precomment:
            in_side = True
            sidecount += 1
            continue
        elif "[/side]" in precomment:
            if recruit or recruitment_pattern:
                sides.append((filename, recruit, recruitment_pattern))
            in_side = False
            recruit = {}
            recruitment_pattern = {}
            continue
        elif in_side and has_opening_tag(precomment, "ai"):
            in_ai = True
            continue
        elif in_side and has_opening_tag(precomment, "unit"):
            in_subunit = True
            continue
        elif in_side and "[/ai]" in precomment:
            in_ai = False
            continue
        elif in_side and "[/unit]" in precomment:
            in_subunit = False
            continue
        if "wmllint: skip-side" in line:
            sidecount += 1
        if not in_side or in_subunit or '=' not in precomment:
            continue
        try:
            (key, prefix, value, comment) = parse_attribute(line)
            if key in ("recruit", "extra_recruit") and value:
                recruit[ifdef_stack[-1]] = (num, [x.strip() for x in value.split(",")])
            elif key == "recruitment_pattern" and value:
                if not in_ai:
                    print('"%s", line %d: recruitment_pattern outside [ai]' \
                              % (filename, num))
                else:
                    recruitment_pattern[ifdef_stack[-1]] = (num, [x.strip() for x in value.split(",")])
            elif key == "side" and in_side and not in_ai:
                try:
                    if not in_generator and sidecount != int(value):
                        print('"%s", line %d: side number %s is out of sequence (%d expected)' \
                              % (filename, num, value, sidecount))
                except ValueError:
                    pass # Ignore ill-formed integer literals
        except TypeError:
            pass
    # Sanity check ellipses
    # Starting from 1.11.5, units with canrecruit=yes gain automatically a leader ellipse
    # Starting from 1.11.6, units without a ZoC gain automatically a nozoc ellipse
    # Check if ellipse= was used and warn if so
    # Do not warn if misc/ellipse-hero was used, since it isn't automatically assigned by C++
    # and it's assigned/removed with IS_HERO/MAKE_HERO/UNMAKE_HERO
    # magic comment wmllint: no ellipsecheck deactivates this check for the current line
    in_effect = False
    in_unit = False
    in_side = False
    in_unit_type = False
    for num, line in enumerate(lines, start=1):
        if has_opening_tag(line, "effect"):
            in_effect = True
        elif "[/effect]" in line:
            in_effect = False
        elif has_opening_tag(line, "unit"):
            in_unit = True
        elif "[/unit]" in line:
            in_unit = False
        elif has_opening_tag(line, "side"):
            in_side = True
        elif "[/side]" in line:
            in_side = False
        elif has_opening_tag(line, "unit_type"):
            in_unit_type = True
        elif "[/unit_type]" in line:
            in_unit_type = False
        # ellipsecheck magic comment allows to deactivate the ellipse sanity check
        if "wmllint: no ellipsecheck" not in line:
            if in_effect:
                try:
                    (key, prefix, value, comment) = parse_attribute(line)
                    if key == "ellipse" and value in ("misc/ellipse-nozoc", "misc/ellipse-leader"):
                        print('"%s", line %d: [effect] apply_to=ellipse needs to be removed' % (filename, num))
                    elif key == "ellipse" and value not in ("none", "misc/ellipse", "misc/ellipse-hero"):
                        print('"%s", line %d: custom ellipse %s may need to be updated' % (filename, num, value))
                except TypeError: # this is needed to handle tags, that parse_attribute cannot split
                    pass
            elif in_unit or in_side or in_unit_type:
                try:
                    (key, prefix, value, comment) = parse_attribute(line)
                    if key == "ellipse" and value in ("misc/ellipse-nozoc","misc/ellipse-leader"):
                        print('"%s", line %d: %s=%s needs to be removed' % (filename, num, key, value))
                    elif key == "ellipse" and value not in ("none","misc/ellipse","misc/ellipse-hero"):
                        print('"%s", line %d: custom ellipse %s may need to be updated' % (filename, num, value))
                except TypeError: # this is needed to handle tags, that parse_attribute cannot split
                    pass
    # Handle [advancefrom] deprecation
    # it should be replaced with [modify_unit_type]
    # but, unlike the former tag, the new one goes in the _main.cfg, even as a macro call
    # Because we can't be sure about what the UMC author wants to do, just warn
    in_campaign = False
    for num, line in enumerate(lines, start=1):
        precomment = line.split("#")[0]
        if "[campaign]" in precomment:
            in_campaign = True
            continue
        if "[/campaign]" in precomment:
            in_campaign = False
            continue
        if has_opening_tag(precomment, "advancefrom"):
            print("{}, line {}: [advancefrom] needs to be manually updated to \
[modify_unit_type] and moved into the _main.cfg file".format(filename, num))
        if in_campaign:
            try:
                (key, prefix, value, comment) = parse_attribute(line)
                if key == "extra_defines":
                    print("{}, line {}: extra_defines are now macros and need \
to be called on their own".format(filename, num))
            except TypeError:
                pass
    # Interpret various magic comments
    for line in lines:
        # Interpret magic comments for setting the usage pattern of units.
        # This coped with some wacky UtBS units that were defined with
        # variant-spawning macros.  The prototype comment looks like this:
        #wmllint: usage of "Desert Fighter" is fighter
        m = re.search('# *wmllint: usage of "([^"]*)" is +(.*)', line)
        if m:
            usage[m.group(1)] = m.group(2).strip()
            unit_types.append(m.group(1))
        # Magic comment for adding non-standard usage types
        m = re.search('# *wmllint: usagetypes? +(.*)', line)
        if m:
            for newusage in m.group(1).split(","):
                usage_types.append(newusage.strip())
        # Accumulate global spelling exceptions
        words = re.search("wmllint: general spellings? (.*)", line)
        if words:
            for word in words.group(1).split():
                declared_spellings["GLOBAL"].append(word.lower())
        words = re.search("wmllint: directory spellings? (.*)", line)
        if words:
            fdir = os.path.dirname(filename)
            if fdir not in declared_spellings:
                declared_spellings[fdir] = []
            for word in words.group(1).split():
                declared_spellings[fdir].append(word.lower())
    # Consistency-check the id= attributes in [side], [unit], [recall],
    # and [message] scopes, also correctness-check translation marks and look
    # for double spaces at end of sentence.
    present = []
    in_scenario = False
    in_multiplayer = False
    subtag_depth = 0
    in_person = False
    in_trait = False
    ignore_id = False
    in_object = False
    in_stage = False
    in_cfg = False
    in_goal = False
    in_set_menu_item = False
    in_clear_menu_item = False
    in_aspect = False
    in_facet = False
    in_sound_source = False
    in_remove_sound_source = False
    in_load_resource = False
    in_message = False
    in_option = False
    #last index is true: we're currently directly in an [event]
    #this avoids complaints about unknown [event]id=something, but keeps the check
    #in case some [filter]id= comes in this [event]
    directly_in_event = []
    in_time_area = False
    in_store = False
    in_unstore = False
    in_not = False
    in_clear = False
    in_fire_event = False
    in_primary_unit = False
    in_secondary_unit = False
    in_remove_event = False
    in_remove_time_area = False
    in_tunnel = False
    in_filter = False
    in_checkbox = False
    in_combo = False
    in_entry = False
    in_slider = False
    in_map_generator = False
    in_name_generator = False
    in_candidate_action = False
    storeid = None
    storevar = None
    ignoreable = False
    preamble_seen = False
    sentence_end = re.compile("(?<=[.!?;:])  +")
    capitalization_error = re.compile("(?<=[.!?])  +[a-z]")
    markcheck = True
    translation_mark = re.compile(r'_ *"')
    name_generator_re = re.compile(r"name_generator\s*=\s*_\s*<<")
    for i in range(len(lines)):
        if '[' in lines[i]:
            preamble_seen = True
        # This logic looks odd because a scenario can be conditionally
        # wrapped in both [scenario] and [multiplayer]; we mustn't count
        # either as a subtag even if it occurs inside the other, otherwise
        # this code might see id= declarations as being at the wrong depth.
        if "[scenario]" in lines[i]:
            in_scenario = True
            preamble_seen = False
        elif "[/scenario]" in lines[i]:
            in_scenario = False
        elif "[multiplayer]" in lines[i]:
            in_multiplayer = True
            preamble_seen = False
        elif "[/multiplayer]" in lines[i]:
            in_multiplayer = False
        else:
            # the + check is needed for augmentation tags
            # otherwise subtag_depth may become negative
            if re.search(r"\[\+?[a-z]", lines[i]):
                subtag_depth += 1
            if "[/" in lines[i]:
                subtag_depth -= 1
        if has_opening_tag(lines[i], "event"):
            directly_in_event.append(True)
        elif re.search(r"\[\+?[a-z]", lines[i]):
            directly_in_event.append(False)
        elif "[/" in lines[i]:
            if len(directly_in_event) > 0:
                directly_in_event.pop()
        # Ordinary subtag flags begin here
        if has_opening_tag(lines[i], "trait"):
            in_trait = True
        elif "[/trait]" in lines[i]:
            in_trait = False
        elif has_opening_tag(lines[i], "object"):
            in_object = True
        elif "[/object]" in lines[i]:
            in_object = False
        elif has_opening_tag(lines[i], "stage"):
            in_stage = True
        elif "[/stage]" in lines[i]:
            in_stage = False
        elif has_opening_tag(lines[i], "cfg"):
            in_cfg = True
        elif "[/cfg]" in lines[i]:
            in_cfg = False
        elif has_opening_tag(lines[i], "goal"):
            in_goal = True
        elif "[/goal]" in lines[i]:
            in_goal = False
        elif has_opening_tag(lines[i], "set_menu_item"):
            in_set_menu_item = True
        elif "[/set_menu_item]" in lines[i]:
            in_set_menu_item = False
        elif has_opening_tag(lines[i], "clear_menu_item"):
            in_clear_menu_item = True
        elif "[/clear_menu_item]" in lines[i]:
            in_clear_menu_item = False
        elif has_opening_tag(lines[i], "aspect"):
            in_aspect = True
        elif "[/aspect]" in lines[i]:
            in_aspect = False
        elif has_opening_tag(lines[i], "facet"):
            in_facet = True
        elif "[/facet]" in lines[i]:
            in_facet = False
        elif has_opening_tag(lines[i], "sound_source"):
            in_sound_source = True
        elif "[/sound_source]" in lines[i]:
            in_sound_source = False
        elif has_opening_tag(lines[i], "remove_sound_source"):
            in_remove_sound_source = True
        elif "[/remove_sound_source]" in lines[i]:
            in_remove_sound_source = False
        elif has_opening_tag(lines[i], "load_resource"):
            in_load_resource = True
        elif "[/load_resource]" in lines[i]:
            in_load_resource = False
        elif has_opening_tag(lines[i], "message"):
            in_message = True
        elif "[/message]" in lines[i]:
            in_message = False
        elif has_opening_tag(lines[i], "option"):
            in_option = True
        elif "[/option]" in lines[i]:
            in_option = False
        elif has_opening_tag(lines[i], "time_area"):
            in_time_area = True
        elif "[/time_area]" in lines[i]:
            in_time_area = False
        elif has_opening_tag(lines[i], "label") or \
             has_opening_tag(lines[i], "chamber") or \
             has_opening_tag(lines[i], "time"):
            ignore_id = True
        elif "[/label]" in lines[i] or "[/chamber]" in lines[i] or "[/time]" in lines[i]:
            ignore_id = False
        elif has_opening_tag(lines[i], "kill") or \
             has_opening_tag(lines[i], "effect") or \
             has_opening_tag(lines[i], "move_unit_fake") or \
             has_opening_tag(lines[i], "scroll_to_unit"):
            ignoreable = True
        elif "[/kill]" in lines[i] or "[/effect]" in lines[i] or "[/move_unit_fake]" in lines[i] or "[/scroll_to_unit]" in lines[i]:
            ignoreable = False
        elif has_opening_tag(lines[i], "side") or \
             has_opening_tag(lines[i], "unit") or \
             has_opening_tag(lines[i], "recall"):
            in_person = True
            continue
        elif "[/side]" in lines[i] or "[/unit]" in lines[i] or "[/recall]" in lines[i]:
            in_person = False
        elif has_opening_tag(lines[i], "store_unit"):
            in_store = True
        elif "[/store_unit]" in lines[i]:
            if storeid and storevar:
                storedids.update({storevar: storeid})
            in_store = False
            storeid = storevar = None
        elif has_opening_tag(lines[i], "unstore_unit"):
            in_unstore = True
        elif "[/unstore_unit]" in lines[i]:
            in_unstore = False
        elif has_opening_tag(lines[i], "not"):
            in_not = True
        elif "[/not]" in lines[i]:
            in_not = False
        elif has_opening_tag(lines[i], "clear_variable"):
            in_clear = True
        elif "[/clear_variable]" in lines[i]:
            in_clear = False
        # starting from 1.13.6, [fire_event] supports id= fields
        # ignore them, but don't ignore [primary_unit] and [secondary_unit]
        elif has_opening_tag(lines[i], "fire_event"):
            in_fire_event = True
        elif "[/fire_event]" in lines[i]:
            in_fire_event = False
        elif has_opening_tag(lines[i], "primary_unit"):
            in_primary_unit = True
        elif "[/primary_unit]" in lines[i]:
            in_primary_unit = False
        elif has_opening_tag(lines[i], "secondary_unit"):
            in_secondary_unit = True
        elif "[/secondary_unit]" in lines[i]:
            in_secondary_unit = False
        # version 1.13.0 added [remove_event], which accepts a id= field
        elif has_opening_tag(lines[i], "remove_event"):
            in_remove_event = True
        elif "[/remove_event]" in lines[i]:
            in_remove_event = False
        elif "[remove_time_area]" in lines[i]:
            in_remove_time_area = True
        elif "[/remove_time_area]" in lines[i]:
            in_remove_time_area = False
        # [tunnel] supports a [filter] sub-tag, so handle it
        elif has_opening_tag(lines[i], "tunnel"):
            in_tunnel = True
        elif "[/tunnel]" in lines[i]:
            in_tunnel = False
        elif has_opening_tag(lines[i], "filter"):
            in_filter = True
        elif "[/filter]" in lines[i]:
            in_filter = False
        # sub-tags of [options] tag
        elif has_opening_tag(lines[i], "checkbox"):
            in_checkbox = True
        elif "[/checkbox]" in lines[i]:
            in_checkbox = False
        elif has_opening_tag(lines[i], "combo"):
            in_combo = True
        elif "[/combo]" in lines[i]:
            in_combo = False
        elif has_opening_tag(lines[i], "entry"):
            in_entry = True
        elif "[/entry]" in lines[i]:
            in_entry = False
        elif has_opening_tag(lines[i], "slider"):
            in_slider = True
        elif "[/slider]" in lines[i]:
            in_slider = False
        elif has_opening_tag(lines[i], "generator"):
            in_map_generator = True
        elif "[/generator]" in lines[i]:
            in_map_generator = False
        elif has_opening_tag(lines[i], "candidate_action"):
            in_candidate_action = True
        elif "[/candidate_action]" in lines[i]:
            in_candidate_action = False
        elif name_generator_re.search(lines[i]):
            in_name_generator = True
        elif in_name_generator and ">>" in lines[i]:
            in_name_generator = False
        if "wmllint: markcheck off" in lines[i]:
            markcheck = False
        elif "wmllint: markcheck on" in lines[i]:
            markcheck = True
        elif 'wmllint: who ' in lines[i]:
            try:
                fields = lines[i].split("wmllint: who ", 1)[1].split(" is ", 1)
                if len(fields) == 2:
                    mac = string_strip(fields[0].strip()).strip('{}')
                    if mac in whopairs:
                        whopairs[mac] = whopairs[mac] + ", " + fields[1].strip()
                    else:
                        whopairs.update({mac: fields[1].strip()})
            except IndexError:
                pass
        elif 'wmllint: unwho ' in lines[i]:
            unmac = lines[i].split("wmllint: unwho ", 1)[1].strip()
            if string_strip(unmac).upper() == 'ALL':
                whopairs.clear()
            else:
                try:
                    del whopairs[string_strip(unmac).strip('{}')]
                except KeyError:
                    print('%s, line %s: magic comment "unwho %s" does not match any current keys: %s' \
                          % (filename, i+1, unmac, ", ".join(whopairs.keys())), file=sys.stderr)
        elif 'wmllint: whofield' in lines[i]:
            fields = re.search(r'wmllint: whofield\s+([^\s]+)(\s+is)?\s*([^\s]*)', lines[i])
            if fields:
                if fields.group(1).startswith('clear'):
                    if fields.group(3) in whomacros:
                        del whomacros[fields.group(3)]
                    else:
                        whomacros.clear()
                elif re.match(r'[1-9][0-9]*$', fields.group(3)):
                    whomacros.update({fields.group(1): int(fields.group(3))})
                else:
                    try:
                        del whomacros[fields.group(1)]
                    except KeyError:
                        print('%s, line %s: magic comment "whofield %s" should be followed by a number: %s' \
                              % (filename, i+1, unmac, fields.group(3)), file=sys.stderr)
        # Parse recruit/recall macros to recognize characters.  This section
        # assumes that such a macro is the first item on a line.
        leadmac = re.match(r'{[^}\s]+.', lines[i].lstrip())
        if leadmac:
            macname = leadmac.group()[1:-1]
            # Recognize macro pairings from "wmllint: who" magic
            # comments.
            if macname in whopairs:
                for who in whopairs[macname].split(","):
                    if who.strip().startswith("--"):
                        try:
                            present.remove(who.replace('--', '', 1).strip())
                        except:
                            ValueError
                    else:
                        present.append(who.strip())
            elif not leadmac.group().endswith('}'):
                # Update 1.4's {LOYAL_UNIT} macro to {NAMED_LOYAL_UNIT}.  Do
                # this here rather than hack_syntax so the character can be
                # recognized.
                if macname == 'LOYAL_UNIT':
                    (args, optional_args, brack, paren) = parse_macroref(0, leadmac.string)
                    if len(args) == 7:
                        lines[i] = lines[i].replace('{LOYAL_UNIT', '{NAMED_LOYAL_UNIT', 1)
                # Auto-recognize the people in the {NAMED_*UNIT} macros.
                if re.match(r'NAMED_[A-Z_]*UNIT$', macname):
                    (args, optional_args, brack, paren) = parse_macroref(0, leadmac.string)
                    if len(args) >= 7 and \
                       re.match(r'([0-9]+|[^\s]*\$[^\s]*side[^\s]*|{[^\s]*SIDE[^\s]*})$', args[1]) and \
                       re.match(r'([0-9]+|[^\s]*\$[^\s]*x[^\s]*|{[^\s]*X[^\s]*})$', args[3]) and \
                       re.match(r'([0-9]+|[^\s]*\$[^\s]*y[^\s]*|{[^\s]*Y[^\s]*})$', args[4]) and \
                       len(args[5]) > 0:
                        present.append(args[5])
                elif macname == 'RECALL':
                    (args, optional_args, brack, paren) = parse_macroref(0, leadmac.string)
                    if len(args) == 2 and brack == 0:
                        present.append(args[1])
                elif macname == 'RECALL_XY':
                    (args, optional_args, brack, paren) = parse_macroref(0, leadmac.string)
                    if len(args) == 4:
                        present.append(args[1])
                elif macname == 'CLEAR_VARIABLE':
                    (args, optional_args, brack, paren) = parse_macroref(0, leadmac.string)
                    # having CLEAR_VARIABLE on a line and its arguments in the following lines
                    # leads to an args list with length 1
                    # skip the check and avoid a crash if that's the case
                    if len(args) > 1:
                        for arg in [x.lstrip() for x in args[1].split(',')]:
                            if arg in storedids:
                                del storedids[arg]
                elif macname in whomacros:
                    (args, optional_args, brack, paren) = parse_macroref(0, leadmac.string)
                    present.append(args[whomacros[macname]])
        m = re.search("# *wmllint: recognize +(.*)", lines[i])
        if m:
            present.append(string_strip(m.group(1)).strip())
        if '=' not in lines[i] or ignoreable:
            continue
        parseable = False
        try:
            (key, prefix, value, comment) = parse_attribute(lines[i])
            parseable = True
        except TypeError:
            pass
        if parseable:
            if "wmllint: ignore" in comment:
                continue
            # Recognize units when unstored
            if (in_scenario or in_multiplayer) and in_store:
                if key == 'id' and not in_not:
                    if not storeid == None:
                        storeid == storeid + ',' + value
                    else:
                        storeid = value
                elif key == 'variable' and '{' not in value:
                    storevar = value
            elif in_unstore:
                if key == 'variable':
                    value = value.split("[$")[0]
                    if value in storedids:
                        for unit_id in storedids[value].split(','):
                            present.append(unit_id.lstrip())
                        del storedids[value]
            elif key == 'name' and in_clear:
                for val in value.split(','):
                    val = val.lstrip()
                    if val in storedids:
                        del storedids[val]
            has_tr_mark = translation_mark.search(value)
            if key == 'role':
                present.append(value)
            if has_tr_mark:
                # FIXME: This test is rather bogus as is.
                # Doing a better job would require tokenizing to pick up the
                # string boundaries. I'd do it, but AI0867 is already working
                # on a parser-based wmllint.
                if '{' in value and "+" not in value and value.find('{') > value.find("_"):
                    print('"%s", line %d: macro reference in translatable string'\
                          % (filename, i+1))
                #if future and re.search("[.,!?]  ", lines[i]):
                #    print('"%s", line %d: extraneous space in translatable string'\
                #          % (filename, i+1))
            # Check correctness of translation marks and descriptions
            if key.startswith("#"): # FIXME: parse_attribute is confused.
                pass
            elif key.startswith("{"):
                pass
            elif in_name_generator:
                pass
            elif key == 'letter': # May be led with _s for void
                pass
            elif key in ('name', 'male_name', 'female_name', 'value'): # FIXME: check this someday
                pass
            elif key == "variation_name":
                if markcheck and not has_tr_mark:
                    print('"%s", line %d: %s should be renamed as variation_id and/or marked as translatable' \
                          % (filename, i+1, key))
            elif is_translatable(key):
                if markcheck and has_tr_mark and '""' in lines[i]:
                    print('"%s", line %d: %s doesn`t need translation mark (translatable string is empty)' \
                          % (filename, i+1, key))
                    lines[i] = lines[i].replace("=_","=")
                if markcheck and not value.startswith("$") and not value.startswith("{") and not re.match(" +", value) and not has_tr_mark and '""' not in lines[i] and not ("wmllint: ignore" in comment or "wmllint: noconvert" in comment):
                    print('"%s", line %d: %s needs translation mark' \
                          % (filename, i+1, key))
                    lines[i] = lines[i].replace('=', "=_ ", 1)
                nv = sentence_end.sub(" ", value)
                if nv != value:
                    print('"%s", line %d: double space after sentence end' \
                          % (filename, i+1))
                    if not stringfreeze:
                        lines[i] = sentence_end.sub(" ", lines[i])
                if capitalization_error.search(lines[i]):
                    print('"%s", line %d: probable capitalization or punctuation error' \
                          % (filename, i+1))
                if key == "message" and in_message and not in_option and not ("wmllint: ignore" in comment or "wmllint: noconvert" in comment):
                    lines[i] = pangoize(lines[i], filename, i)
            else:
                if (in_scenario or in_multiplayer) and key == "id":
                    if in_person:
                        present.append(value)
                    elif value and value[0] in ("$", "{"):
                        continue
                    elif preamble_seen and subtag_depth > 0 and not ignore_id \
                         and not in_object and not in_cfg and not in_aspect \
                         and not in_facet and not in_sound_source \
                         and not in_remove_sound_source and not in_load_resource \
                         and not in_stage \
                         and not in_goal and not in_set_menu_item \
                         and not in_clear_menu_item and not directly_in_event[-1] \
                         and not in_time_area and not in_trait and not in_checkbox \
                         and not in_combo and not in_entry and not in_slider \
                         and not in_map_generator and not in_candidate_action \
                         and not (in_fire_event and not (in_primary_unit or in_secondary_unit)) \
                         and not in_remove_event and not in_remove_time_area \
                         and not (in_tunnel and not in_filter):
                        ids = value.split(",")
                        for id_ in ids:
                            # removal of leading whitespace of items in comma-separated lists
                            # is usually supported in the mainline wesnoth lua scripts
                            # not sure about trailing one
                            # also, do not complain about ids if they're referred to a menu item being cleared
                            if id_.lstrip() not in present:
                                print('"%s", line %d: unknown \'%s\' referred to by id' \
                                      % (filename, i+1, id_))
                if (in_scenario or in_multiplayer) and key == "speaker":
                    if value not in present and value not in ("narrator", "unit", "second_unit") and value[0] not in ("$", "{"):
                        print('"%s", line %d: unknown speaker \'%s\' of [message]' \
                              % (filename, i+1, value))
                if markcheck and has_tr_mark and not ("wmllint: ignore" in comment or "wmllint: noconvert" in comment):
                    print('"%s", line %d: %s should not have a translation mark' \
                          % (filename, i+1, key))
                    lines[i] = prefix + value.replace("_", "", 1) + comment + '\n'
    # Now that we know who's present, register all these names as spellings
    declared_spellings[filename] = [x.lower() for x in present if len(x) > 0]
    # Check for textdomain strings; should be exactly one, on line 1
    textdomains = []
    no_text = False
    for num, line in enumerate(lines, start=1):
        if "#textdomain" in line:
            textdomains.append(num)
        elif "wmllint: no translatables" in line:
            no_text = True
    if not no_text:
        if not textdomains:
            print('"%s", line 1: no textdomain string' % filename)
        elif textdomains[0] == 1: # Multiples are OK if first is on line 1
            pass
        elif len(textdomains) > 1:
            print('"%s", line %d: multiple textdomain strings on lines %s' % \
                  (filename, textdomains[0], ", ".join(map(str, textdomains))))
        else:
            w = textdomains[0]
            print('"%s", line %d: single textdomain declaration not on line 1.' % \
                  (filename, w))
            lines = [lines[w-1].lstrip()] + lines[:w-1] + lines[w:]
    return lines

def condition_match(p, q):
    "Do two condition-states match?"
    # The empty condition state is represented by None
    if p is None or q is None or (p == q):
        return True
    # Past this point it's all about handling cases with negation
    sp = p
    np = False
    if sp.startswith("!"):
        sp = sp[1:]
        np = True
    sq = q
    nq = False
    if sq.startswith("!"):
        sq = sp[1:]
        nq == True
    return (sp != sq) and (np != nq)

def consistency_check():
    "Consistency-check state information picked up by sanity_check"
    derivations = {u[2]: u[3] for u in derived_units}
    for (filename, recruitdict, patterndict) in sides:
        for (rdifficulty, (rl, recruit)) in recruitdict.items():
            utypes = []
            for rtype in recruit:
                base = rtype
                if rtype not in unit_types:
                    # Assume WML coder knew what he was doing if macro reference
                    if not rtype.startswith("{"):
                        print('"%s", line %d: %s is not a known unit type' % (filename, rl, rtype))
                    continue
                elif rtype not in usage:
                    if rtype in derivations:
                        base = derivations[rtype]
                    else:
                        print('"%s", line %d: %s has no usage type' % \
                              (filename, rl, rtype))
                        continue
                if not base in usage:
                    print('"%s", line %d: %s has unknown base %s' % \
                          (filename, rl, rtype, base))
                    continue
                else:
                    utype = usage[base]
                utypes.append(utype)
                for (pdifficulty, (pl, recruit_pattern)) in patterndict.items():
                    if condition_match(pdifficulty, rdifficulty):
                        if utype not in recruit_pattern:
                            rshow = ''
                            if rdifficulty is not None:
                                rshow = 'At ' + rdifficulty + ', '
                            ushow = ''
                            if utype not in usage_types:
                                ushow = ', a non-standard usage class'
                            pshow = ''
                            if pdifficulty is not None:
                                pshow = ' ' + pdifficulty
                            print('"%s", line %d: %s%s (%s%s) doesn\'t match the%s recruitment pattern (%s) for its side' \
                                  % (filename, rl, rshow, rtype, utype, ushow, pshow, ", ".join(recruit_pattern)))
            # We have a list of all the usage types recruited at this difficulty
            # in utypes.  Use it to check the matching pattern, if any. Suppress
            # this check if the recruit line is a macroexpansion.
            if recruit and not recruit[0].startswith("{"):
                for (pdifficulty, (pl, recruitment_pattern)) in patterndict.items():
                    if condition_match(pdifficulty, rdifficulty):
                        for utype in recruitment_pattern:
                            if utype not in utypes:
                                rshow = '.'
                                if rdifficulty is not None:
                                    rshow = ' at difficulty ' + rdifficulty + '.'
                                ushow = ''
                                if utype not in usage_types:
                                    ushow = ' (a non-standard usage class)'
                                print('"%s", line %d: no %s%s units recruitable%s' % (filename, pl, utype, ushow, rshow))
    if movetypes:
        for (unit_id, filename, line, movetype) in unit_movetypes:
            if movetype not in movetypes:
                print('"%s", line %d: %s has unknown movement type' \
                      % (filename, line, unit_id))
    if races:
        for (unit_id, filename, line, race) in unit_races:
            if race not in races:
                print('"%s", line %d: %s has unknown race' \
                      % (filename, line, unit_id))
    # Should we be checking the transitive closure of derivation?
    # It's not clear whether [base_unit] works when the base is itself derived.
    for (filename, line, unit_type, base_unit) in derived_units:
        if base_unit not in unit_types:
            print('"%s", line %d: derivation of %s from %s does not resolve' \
                  % (filename, line, unit_type, base_unit))
    # Check that all advancements are known units
    for (unit_id, filename, lineno, advancements) in advances:
        advancements = [elem.strip() for elem in advancements.split(",")]
        known_units = unit_types + list(derivations.keys())
        bad_advancements = [x for x in advancements if x not in known_units]
        if bad_advancements:
            print('"%s", line %d: %s has unknown advancements %s' \
                  % (filename, lineno, unit_id, bad_advancements))
    # Check next-scenario pointers
    #print("Scenario ID map", scenario_to_filename)
    for (filename, lineno, value) in nextrefs:
        if value not in scenario_to_filename:
            print('"%s", line %d: unresolved scenario reference %s' % \
                  (filename, lineno, value))
    # Report stored units never unstored or cleared
    for store in storedids.keys():
        print('wmllint: stored unit "%s" not unstored or cleared from "%s"' % (storedids[store], store))

# Syntax transformations

leading_ws = re.compile(r"^\s*")

def leader(s):
    "Return a copy of the leading whitespace in the argument."
    return leading_ws.match(s).group(0)

def hack_syntax(filename, lines):
    # Syntax transformations go here.  This gets called once per WML file;
    # the name of the file is passed as filename, text of the file as the
    # array of strings in lines.  Modify lines in place as needed;
    # changes will be detected by the caller.
    #
    # Deal with a few Windows-specific problems for the sake of cross-
    # platform harmony. First, the use of backslashes in file paths.
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        if lines[i].lstrip().startswith("#"):
            pass
        # Looking out for "#" used for color markup
        precomment = re.split(r'\s#', lines[i], 1)[0]
        comment = lines[i][len(precomment):]
        if '\\' in precomment:
            while re.search(r'(?<!\\)\\(?!\\)[^ ={}"]+\.(png|ogg|wav|gif|jpe?g|map|mask|cfg)\b', precomment, flags=re.IGNORECASE):
                backslash = re.search(r'([^ ={}"]*(?<!\\)\\(?!\\)[^ ={}"]+\.)(png|ogg|wav|gif|jpe?g|map|mask|cfg)(?=\b)', precomment, flags=re.IGNORECASE)
                fronted = backslash.group(1).replace("\\","/") + backslash.group(2)
                precomment = precomment[:backslash.start()] + fronted + precomment[backslash.end():]
                print('"%s", line %d: %s -> %s -- please use frontslash (/) for cross-platform compatibility' \
                      % (filename, i+1, backslash.group(), fronted))
        # Then get rid of the 'userdata/' headache.
        if 'userdata/' in precomment:
            while re.search(r'user(data/)?data/[ac]', precomment):
                userdata = re.search(r'(?:\.\./)?user(?:data/)?(data/[ac][^/]*/?)', precomment)
                precomment = precomment[:userdata.start()] + userdata.group(1) + precomment[userdata.end():]
                print('"%s", line %d: %s -> %s -- DO NOT PREFIX PATHS WITH "userdata/"' \
                      % (filename, i+1, userdata.group(), userdata.group(1)))
        lines[i] = precomment + comment

    # Ensure that every attack has a translatable description.
    in_filter_wml = False
    attack_left_open = False
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:

            break
        elif "[filter_wml]" in lines[i]:
            in_filter_wml = True
        elif "[/filter_wml]" in lines[i]:
            in_filter_wml = False
        elif "[attack]" in lines[i]:
            j = i
            have_description = False
            while '[/attack]' not in lines[j]:
                if lines[j].strip().startswith("description"):
                    have_description = True
                j += 1
                # unterminated [attack] tags, for example embedded in a macro,
                # lead to a crash. Print an error message, skip this loop
                # and the following one
                if j >= len(lines):
                    print("{}, line {}: [attack] tag not closed in this file".format(filename, i+1))
                    attack_left_open = True
                    break
            if (not have_description) and (not attack_left_open):
                j = i
                while '[/attack]' not in lines[j]:
                    fields = lines[j].strip().split('#')
                    syntactic = fields[0]
                    comment = ""
                    if len(fields) > 1:
                        comment = fields[1]
                    if syntactic.strip().startswith("name"):
                        description = syntactic.split("=")[1].strip()
                        if not description.startswith('"'):
                            description = '"' + description + '"\n'
                        # Skip the insertion if this is a dummy declaration
                        # or one modifying an attack inherited from a base unit.
                        if "no-icon" not in comment and not in_filter_wml:
                            new_line = leader(syntactic) + "description=_"+description
                            if verbose:
                                print('"%s", line %d: inserting %s' % (filename, i+1, repr(new_line)))
                            lines.insert(j+1, new_line)
                            j += 1
                    j += 1
    # Ensure that every speaker=narrator block without an image uses
    # wesnoth-icon.png as an image.
    narrator = has_image = in_message = False
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        precomment = lines[i].split("#")[0]
        if '[message]' in precomment:
            in_message = True
        if "speaker=narrator" in precomment:
            narrator = True
        elif precomment.strip().startswith("image"):
            has_image = True
        elif '[/message]' in precomment:
            if narrator and not has_image:
                # This line presumes the code has been through wmlindent
                if verbose:
                    print('"%s", line %d: inserting "image=wesnoth-icon.png"'%(filename, i+1))
                lines.insert(i, leader(precomment) + baseindent + "image=wesnoth-icon.png\n")
            narrator = has_image = in_message = False
    # Hack tracking-map macros from 1.4 and earlier.  The idea is to lose
    # all assumptions about colors in the names
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        if lines[i].lstrip().startswith("#"):
            pass
        elif "{DOT_CENTERED" in lines[i]:
            lines[i] = lines[i].replace("DOT_CENTERED", "NEW_JOURNEY")
        elif "{DOT_WHITE_CENTERED" in lines[i]:
            lines[i] = lines[i].replace("DOT_WHITE_CENTERED", "OLD_JOURNEY")
        elif "{CROSS_CENTERED" in lines[i]:
            lines[i] = lines[i].replace("CROSS_CENTERED", "NEW_BATTLE")
        elif "{CROSS_WHITE_CENTERED" in lines[i]:
            lines[i] = lines[i].replace("CROSS_WHITE_CENTERED", "OLD_BATTLE")
        elif "{FLAG_RED_CENTERED" in lines[i]:
            lines[i] = lines[i].replace("FLAG_RED_CENTERED", "NEW_REST")
        elif "{FLAG_WHITE_CENTERED" in lines[i]:
            lines[i] = lines[i].replace("FLAG_WHITE_CENTERED", "OLD_REST")
        elif "{DOT " in lines[i] or "CROSS" in lines[i]:
            m = re.search("{(DOT|CROSS) ([0-9]+) ([0-9]+)}", lines[i])
            if m:
                n = m.group(1)
                if n == "DOT":
                    n = "NEW_JOURNEY"
                if n == "CROSS":
                    n = "NEW_BATTLE"
                x = int(m.group(2)) + 5
                y = int(m.group(3)) + 5
                lines[i] = lines[i][:m.start(0)] +("{%s %d %d}" % (n, x, y)) + lines[i][m.end(0):]
    # Fix bare strings containing single quotes; these confuse wesnoth-mode.el
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        elif lines[i].count("'") % 2 == 1:
            try:
                (key, prefix, value, comment) = parse_attribute(lines[i])
                if "'" in value and value[0].isalpha() and value[-1].isalpha() and '"'+value+'"' not in lines[i]:
                    newtext = prefix + '"' + value + '"' + comment + "\n"
                    if lines[i] != newtext:
                        lines[i] = newtext
                        if verbose:
                            print('"%s", line %d: quote-enclosing attribute value.'%(filename, i+1))
            except TypeError:
                pass
    # Palette transformation for 1.7:
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        if lines[i].lstrip().startswith("#"):
            pass
        # RC -> PAL
        elif "RC" in lines[i]:
            lines[i] = re.sub(r"~RC\(([^=\)]*)=([^)]*)\)",r"~PAL(\1>\2)",lines[i])
    # Rename the terrain definition tag
    in_standing_anim = False
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        if lines[i].lstrip().startswith("#"):
            pass
        # Ugh...relies on code having been wmlindented
        lines[i] = re.sub(r"^\[terrain\]", "[terrain_type]", lines[i])
        lines[i] = re.sub(r"^\[/terrain\]", "[/terrain_type]", lines[i])
        if has_opening_tag(lines[i], "standing_anim"):
            in_standing_anim = True
        if "[/standing_anim]" in lines[i]:
            in_standing_anim = False
        if in_standing_anim:
            lines[i] = re.sub(r"terrain([^_])", r"terrain_type\1", lines[i])
    # Rename two attributes in [set_variable]
    in_set_variable = False
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        if lines[i].lstrip().startswith("#"):
            pass
        if has_opening_tag(lines[i], "set_variable"):
            in_set_variable = True
        if "[/set_variable]" in lines[i]:
            in_set_variable = False
        if in_set_variable:
            lines[i] = re.sub(r"format(?=\s*=)", r"value", lines[i])
            lines[i] = re.sub(r"random(?=\s*=)", r"rand", lines[i])
    # campaigns directory becomes add-ons
    in_binary_path = in_textdomain = False
    for i in range(len(lines)):
        if "no-syntax-rewrite" in lines[i]:
            break
        if lines[i].lstrip().startswith("#"):
            pass
        # This is done on every line
        if "campaigns/" in lines[i]:
            lines[i] = lines[i].replace("{~campaigns/", "{~add-ons/")
            lines[i] = lines[i].replace("{~/campaigns/", "{~add-ons/")
            lines[i] = lines[i].replace("{@campaigns/", "{~add-ons/")
            # Convert UMC to data/add-ons without clobbering mainline. Each path
            # is checked against a list of mainline campaigns. UMC paths are
            # updated to "data/add-ons/"; mainline path strings are unaltered.
            x = 0
            for dc in re.finditer(r"data/campaigns/(\w[\w'&+-]*)", lines[i]):
                if dc.group(1) in mainline:
                    continue
                # Because start() and end() are based on the original position
                # of each iteration, while each replacement shortens the line
                # by two characters, we must subtract an increment that grows
                # with each substitution.
                lines[i] = lines[i][:dc.start()-x] + 'data/add-ons/' + dc.group(1) + lines[i][dc.end()-x:]
                x = x+2
                print('"%s", line %d: data/campaigns/%s -> data/add-ons/%s'\
                      %(filename, i+1, dc.group(1), dc.group(1)))
        elif "@add-ons/" in lines[i]:
            lines[i] = lines[i].replace("{@add-ons/", "{~add-ons/")
        # Occasionally authors try to use '~' with [textdomain] or [binary_path].
        if has_opening_tag(lines[i], "binary_path"):
            in_binary_path = True
        if "[/binary_path]" in lines[i]:
            in_binary_path = False
        if has_opening_tag(lines[i], "textdomain"):
            in_textdomain = True
        if "[/textdomain]" in lines[i]:
            in_textdomain = False
        if in_binary_path or in_textdomain:
            if '~' in lines[i]:
                tilde = re.search(r'(^\s*path) *= *([^#]{0,5})(~/?(data/)?add-ons/)', lines[i])
                if tilde:
                    lines[i] = tilde.group(1) + '=' + tilde.group(2) + 'data/add-ons/' + lines[i][tilde.end():]
                    print('"%s", line %d: %s -> data/add-ons/ -- [textdomain] and [binary_path] paths do not accept "~" for userdata'\
                          % (filename, i+1, tilde.group(3)))
    # some tags do no longer support default side=1 attribute but may use [filter_side]
    # with a SSF instead
    # (since 1.9.5, 1.9.6)
    if missingside:
        side_one_tags_allowing_filter_side = (
            ("remove_shroud"),
            ("place_shroud"),
            ("gold"),
            ("modify_side"),
            ("modify_ai")
            )
        outside_of_theme_wml = True # theme wml contains a [gold] tag - exclude that case
        in_side_one_tag = False
        side_one_tag_needs_side_one = True
        for i in range(len(lines)):
            if "no-syntax-rewrite" in lines[i]:
                break
            precomment = lines[i].split("#")[0]
            if outside_of_theme_wml:
                if has_opening_tag(precomment, "theme"):
                    outside_of_theme_wml = False
            else:
                if "[/theme]" in precomment:
                    outside_of_theme_wml = True
            if outside_of_theme_wml:
                if not in_side_one_tag:
                    for tag in side_one_tags_allowing_filter_side:
                        if "[" + tag + "]" in precomment:
                            in_side_one_tag = True
                else:
                    if side_one_tag_needs_side_one:
                        if "side=" in precomment:
                            side_one_tag_needs_side_one = False
                        if "[filter_side]" in precomment:
                            side_one_tag_needs_side_one = False
                    for tag in side_one_tags_allowing_filter_side:
                        if "[/" + tag + "]" in precomment:
                            if side_one_tag_needs_side_one:
                                if verbose:
                                    print('"%s", line %d: [%s] without "side" attribute is now applied to all sides'%(filename, i+1, tag))
                                #lines.insert(i, leader(precomment) + baseindent + "side=1\n")
                            in_side_one_tag = False
                            side_one_tag_needs_side_one = True
                            break
    # More syntax transformations would go here.
    return lines

def maptransform(filename, baseline, inmap, y):
    # Transform lines in maps
    for i in range(len(inmap[y])):
        for (old, new) in mapchanges:
            inmap[y][i] = inmap[y][i].replace(old, new)

# Generic machinery starts here

def is_map(filename):
    "Is this file a map?"
    return filename.endswith(".map") or filename.endswith(".mask")

if 0: # Not used, as there are currently no defined map transforms
    class maptransform_error(BaseException):
        "Error object to be thrown by maptransform."
        def __init__(self, infile, inline, type):
            self.infile = infile
            self.inline = inline
            self.type = type
        def __repr__(self):
            return '"%s", line %d: %s' % (self.infile, self.inline, self.type)

    def maptransform_sample(filename, baseline, inmap, y):
        "Transform a map line."
        # Sample to illustrate how map-transformation hooks are called.
        # The baseline argument will be the starting line number of the map.
        # The inmap argument will be a 2D string array containing the
        # entire map.  y will be the vertical coordinate of the map line.
        # You pass a list of these as the second argument of translator().
        raise maptransform_error(filename, baseline+y+1,
                             "unrecognized map element at line %d" % (y,))

tagstack = [] # For tracking tag nesting

def outermap(func, inmap):
    "Apply a transformation based on neighborhood to the outermost ring."
    # Top and bottom rows
    for i in range(len(inmap[0])):
        inmap[0][i] = func(inmap[0][i])
        inmap[len(inmap)-1][i] = func(inmap[len(inmap)-1][i])
    # Leftmost and rightmost columns excluding top and bottom rows
    for i in range(1, len(inmap)-1):
        inmap[i][0] = func(inmap[i][0])
        inmap[i][len(inmap[0])-1] = func(inmap[i][len(inmap[0])-1])

def translator(filename, mapxforms, textxform):
    "Apply mapxform to map lines and textxform to non-map lines."
    global tagstack
    gzipped = filename.endswith(".gz")
    if gzipped:
        with gzip.open(filename) as content:
            unmodified = content.readlines()
    else:
        with codecs.open(filename, "r", "utf8") as content:
            unmodified = content.readlines()
    # Pull file into an array of lines, CR-stripping as needed
    mfile = []
    map_only = filename.endswith(".map")
    terminator = "\n"
    UTF8_BOM = "\ufeff"
    for i, line in enumerate(unmodified):
        # get rid of BOM characters
        if i == 0 and line.startswith(UTF8_BOM):
            line = line[1:]
            print("%s: removed UTF-8 BOM character at the start of the file" % (filename))
        if line.endswith("\n"):
            line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
            if not stripcr:
                terminator = '\r\n'
        mfile.append(line)
        if "map_data" in line:
            map_only = False
    # Process line-by-line
    lineno = baseline = 0
    cont = False
    validate = True
    unbalanced = False
    newdata = []
    refname = None
    while mfile:
        if not map_only:
            line = mfile.pop(0)
            if verbose >= 3:
                print(line, end=terminator)
            lineno += 1
        # Check for one certain error condition
        if "{" in line and "}" in line:
            refname = line[line.find("{"):line.rfind("}")]
            # Ignore all-caps macro arguments.
            if refname == refname.upper():
                pass
            elif 'mask=' in line and not (refname.endswith("}") or refname.endswith(".mask")):
                print('"%s", line %d: mask file without .mask extension or not a mask file (%s)' \
                      % (filename, lineno+1, refname))
        # Exclude map_data= lines that are just 1 line without
        # continuation, or which contain {}.  The former are
        # pathological and the parse won't handle them, the latter
        # refer to map files which will be checked separately.
        if map_only or (("map_data=" in line or "mask=" in line)
                        and line.count('"') in (1, 2)
                        and '""' not in line
                        and "{" not in line
                        and "}" not in line
                        and not within('time')):
            outmap = []
            have_header = have_delimiter = False
            maskwarn = False
            maptype = None
            if map_only:
                if filename.endswith(".mask"):
                    maptype = "mask"
                else:
                    maptype = "map"
            else:
                leadws = leader(line)
                if "map_data" in line:
                    maptype = "map"
                elif "mask" in line:
                    maptype = "mask"
            baseline = lineno
            cont = True
            if not map_only:
                fields = line.split('"')
                if fields[1].strip():
                    mfile.insert(0, fields[1])
                if len(fields) == 3:
                    mfile.insert(1, '"')
            if verbose >= 3:
                print("*** Entering %s mode on:" % maptype)
                print(mfile)
            # Gather the map header (if any) and data lines
            savedheaders = []
            while cont and mfile:
                line = mfile.pop(0)
                if verbose >= 3:
                    print(line, end=terminator)
                lineno += 1
                # This code supports ignoring comments and header lines
                if len(line) == 0 or line[0] == '#' or '=' in line:
                    if '=' in line:
                        have_header = True
                    if len(line) == 0:
                        have_delimiter = True
                    savedheaders.append(line + terminator)
                    continue
                if '"' in line:
                    cont = False
                    if verbose >= 3:
                        print("*** Exiting map mode.")
                    line = line.split('"')[0]
                if line:
                    if ',' in line:
                        fields = line.split(",")
                    else:
                        fields = [x for x in line]
                    outmap.append(fields)
                    if not maskwarn and maptype == 'map' and re.search('_s|_f(?!me)', line):
                        print('"%s", line %d: warning, fog or shroud in map file' \
                              % (filename, lineno+1))
                        maskwarn = True
            # Deduce the map type
            if not map_only:
                if maptype == "map":
                    newdata.append(leadws + "map_data=\"")
                elif maptype == "mask":
                    newdata.append(leadws + "mask=\"")
            original = copy.deepcopy(outmap)
            for transform in mapxforms:
                for y in range(len(outmap)):
                    transform(filename, baseline, outmap, y)
            newdata += savedheaders
            if have_header and not have_delimiter:
                newdata.append(terminator)
            for y in range(len(outmap)):
                newdata.append(",".join(outmap[y]) + terminator)
            # All lines of the map are processed, add the appropriate trailer
            if not map_only:
                newdata.append("\"" + terminator)
        elif "map_data=" in line and ("{" in line or "}" in line):
            newline = line
            refre = re.compile(r"\{@?([^A-Z].*)\}").search(line)
            if refre:
                mapfile = refre.group(1)
                if not mapfile.endswith(".map") and is_map(mapfile):
                    newline = newline.replace(mapfile, mapfile + ".map")
            newdata.append(newline + terminator)
            if newline != line:
                if verbose > 0:
                    print('wmllint: "%s", line %d: %s -> %s.' % (filename, lineno, line, newline))
        elif "map_data=" in line and line.count('"') > 1:
            print('wmllint: "%s", line %d: one-line map.' % (filename, lineno))
            newdata.append(line + terminator)
        else:
            # Handle text (non-map) lines.  It can use within().
            newline = textxform(filename, lineno, line)
            newdata.append(newline + terminator)
            fields = newline.split("#")
            trimmed = fields[0]
            destringed = re.sub('"[^"]*"', '', trimmed) # Ignore string literals
            comment = ""
            if len(fields) > 1:
                comment = fields[1]
            # Now do warnings based on the state of the tag stack.
            # the regex check for "path=" is needed due to [modify_ai]
            # which uses square braces in its syntax
            if not unbalanced and not re.match(r"\s*path\=", destringed):
                for instance in re.finditer(r"\[\/?\+?([a-z][a-z_]*[a-z])\]", destringed):
                    tag = instance.group(1)
                    closer = instance.group(0)[1] == '/'
                    if not closer:
                        tagstack.append((tag, {}, []))
                    else:
                        if len(tagstack) == 0:
                            print('"%s", line %d: closer [/%s] with tag stack empty.' % (filename, lineno+1, tag))
                        elif tagstack[-1][0] != tag:
                            print('"%s", line %d: unbalanced [%s] closed with [/%s].' % (filename, lineno+1, tagstack[-1][0], tag))
                        else:
                            if validate:
                                validate_on_pop(tagstack, tag, filename, lineno)
                            tagstack.pop()
                if tagstack:
                    for instance in re.finditer(r'([a-z][a-z_]*[a-z])\s*=(.*)', trimmed):
                        attribute, value = instance.groups()
                        if '#' in value:
                            value = value.split("#")[0]
                        tagstack[-1][1][attribute] = value.strip()
            if "wmllint: validate-on" in comment:
                validate = True
            if "wmllint: validate-off" in comment:
                validate = False
            if "wmllint: unbalanced-on" in comment:
                unbalanced = True
            if "wmllint: unbalanced-off" in comment:
                unbalanced = False
            if "wmllint: match" in comment:
                comment = comment.strip()
                try:
                    fields = comment.split("match ", 1)[1].split(" with ", 1)
                    if len(fields) == 2:
                        notepairs.append((fields[0], fields[1]))
                except IndexError:
                    pass
    # It's an error if the tag stack is nonempty at the end of any file:
    if tagstack:
        print('"%s", line %d: tag stack nonempty (%s) at end of file.' % (filename, lineno, tagstack))
    tagstack = []
    if iswml(filename):
        # Perform checks that are purely local.  This is an
        # optimization hack to reduce parsing overhead.
        for nav in WmllintIterator(newdata, filename):
            try:
                (key, prefix, value, comment) = parse_attribute(nav.text)
                local_sanity_check(filename, nav, key, prefix, value, comment)
            except TypeError:
                key = prefix = value = comment = None
                local_sanity_check(filename, nav, key, prefix, value, comment)
        # Perform file-global semantic sanity checks
        newdata = global_sanity_check(filename, newdata)
        # OK, now perform WML rewrites
        newdata = hack_syntax(filename, newdata)
        # Run everything together
        filetext = "".join(newdata)
        transformed = filetext
    else:
        # Map or mask -- just run everything together
        transformed = "".join(newdata)
    # Simple check for unbalanced macro calls
    linecount = 1
    quotecount = 0
    display_state = False
    singleline = False
    for i in range(len(transformed)):
        if transformed[i] == '\n':
            if singleline:
                singleline = False
                if not display_state and quotecount % 2 and transformed[i:i+2] != "\n\n" and transformed[i-1:i+1] != "\n\n":
                    print('"%s", line %d: nonstandard word-wrap style within message' % (filename, linecount))
            linecount += 1
        elif transformed[i-7:i] == "message" and transformed[i] == '=':
            singleline = True
        elif re.match(" *wmllint: *display +on", transformed[i:]):
            display_state = True
        elif re.match(" *wmllint: *display +off", transformed[i:]):
            display_state = False
        elif transformed[i] == '"' and not display_state:
            quotecount += 1
            if quotecount % 2 == 0:
                singleline = False
    # Return None if the transformation functions made no changes.
    if "".join(unmodified) != transformed:
        return transformed
    else:
        return None

def inner_spellcheck(nav, value, spelldict):
    "Spell-check an attribute value or string."
    # Strip off translation marks
    if value.startswith("_"):
        value = value[1:].strip()
    # Strip off line continuations, they interfere with string-stripping
    value = value.strip()
    if value.endswith("+"):
        value = value[:-1].rstrip()
    # Strip off string quotes
    value = string_strip(value)
    # Discard extraneous stuff
    replacements = (
        ("[", " "),
        ("]", " "),
        ("...", " "),
        ("\"", " "),
        ("\\n", " "),
        ("/", " "),
        ("@", " "),
        (")", " "),
        ("(", " "),
        ("…", " "),  # UTF-8 ellipsis
        ("—", " "),  # UTF-8 em dash
        ("–", " "),  # UTF-8 en dash
        ("―", " "),  # UTF-8 horizontal dash
        ("−", " "),  # UTF-8 minus sign
        ("’", "'"),  # UTF-8 right single quote
        ("‘", "'"),  # UTF-8 left single quote
        ("”", " "),  # UTF-8 right double quote
        ("“", " "),  # UTF-8 left double quote
        ("•", " "),  # UTF-8 bullet
        ("◦", ""),              # Why is this necessary?
        ("''", ""),
        ("female^", " "),
        ("male^", " "),
        ("teamname^", " "),
        ("team_name^", " "),
        ("UI^", " "),
        ("^", " "),
    )

    for old, new in replacements:
        value = value.replace(old, new)

    if '<' in value:
        # remove HelpWML markup and extract its text content where needed
        value = re.sub(r"<(ref|format)>.*?text='(.*?)'.*?< \1>", r"\2", value)
        value = re.sub(r"<(jump|img)>.*?< \1>", "", value)
        value = re.sub(r"<(italic|bold|header)>text='(.*?)'< \1>", r"\2", value)
    # Fold continued lines
    value = re.sub(r'" *\+\s*_? *"', "", value)
    # It would be nice to use pyenchant's tokenizer here, but we can't
    # because it wants to strip the trailing quotes we need to spot
    # the Dwarvish-accent words.
    for token in value.split():
        # Try it with simple lowercasing first
        lowered = token.lower()
        normal = token
        if d.check(lowered):
            continue
        # Strip leading punctuation and grotty Wesnoth highlighters
        # Last char in this regexp is to ignore concatenation signs.
        while lowered and lowered[0] in " \t(`@*'%_+":
            lowered = lowered[1:]
            normal = normal[1:]
        # Not interested in interpolations or numeric literals
        if not lowered or lowered.startswith("$"):
            continue
        # Suffix handling. Done in two passes because some
        # Dwarvish dialect words end in a single quote
        while lowered and lowered[-1] in "_-*).,:;?!& \t":
            lowered = lowered[:-1]
            normal = normal[:-1]
        if lowered and spelldict.check(lowered):
            continue
        while lowered and lowered[-1] in "_-*').,:;?!& \t":
            lowered = lowered[:-1]
            normal = normal[:-1]
        # Not interested in interpolations or numeric literals
        if not lowered or lowered.startswith("$") or lowered[0].isdigit():
            continue
       # Nuke balanced string quotes if present
        lowered = string_strip(lowered)
        normal = string_strip(normal)
        if lowered and spelldict.check(lowered):
            continue
        # No match? Strip possessive suffixes and try again.
        elif lowered.endswith("'s") and spelldict.check(lowered[:-2]):
            continue
        # Hyphenated compounds need all their parts good
        if "-" in lowered:
            parts = lowered.split("-")
            if [w for w in parts if not w or spelldict.check(w)] == parts:
                continue
        # Modifier literals aren't interesting
        if re.match("[+-][0-9]", lowered):
            continue
        # Match various onomatopoetic exclamations of variable form
        if re.match("hm+", lowered):
            continue
        if re.match("a+[ur]*g+h*", lowered):
            continue
        if re.match("(mu)?ha(ha)*", lowered):
            continue
        if re.match("ah+", lowered):
            continue
        if re.match("no+", lowered):
            continue
        if re.match("um+", lowered):
            continue
        if re.match("aw+", lowered):
            continue
        if re.match("o+h+", lowered):
            continue
        if re.match("s+h+", lowered):
            continue
        yield normal


def spellcheck(fn, d):
    "Spell-check a file using an Enchant dictionary object."
    local_spellings = []
    # Accept declared spellings for this file
    # and for all directories above it.
    up = fn
    while True:
        if not up or is_root(up):
            break
        else:
            local_spellings += declared_spellings.get(up,[])
            up = os.path.dirname(up)
    local_spellings = [w for w in local_spellings if not d.check(w)]
    for word in local_spellings:
        d.add_to_session(word)

    # Process this individual file
    for nav in WmllintIterator(filename=fn):
        # Recognize local spelling exceptions
        if not nav.element and "#" in nav.text:
            comment = nav.text[nav.text.index("#"):]
            words = re.search("wmllint: local spellings? (.*)", comment)
            if words:
                for word in words.group(1).split():
                    word = word.lower()
                    if not d.check(word):
                        d.add_to_session(word)
                        local_spellings.append(word)
                    else:
                        nav.printError("spelling '%s' already declared" % word)

    to_insert = defaultdict(list)
    for nav in WmllintIterator(filename=fn):
        # Spell-check message and story parts
        if nav.element in spellcheck_these:
            # Special case, beyond us until we can do better filtering..
            # There is lots of strange stuff in text- attributes in the
            # helpfile(s).
            if nav.element == 'text=' and '[help]' in nav.ancestors():
                continue
            # Remove pango markup
            if "<" in nav.text or ">" in nav.text or '&' in nav.text:
                nav.text = pangostrip(nav.text)
            # Spell-check the attribute value
            (key, prefix, value, comment) = parse_attribute(nav.text)
            if "no spellcheck" in comment:
                continue
            to_insert[nav.lineno].extend(inner_spellcheck(nav, value, d))
        # Take exceptions from the id fields
        if nav.element == "id=":
            (key, prefix, value, comment) = parse_attribute(nav.text)
            value = string_strip(value).lower()
            if value and not d.check(value):
                d.add_to_session(value)
                local_spellings.append(value)
    for word in local_spellings:
        try:
            d.remove_from_session(word)
        except AttributeError:
            print("Caught AttributeError when trying to remove %s from dict" % word)
    with open(fn) as fd:
        lines = list(fd)
    inserted = set()
    with open(fn, 'w') as fd:
        for i, l in enumerate(lines):
            spellings = set(to_insert[i]) - inserted
            inserted = inserted | spellings
            if spellings:
                print('# wmllint: local spellings', ' '.join(spellings), file=fd)
            print(l, file=fd, end='')

vctypes = (".svn", ".git", ".hg")

def interesting(fn):
    "Is a file interesting for conversion purposes?"
    return (fn.endswith(".cfg") and not fn.endswith("_info.cfg")) \
           or is_map(fn) or issave(fn)

def allcfgfiles(directory):
    "Get the names of all interesting files under directory."
    datafiles = []
    if not os.path.isdir(directory):
        if interesting(directory):
            if not os.path.exists(directory):
                print("wmllint: %s does not exist" % directory, file=sys.stderr)
            else:
                datafiles.append(directory)
    else:
        for root, dirs, files in os.walk(directory):
            for vcsubdir in vctypes:
                if vcsubdir in dirs:
                    dirs.remove(vcsubdir)
            for name in files:
                if interesting(os.path.join(root, name)):
                    datafiles.append(os.path.join(root, name))
    datafiles.sort() # So diffs for same campaigns will cluster in reports
    return map(os.path.normpath, datafiles)

if __name__ == '__main__':
    missingside = True
    stringfreeze = False
    stripcr = False
    verbose = 1
    arguments = sys.argv[1:]
    
    import json
    with open('declared_spellings.json') as fd:
        declared_spellings = json.load(fd)

    try:
        if not arguments:
            arguments = ["."]

        failed_any_dirs = False

        if True:
            # Attempt a spell-check
            if True:
                try:
                    import enchant
                    d = enchant.Dict("en_US")
                    checker = d.provider.desc
                    if checker.endswith(" Provider"):
                        checker = checker[:-9]
                    print("# Spell-checking with", checker)
                    for word in declared_spellings["GLOBAL"]:
                        d.add_to_session(word.lower())
                    for directory in arguments:
                        if not os.path.exists(directory):
                            failed_any_dirs = True
                            print("wmllint: skipping non-existent path %s" % directory)
                            continue
                        ofp = None
                        for fn in allcfgfiles(directory):
                            if verbose >= 2:
                                print(fn + ":")
                            spellcheck(fn, d)
                except ImportError:
                    print("wmllint: spell check unavailable, install python-enchant to enable", file=sys.stderr)
        if failed_any_dirs:
            sys.exit(1)
    except KeyboardInterrupt:
        print("Aborted")
