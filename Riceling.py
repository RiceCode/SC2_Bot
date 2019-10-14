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








class Riceling(sc2.BotAI):


    def __init__(self):

        self.overlord_list = []              #set up the list -> but put outside it won't recognize..; put inside -> second iteration will clear everything.
        self.overlord_timer = 0        #in seconds, we determine when to send our overlord to scout
        self.defend_around = [HATCHERY, LAIR, HIVE, EXTRACTOR, DRONE]
        self.attacking = 0

        #ideal units
        self.ideal_mutalisk = 0
        self.ideal_corrupter = 0

        #action
        self.action_scouting = 0


        #buildorder
        self.buildorder = [
            UnitTypeId.DRONE,       #first set
            UnitTypeId.OVERLORD,
            UnitTypeId.DRONE,
            UnitTypeId.DRONE,       #second set
            UnitTypeId.DRONE,
            UnitTypeId.DRONE,
            UnitTypeId.HATCHERY,
            UnitTypeId.DRONE,       #third set
            UnitTypeId.DRONE,
            UnitTypeId.EXTRACTOR,
            UnitTypeId.SPAWNINGPOOL,
            UnitTypeId.DRONE,       #forth set
            UnitTypeId.DRONE,
            UnitTypeId.DRONE,
            UnitTypeId.DRONE,
            "END",
        ]
        # current step of the buildorder;
        self.buildorder_step = 0
        self.from_larva = {UnitTypeId.DRONE, UnitTypeId.OVERLORD, UnitTypeId.ZERGLING, UnitTypeId.ROACH}
        self.from_drone = {UnitTypeId.SPAWNINGPOOL, UnitTypeId.EXTRACTOR, UnitTypeId.ROACHWARREN}

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


    def train_overlord(self):
        if self.can_afford(OVERLORD) and self.units(LARVA).exists and not self.already_pending(OVERLORD):
            self.do(self.units(LARVA).random.train(OVERLORD))


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


        await self.distribute_workers() # in sc2/bot_ai.py
        await self.do_buildorder()

        if self.buildorder[self.buildorder_step] == "END":
            await self.distribute_workers() # in sc2/bot_ai.py
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
        defense_forces_antiair = self.units(HYDRALISK) | self.units(QUEEN)
        forces = self.units(ZERGLING) | self.units(HYDRALISK) | self.units(BANELING)

        #Defend your base with 15+ defense force
        threats = []
        threats_air = []

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
                        if enemy.type_id not in self.units_to_ignore_defend and not enemy.is_flying:
                            #print("6.2) If not units_to ignore", enemy)
                            #6.2) If not units_to ignore Unit(name='Drone', tag=4349755393)
                            #  threats += enemy #does this need to be typeid??
                            threats.append(enemy)
                            #print("6.3) Current threat:", threats)
                        if enemy.type_id not in self.units_to_ignore_defend and enemy.is_flying:
                            threats_air.append(enemy)

                #print("7) current threats numbers", len(threats), ":", threats)
                #keep running this loop until we have a threat.
                if len(threats) + len(threats_air) > 1:
                    break
            if len(threats) + len(threats_air) > 1:
                break




                #it seems like whatever is scouted gets added to the list???
                #Attempting to defend ground -> which says everything has been added to the threats regardless of how far away it is.

                #need to check overlord list and see why we send all 3 of them.


                #units.can_attack_air
                #units.can_attack_ground
                #units.is_flying


        #print("current attack value ", self.attacking, "; Forces amount:", forces.amount, "threats", len(threats))
        if defense_forces_antiair.amount > len(threats_air) and len(threats_air) >= 1:
            print("Attempting to defend Air")
            defence_target_air = threats_air[0].position.random_on_distance(random.randrange(1, 3))

            for unit in defense_forces_antiair.idle:
                 self.do(unit.attack(defence_target_air))



        #for now lets set it to if have 1 defense force, defend. Future we set based on maybe number of units... waiting is too damn painful
        if defense_forces.amount > len(threats) and len(threats) >= 1:
            #print("Attempting to defend ground")
            defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))

            for unit in defense_forces.idle:
                self.do(unit.attack(defence_target))



        #in_ability_cast_range
        #energy_percentage





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




    #do_buildorder modified from RoachRush.py https://github.com/tweakimp/RoachRush/blob/master/Main.py
    async def do_buildorder(self):
        # only try to build something if you have 25 minerals, otherwise you dont have enough anyway
        if self.minerals < 25:
            return
        current_step = self.buildorder[self.buildorder_step]
        # do nothing if we are done already or dont have enough resources for current step of build order
        if current_step == "END" or not self.can_afford(current_step):
            return
        if current_step == UnitTypeId.HATCHERY:
            await self.expand(2)
            self.buildorder_step += 1



        # check if current step needs larva
        if current_step in self.from_larva and self.larva:
            self.do(self.larva.first.train(current_step))
            print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name} ")
            self.buildorder_step += 1



        # check if current step needs drone
        elif current_step in self.from_drone:
            if current_step == UnitTypeId.EXTRACTOR:
                # get geysers that dont have extractor on them
                geysers = self.vespene_geyser.filter(
                    lambda g: all(g.position != e.position for e in self.units(UnitTypeId.EXTRACTOR))
                )
                # pick closest
                position = geysers.closest_to(self.start_location)
            else:
                if current_step == UnitTypeId.ROACHWARREN:
                    # check tech requirement
                    if not self.structures(UnitTypeId.SPAWNINGPOOL).ready:
                        return
                # pick position towards ramp to avoid building between hatchery and resources
                buildings_around = self.townhalls(UnitTypeId.HATCHERY).first.position.towards(
                    self.main_base_ramp.depot_in_middle, 7
                )
                # look for position until we find one that is not already used
                position = None
                while not position:
                    position = await self.find_placement(building=current_step, near=buildings_around, placement_step=4)
                    if any(building.position == position for building in self.units.structure):
                        position = None
            # got building position, pick worker that will get there the fastest
            worker = self.workers.closest_to(position)
            self.do(worker.build(current_step, position))
            print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name}")
            self.buildorder_step += 1
        elif current_step == UnitTypeId.QUEEN:
            # tech requirement check
            if not self.structures(UnitTypeId.SPAWNINGPOOL).ready:
                return
            hatch = self.townhalls(UnitTypeId.HATCHERY).first
            self.do(hatch.train(UnitTypeId.QUEEN))
            print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name}")
            self.buildorder_step += 1


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

        #drones that are idle
        for drone in self.units(DRONE).idle:
            #print("attempting to redistribute idle worker")
            await self.distribute_workers()


    #Only allow 3 expansion max
    async def expand(self, numBase):
        #3 base start
        if (self.structures(HATCHERY).amount + self.structures(LAIR).amount + self.structures(HIVE).amount )  <= numBase :
            if self.can_afford(HATCHERY) and  not self.already_pending(HATCHERY):
                await self.expand_now()

        #continue expansion if have extra resources
        if (self.townhalls.amount) >= 3:
            if self.minerals > 2500:
                if self.can_afford(HATCHERY) and  not self.already_pending(HATCHERY):
                    await self.expand_now()





    async def overlord_management(self):
        """
            Creates overlords whenever we're reaching towards population cap.
            Assume the timing of the base determines what stage of the game we're at.

            We also manage scouting with overlord. Currently sending one to the main base of enemy. Send new one every 80 secs when previous one dies.
            todo: scout multiple base; scouting route.
        """

        #Early game
        if self.supply_left < 2 and self.game_stage() == "early":
            self.train_overlord()
        #Mid game
        if self.supply_left < 6 and self.game_stage() == "mid":
            self.train_overlord()
        #Late game
        if self.supply_left < 12 and self.game_stage() == "late":
            self.train_overlord()


        #if there's second townhall
        if len(self.townhalls) > 1:
            th = self.townhalls[1]
            abilities = await self.get_available_abilities(th)
            if AbilityId.RESEARCH_PNEUMATIZEDCARAPACE in abilities and self.can_afford(AbilityId.RESEARCH_PNEUMATIZEDCARAPACE):
                self.do(th(AbilityId.RESEARCH_PNEUMATIZEDCARAPACE))
                print("started research")


        #First start by sending our first overlord directly into the enemy's base. Must be not scouting (action_scouting = 0) and wasn't scouting in the last 80 seconds (as defined by overlord_timer)
        if self.action_scouting == 0 and self.time >= self.overlord_timer:
            self.action_scouting = 1
            print("Sending overlord at ", self.time_formatted)
            #assign all overlord to the list
            for overlord in self.units(OVERLORD).idle:
                self.overlord_list.append(overlord)
                break

            print("First overlord in list", self.overlord_list[0])               #returns the first overlord's [name, tag]
            self.do(self.overlord_list[0].move(self.enemy_start_locations[0]))   #successfully moved the overlord


        #When our overlord dies, we reset everything
        if len(self.overlord_list) >= 1:
            if self.overlord_list[0] not in self.units(OVERLORD):
                print("Scouting Overlord is dead, resetting scouting")
                #reset everything
                self.action_scouting = 0
                self.overlord_list.clear()  #reset the list
                self.overlord_timer = self.time + 80                        #time is in seconds. We're going to send next overlord in 80 seconds.
                print("Next overlord scout = ", self.overlord_timer, "which is:", self.overlord_timer/60, "min")
                self.train_overlord()                                         #overlord is going to die, so train a new one.






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
        Bot(Race.Protoss, Emptybot()),
        Bot(Race.Zerg, Riceling())
        ], realtime=True,
        save_replay_as="ZvT.SC2Replay",
    )


if __name__ == "__main__":
    main()


