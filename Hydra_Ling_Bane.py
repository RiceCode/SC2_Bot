from operator import or_
import random

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units
from random import randrange




###########################


#PROBLEM - DEFEND() NOT WORKING ALL OF A SUDDEN AFTER WE FINISH THE UPGRADE METHODS......

################


class Emptybot(sc2.BotAI):
    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send("(glhf)")








class Hydra_Ling_Bane(sc2.BotAI):


    def __init__(self):
        self.defend_around = [HATCHERY, LAIR, HIVE, EXTRACTOR, DRONE]
        self.attacking = 0

        self.units_to_ignore_defend = [
            UnitTypeId.KD8CHARGE,
            UnitTypeId.REAPER,
            UnitTypeId.BANELING,
            UnitTypeId.EGG,
            UnitTypeId.LARVA,
            UnitTypeId.BROODLING,
            UnitTypeId.INTERCEPTOR,
            UnitTypeId.CREEPTUMOR,
            UnitTypeId.CREEPTUMORBURROWED,
            UnitTypeId.CREEPTUMORQUEEN,
            UnitTypeId.CREEPTUMORMISSILE
        ]



    def select_target(self):
        if self.enemy_units.exists:
            return random.choice(self.enemy_units).position
        if self.enemy_structures.exists:
            return random.choice(self.enemy_structures).position





    def finish_them(self):
        if self.enemy_units.exists:
            return random.choice(self.enemy_units).position
        if self.enemy_structures.exists:
            return random.choice(self.enemy_structures).position
        else:
            return self.enemy_start_locations[0]

    def game_stage(self):
        """
            Creates overlords whenever we're reaching towards population cpa.
            Assume the timing of the base determines what stage of the game we're at.
        """
        #Early game
        if self.structures(LAIR).amount + self.structures(HIVE).amount == 0:
            return "early"
        #Mid game
        elif self.structures(LAIR).amount == 1:
            return "mid"

        #Late game
        elif self.structures(HIVE).amount == 1:
            return "late"



    def train_baneling(self):
        if self.structures(BANELINGNEST).ready.exists:
            if self.can_afford(BANELING) and self.units(ZERGLING).exists:
                self.do(self.units(ZERGLING).random.train(BANELING))

    def train_zergling(self):
        #build zergling
        if self.structures(SPAWNINGPOOL).ready.exists:
            if self.can_afford(ZERGLING) and self.units(LARVA).exists:
                self.do(self.units(LARVA).random.train(ZERGLING))

    def train_hydralisk(self):
        if self.structures(HYDRALISKDEN).ready.exists:
            if self.can_afford(HYDRALISK) and self.units(LARVA).exists:
                self.do(self.units(LARVA).random.train(HYDRALISK))




    async def on_step(self, iteration):

        numBase = 2
        if iteration == 0:
            await self.chat_send("(glhf)")

        await self.distribute_workers() #todo: cannot find this function. rewrite?
        await self.expand(numBase)
        await self.base_management()
        await self.overlord_management()
        await self.drone_management(numBase)
        await self.extractor_build()
        await self.build_baneling()
        await self.defend(iteration)
        await self.queen(numBase)
        await self.build_hydralisk()
        await self.infestation_pit()
        await self.force()




    async def force(self):
        #always have 5 or more zerglings
        #print("current zergling count: ", self.units(ZERGLING).amount, "; current hydra:", self.units(HYDRALISK).amount)
        if self.units(ZERGLING).amount < 5:
            self.train_zergling()
        #goal to have about 5 zergling - 1 hydra
        else:
            if self.units(HYDRALISK).amount/self.units(ZERGLING).amount < 0.25:
                self.train_hydralisk()
            if self.units(BANELING).amount/self.units(ZERGLING).amount < 0.25:
                self.train_baneling()
            else:
                self.train_zergling()


    async def defend(self, iteration):
    #Defend looks into a list of known enemy. When there are known enemy, we defend
        defense_forces = self.units(ZERGLING) | self.units(HYDRALISK) | self.units(BANELING) | self.units(QUEEN)
        forces = self.units(ZERGLING) | self.units(HYDRALISK) | self.units(BANELING)

        #Defend your base with 15+ defense force
        threats = []

        #print(self.enemy_units)

        for structure_type in self.defend_around:
            #print("1) Hello, defend around", self.defend_around; "Structure type:" structure_type)

            #this loop wasn't entered.
            for structure in self.structures(structure_type):
                #print("3) structure:", structure, "structure_type", self.structures(structure_type))

                if len(self.enemy_units) > 0:
                    #print("6) Enemy units: ", self.enemy_units )
                    #self.enemy_units returns: [Unit(name='Drone', tag=4350017537), Unit(name='Drone', tag=4351852545), Unit(name='Drone', tag=4350279681), Unit(name='Drone', tag=4351328257)]

                    #all others
                    #iterate over a list of enemy
                    for enemy in self.enemy_units:
                        #print("6.1) For loop this enemy:", enemy, "type_id:", enemy.type_id)
                        #6.1) For loop this enemy: Unit(name='Drone', tag=4349755393) type_id: UnitTypeId.DRONE
                        if enemy.type_id not in self.units_to_ignore_defend:
                            #print("6.2) If not units_to ignore", enemy)
                            #6.2) If not units_to ignore Unit(name='Drone', tag=4349755393)
                            #  threats += enemy #does this need to be typeid??
                            threats.append(enemy)
                            #print("6.3) Current threat:", threats)

                #print("7) current threats numbers", len(threats), ":", threats)
                #keep running this loop until we have a threat.
                if threats:
                    break
            if threats:
                break




        #print("current attack value ", self.attacking, "; Forces amount:", forces.amount, "threats", len(threats))



        #for now lets set it to if have 1 defense force, defend. Future we set based on maybe number of units... waiting is too damn painful
        if defense_forces.amount > len(threats) and len(threats) >= 1:
            print("Attempting to defend")
            defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
            for unit in defense_forces.idle:
                self.do(unit.attack(defence_target))

            """
            for unit in defense_forces.idle:
                unit.attack(
                    self.structures(HATCHERY)
                        .closest_to(self.game_info.map_center)
                        .position.towards(self.game_info.map_center, random.randrange(8, 10))
                )
            """






        if forces.amount > 120:
            print("Prepare for an attack")
            for unit in forces.idle:
                self.do(unit.attack(self.finish_them()))
                self.attacking = 1


        #if we are attacking and our units fall below 80, we retreat
        if self.attacking == 1 and forces.amount <= 80:
            print("Planning for a retreat")
            for unit in forces:
                self.do(unit.move(self.structures(HATCHERY).closest_to(self.game_info.map_center).position.towards(self.game_info.map_center, randrange(8,10))))
            self.attacking = 0





    async def build_hydralisk(self):
        #build hydra den
        if self.structures(SPAWNINGPOOL).ready.exists and not self.structures(HYDRALISKDEN):
            if not self.already_pending(HYDRALISKDEN) and self.can_afford(HYDRALISKDEN):
                await self.build(HYDRALISKDEN, near=self.townhalls.first.position.towards(self.game_info.map_center,5))

        #upgrade hydra range & speed
        if self.structures(HYDRALISKDEN).ready.exists and self.structures(HIVE).ready.exists:
            hydraden = self.structures(HYDRALISKDEN).ready.first
            abilities = await self.get_available_abilities(hydraden)
            #range
            if AbilityId.RESEARCH_GROOVEDSPINES in abilities and self.can_afford(AbilityId.RESEARCH_GROOVEDSPINES):
                self.do(hydraden(AbilityId.RESEARCH_GROOVEDSPINES))
            #speed
            if AbilityId.RESEARCH_MUSCULARAUGMENTS in abilities and self.can_afford(AbilityId.RESEARCH_MUSCULARAUGMENTS):
                self.do(hydraden(AbilityId.RESEARCH_MUSCULARAUGMENTS))

    async def build_baneling(self):
        #build the building
        if self.structures(SPAWNINGPOOL).ready.exists and not self.structures(BANELINGNEST):
            if not self.already_pending(BANELINGNEST) and self.can_afford(BANELINGNEST):
                await self.build(BANELINGNEST, near=self.townhalls.first.position.towards(self.game_info.map_center,5))


        #upgrade the units
        if self.structures(BANELINGNEST).ready.exists and self.structures(LAIR).ready.exists:
            banelingnest = self.structures(BANELINGNEST).ready.first
            abilities = await self.get_available_abilities(banelingnest)
            if AbilityId.RESEARCH_CENTRIFUGALHOOKS in abilities and self.can_afford(AbilityId.RESEARCH_CENTRIFUGALHOOKS):
                self.do(banelingnest(AbilityId.RESEARCH_CENTRIFUGALHOOKS))



    async def extractor_build(self):
        #only start extractor when we got spawning pool or started one.
        if self.structures(SPAWNINGPOOL).ready.exists or self.already_pending(SPAWNINGPOOL):
            if not self.already_pending(EXTRACTOR) and self.can_afford(EXTRACTOR):
                drone = self.workers.random
                target = self.vespene_geyser.closest_to(drone.position)
                self.do(drone.build(EXTRACTOR, target))

    async def drone_management(self, numBase):
        #create drones when possible; set limit to 60
        #if self.can_afford(DRONE) and self.units(LARVA).exists and self.units(DRONE).amount <= 20*numBase:
        if self.can_afford(DRONE) and self.units(LARVA).exists and self.units(DRONE).amount <= 20*numBase:
            #print("Current drone amount ", self.units(DRONE).amount)
            self.do(self.units(LARVA).random.train(DRONE))

    #Only allow 3 expansion max
    async def expand(self, numBase):
        if (self.structures(HATCHERY).amount + self.structures(LAIR).amount + self.structures(HIVE).amount )  <= numBase :
            if self.can_afford(HATCHERY) and  not self.already_pending(HATCHERY):
                await self.expand_now()

    async def overlord_management(self):
        """
            Creates overlords whenever we're reaching towards population cpa.
            Assume the timing of the base determines what stage of the game we're at.
        """

        #Early game
        if self.supply_left < 2 and self.game_stage() == "early":
            if self.can_afford(OVERLORD) and self.units(LARVA).exists and not self.already_pending(OVERLORD):
                self.do(self.units(LARVA).random.train(OVERLORD))
        #Mid game

        if self.supply_left < 6 and self.game_stage() == "mid":
            if self.can_afford(OVERLORD) and self.units(LARVA).exists and not self.already_pending(OVERLORD):
                self.do(self.units(LARVA).random.train(OVERLORD))
        #Late game
        if self.supply_left < 12 and self.game_stage() == "late":
            if self.can_afford(OVERLORD) and self.units(LARVA).exists and not self.already_pending(OVERLORD):
                self.do(self.units(LARVA).random.train(OVERLORD))



    async def queen(self, numBase):
        #build some queen, maximum = numBase
        if self.units(QUEEN).amount <= numBase*2:
            if self.can_afford(QUEEN) and self.structures(SPAWNINGPOOL).exists and not self.already_pending(QUEEN):
                self.do(self.townhalls.first.train(QUEEN))
        #queen do injects
        for queen in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                self.do(queen(EFFECT_INJECTLARVA, self.townhalls.first))




    async def base_management(self):
        hq = self.townhalls.first
        #always have spawningpool
        if not (self.structures(SPAWNINGPOOL).exists or self.already_pending(SPAWNINGPOOL)):
            if self.can_afford(SPAWNINGPOOL):
                await self.build(SPAWNINGPOOL, near=self.townhalls.first.position.towards(self.game_info.map_center,5))
                #near=self.townhalls.first.position.towards(mineral_patch,-5))

        #upgrade zergling speed
        if self.structures(SPAWNINGPOOL).ready.exists:
            pool = self.structures(SPAWNINGPOOL).ready.first
            abilities = await self.get_available_abilities(pool)
            if AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST in abilities and self.can_afford(AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST):
                self.do(pool(AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST))
        if self.structures(SPAWNINGPOOL).ready.exists and self.structures(HIVE).ready.exists:
            if AbilityId.RESEARCH_ZERGLINGADRENALGLANDS in abilities and self.can_afford(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS):
                self.do(pool(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS))





        #upgrade townhall
        if self.structures(SPAWNINGPOOL).ready.exists:
            if not (self.townhalls(LAIR).exists or self.already_pending(LAIR)) and hq.is_idle:
                if self.can_afford(LAIR):
                    self.do(hq.build(LAIR))

        #upgrade townhall again
        if self.structures(LAIR).ready.exists and self.structures(INFESTATIONPIT).ready.exists:
            if not (self.townhalls(HIVE).exists or self.already_pending(HIVE)) and hq.is_idle:
                if self.can_afford(HIVE):
                    self.do(hq.build(HIVE))



    async def infestation_pit(self):
        if self.structures(LAIR).ready.exists  and not (self.structures(INFESTATIONPIT).exists or self.already_pending(INFESTATIONPIT)):
            if self.can_afford(INFESTATIONPIT):
                await self.build(INFESTATIONPIT, near=self.townhalls.first.position.towards(self.game_info.map_center,5))






""" #use this for playing main bot.
def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"), [
        Bot(Race.Zerg, Hydra_Ling_Bane()), '
        Computer(Race.Terran, Difficulty.Harder)
        ], realtime=False,
        save_replay_as="ZvT.SC2Replay",
    )
"""

#use this if playing against main bot
def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"), [
        Bot(Race.Zerg, Emptybot()),
        Bot(Race.Zerg, Hydra_Ling_Bane())
        ], realtime=True,
        save_replay_as="ZvT.SC2Replay",
    )


if __name__ == "__main__":
    main()


