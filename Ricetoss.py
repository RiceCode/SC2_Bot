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
from sc2 import position
import math
from operator import itemgetter
import cv2
import numpy as np
import time



###########################


#PROBLEM - DEFEND() NOT WORKING ALL OF A SUDDEN AFTER WE FINISH THE UPGRADE METHODS......

################


class Emptybot(sc2.BotAI):
    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send("(glhf)")








class Ricetoss(sc2.BotAI):


    def __init__(self):

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
            #UnitTypeId.REAPER,
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

        self.known_enemy_units = []





    def select_target(self):
        if self.enemy_units.exists:
            return random.choice(self.enemy_units).position
        if self.enemy_structures.exists:
            return random.choice(self.enemy_structures).position




    def scouting_cloeset_enemybase(self, target, baseoptions, target_list):
        # Determine which base is closest to the target.
        # takes target = the closest base; base option = all option; target_list = used up targets
        # Returns the Point2 of the closest base to target.

        scouting_targets = {}
        for c_expansion in baseoptions:
            #print("c_expansion", c_expansion)
            #print("target_list", target_list)

            if c_expansion not in target_list:
                #print("not in")

                #enemy starting base
                x0 = self.enemy_start_locations[0][0]
                y0 = self.enemy_start_locations[0][1]

                #target
                x1 = target[0]
                y1 = target[1]

                #base option list
                x2 = c_expansion[0]
                y2 = c_expansion[1]

                #expansion score from enemy -- it's now based on enemy's first base because of the weight.
                score = (abs(x1-x2) + abs(y1-y2)*1) + (abs(x1-x0) + abs(y1-y0) *2)

                #add to the list. Current score : expansion point2
                scouting_targets[score] = c_expansion



        #print("####current")
        #print(scouting_targets)


        #list out all the keys
        closest_key = 1000000
        for score in scouting_targets:
            if score < closest_key:
                closest_key = score


        closest_to_target = scouting_targets[closest_key]               #get the point2 based on minimum score

        return closest_to_target    #return the Point2 of the closest base


    def scouting_targets(self):
        #creates a list starting with the enemy's closest expansion.
        #return a list of Point2 of potential expansion location
        target_list = []
        result = "temp"
        enemy_base = {}      #create a new dictionary - so it won't make enemy_base point to self.expansion_locations.
        enemy_base = self.expansion_locations   #dictionary of all the base locations

        numberofexpansion = len(enemy_base)
        x = 0   #ensure first run check against enemy base


        while x < numberofexpansion:
            #first run will look into enemy base vs all possible combination.
            if x == 0:
                result = self.scouting_cloeset_enemybase(self.enemy_start_locations[0], enemy_base, target_list)
            else:
                result = self.scouting_cloeset_enemybase(result, enemy_base, target_list)

            target_list.append(result)

            #POP MIGHT BE AN ISSUE.
            #enemy_base.pop(result)        #remove item from dictionary once we finish looking at it.
            numberofexpansion = len(enemy_base)
            x+=1

        #print("#############")
        #print(target_list)

        return(target_list)





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




    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send("(glhf)")
        else:
            await self.distribute_workers() # in sc2/bot_ai.py
            await self.build_workers()
            await self.build_pylons()
            await self.scout()
            await self.intel()
            await self.build_assimilators()
            await self.build_offensive_buildings()
            await self.build_offensive_force()
            await self.expand()






    """
    async def defend(self, iteration):
    #Defend looks into a list of known enemy. When there are known enemy, we defend
        defense_forces = self.units(ZERGLING) | self.units(HYDRALISK) | self.units(BANELING) | self.units(QUEEN)
        defense_forces_antiair = self.units(HYDRALISK) | self.units(QUEEN)
        forces = self.units(ZERGLING) | self.units(HYDRALISK) | self.units(BANELING)

        #Defend your base with 15+ defense force
        threats = []
        threats_air = []
        close_enemy = []

        #print(self.enemy_units)

        #structure loops: 1) loop through each structure type 2) loop through each structure within that specific structure type
        for structure_type in self.defend_around:
            #print("1) Hello, defend around", self.defend_around, "Structure type:", structure_type)
            for structure in self.structures(structure_type):
                #print("3) structure:", structure, "structure_type", self.structures(structure_type))

                #Check to see if there's enemy unit. If so, we see if they're close to the current structure.
                if len(self.enemy_units) > 0:
                    close_enemy = self.enemy_units.closer_than(self.threat_proximity, structure)    #return a list of enemy units that's close to current structure
                    #print("7) Close enemies ", close_enemy)

                    if len(close_enemy) > 0:
                        print("8) close enemy", close_enemy)

                        for enemy in close_enemy:
                            #6.1) For loop this enemy: Unit(name='Drone', tag=4349755393) type_id: UnitTypeId.DRONE
                            if enemy.type_id not in self.units_to_ignore_defend and not enemy.is_flying:
                                #print("6.2) If not units_to ignore", enemy)
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

    """



    async def scout(self):
        if len(self.units(OBSERVER)) > 0:
            scout = self.units(OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                #move_to = self.random_location_variance(enemy_location)
                move_to = enemy_location
                print(move_to)
                self.do(scout.move(move_to))

        else:
            for rf in self.structures(ROBOTICSFACILITY).ready.idle:
                if self.can_afford(OBSERVER) and self.supply_left > 0:
                    self.do(rf.train(OBSERVER))





    async def build_workers(self):
        for nexus in self.structures(NEXUS).ready.idle:
            print("Training probe from idle townhalls")
            if self.can_afford(PROBE):
                self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON):
            # self.build(PYLON, near=nexuses.first)
            print("attempting to build pylon")
            await self.build(PYLON, near=self.townhalls.first)


    async def build_assimilators(self):
        if not self.already_pending(ASSIMILATOR) and self.can_afford(ASSIMILATOR):
            worker = self.workers.random
            target = self.vespene_geyser.closest_to(worker.position) #or use closest_to(self.start_location)
            self.do(worker.build(ASSIMILATOR, target))






    async def expand(self):
        #expand if we can afford + not building one + if there's at least 18 probe per nexus
        if self.can_afford(NEXUS) and not self.already_pending(NEXUS) and len(self.units(PROBE))* len(self.structures(NEXUS)) > 18*len(self.structures(NEXUS)):
            await self.expand_now()

        #redistribute idles.
        for probes in self.units(PROBE).idle:
            await self.distribute_workers()


    async def build_offensive_force(self):
        for sg in self.structures(STARGATE).ready.idle:
            if self.can_afford(VOIDRAY) and self.supply_left > 0:
                self.do(sg.train(VOIDRAY))


    async def build_offensive_buildings(self):
        #print(self.iteration / self.ITERATIONS_PER_MINUTE)
        if self.structures(PYLON).ready.exists:
            pylon = self.structures(PYLON).ready.random


            if len(self.structures(GATEWAY)) < 1:
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)

            elif self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=pylon)

            if self.structures(CYBERNETICSCORE).ready.exists:
                if len(self.structures(ROBOTICSFACILITY)) < 1:
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(ROBOTICSFACILITY, near=pylon)

            if self.structures(CYBERNETICSCORE).ready.exists:
                if len(self.structures(STARGATE)) < 3:
                    if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                        await self.build(STARGATE, near=pylon)



    async def intel(self):
        """
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)
        draw_dict = {
            #ARMY
            ZERGLING: [3, (255, 100, 1)],
            HYDRALISK: [3, (255, 100, 2)],
            BANELING: [3, (255, 100, 3)],
            QUEEN: [3, (255, 100, 4)],

            #BUILDING AND ECON
            HATCHERY: [15, (0, 255, 0)],
            LAIR: [15, (0, 255, 0)],
            HIVE: [15, (0, 255, 0)],
            EXTRACTOR: [2, (55, 200, 0)],
            DRONE: [1, (55, 200, 0)],
            OVERLORD: [3, (20, 235, 0)],
            SPAWNINGPOOL: [3, (200, 100, 0)],
            HYDRALISKDEN: [3, (150, 150, 0)],
            INFESTATIONPIT: [5, (255, 0, 0)]

        }

        for unit_type in draw_dict:
            for unit in self.units(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)


        #Adding enemy units and structure to stored list. Todo: add something to remove dead units.
        if self.enemy_units.exists:
            for enemy in self.enemy_units.ready:
                if enemy not in self.known_enemy_units:
                    self.known_enemy_units.append(enemy)
                    self.known_enemy_name.append(enemy.name)
        if self.enemy_structures.exists:
            for enemy in self.enemy_structures.ready:
                if enemy not in self.known_enemy_units:
                    self.known_enemy_units.append(enemy)
                    self.known_enemy_name.append(enemy.name)


        if len(self.known_enemy_units) > 1:
            worker_names = ["probe", "scv", "drone"]
            for enemy in self.known_enemy_units:
                if enemy.name.lower() in worker_names:
                    cv2.circle(game_data, (int(enemy.position[0]), int(enemy.position[1])), 1, (55, 0, 155), -1)
                else:
                    cv2.circle(game_data, (int(enemy.position[0]), int(enemy.position[1])), 3, (50, 0, 215), -1)






         # flip horizontally to make our final fix in visual representation:
        flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(flipped, dsize=None, fx=2, fy=2)

        cv2.imshow('Intel', resized)
        cv2.waitKey(1)

        #print(self.known_enemy)




        #
        #    return random.choice(self.enemy_structures).position
    """



#use this for playing main bot.
def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"), [
        Bot(Race.Protoss, Ricetoss()),
        #Computer(Race.Terran, Difficulty.Harder)
        Computer(Race.Terran, Difficulty.Medium)
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
        ], realtime=False,
        save_replay_as="ZvT.SC2Replay",
    )
"""


if __name__ == "__main__":
    main()


