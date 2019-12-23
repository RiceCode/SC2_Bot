"""
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units
from random import randrange


units_to_ignore_defend = [
    UnitTypeId.KD8CHARGE,
    UnitTypeId.REAPER,
    UnitTypeId.BANELING,
    UnitTypeId.EGG,
    UnitTypeId.LARVA,
    UnitTypeId.OVERLORD,
    UnitTypeId.BROODLING,
    UnitTypeId.INTERCEPTOR,
    UnitTypeId.CREEPTUMOR,
    UnitTypeId.CREEPTUMORBURROWED,
    UnitTypeId.CREEPTUMORQUEEN,
]


enemy_list = [
    UnitTypeId.KD8CHARGE,
    UnitTypeId.BANELING,
    UnitTypeId.ZEALOT,
    UnitTypeId.MARINE,
    UnitTypeId.REAPER,
]

for enemy in enemy_list:
    if enemy not in units_to_ignore_defend:
        print(enemy)
"""

thisdict =  {
  "brand": "Ford",
  "model": "Mustang",
  "year": 1964
}
thisdict.pop("ssmodel")
print(thisdict)
