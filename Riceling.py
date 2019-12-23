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








class Riceling(sc2.BotAI):


    def __init__(self):

        #overlord and scoutng
        self.overlord_list = []              #list of overlord - used for overlord scouting.
        self.overlord_timer = 0        #in seconds, we determine when to send our overlord to scout
        self.action_scouting = 0
        self.target_base_order = []
        self.known_enemy_units = []
        self.known_enemy_name = []


        self.queen_inject = []
        self.townhall_order = []
        self.queen_creep = []

        #defend/attack
        self.defend_around = [HATCHERY, LAIR, HIVE, EXTRACTOR, DRONE]
        self.attacking = 0
        self.threat_proximity = 11


        #ideal units
        self.ideal_mutalisk = 0
        self.ideal_corrupter = 0

        self.numBase = 2    #default


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
        if iteration == 0:
            await self.chat_send("(glhf)")
            await self.setup_scouting_order()



        await self.distribute_workers() # in sc2/bot_ai.py
        await self.intel()
        await self.do_buildorder()



        if self.buildorder[self.buildorder_step] == "END":
            await self.distribute_workers() # in sc2/bot_ai.py
            await self.scouting_management()
            await self.expand()
            await self.base_management()
            await self.overlord_management()
            await self.drone_management()
            await self.extractor_build()
            await self.build_baneling()
            await self.defend(iteration)
            await self.queen()
            await self.build_hydralisk()
            await self.infestation_pit()
            await self.force()


    async def setup_scouting_order(self):
        self.target_base_order = self.scouting_targets()
        print("Scouting Target Order:")
        print(self.target_base_order)



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
            await self.expand()
            print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name} ")
            self.buildorder_step += 1

        # check if current step needs larva
        if current_step in self.from_larva and self.larva:
            self.do(self.larva.first.train(current_step))
            print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name} ")
            self.buildorder_step += 1

        # check if current step needs drone
        elif current_step in self.from_drone:
            if current_step == UnitTypeId.EXTRACTOR:
                await self.extractor_build()
                print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name}")
                self.buildorder_step += 1


            elif current_step == UnitTypeId.SPAWNINGPOOL:
                await self.spawningpool_build()
                print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name}")
                self.buildorder_step += 1

        elif current_step == UnitTypeId.QUEEN:
            await self.queen()
            print(f"{self.time_formatted} STEP {self.buildorder_step} {current_step.name}")
            self.buildorder_step += 1





            """

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
            """




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
        if not self.already_pending(EXTRACTOR) and self.can_afford(EXTRACTOR):
            drone = self.workers.random
            target = self.vespene_geyser.closest_to(drone.position) #or use closest_to(self.start_location)
            self.do(drone.build(EXTRACTOR, target))




    async def drone_management(self):
        #create drones when possible; set limit to 80 (each base has 20)
        if self.numBase <= 4:
            if self.can_afford(DRONE) and self.units(LARVA).exists and self.units(DRONE).amount <= 20*self.numBase:
                #print("Current drone amount ", self.units(DRONE).amount)
                self.do(self.units(LARVA).random.train(DRONE))

        #drones that are idle
        for drone in self.units(DRONE).idle:
            #print("attempting to redistribute idle worker")
            await self.distribute_workers()


    #Only allow 3 expansion max
    async def expand(self):
        #3 base start
        if (self.structures(HATCHERY).amount + self.structures(LAIR).amount + self.structures(HIVE).amount )  <= self.numBase :
            if self.can_afford(HATCHERY) and  not self.already_pending(HATCHERY):
                await self.expand_now()

        #continue expansion if have extra resources
        if (self.townhalls.amount) >= 3:
            if self.minerals > 2500:
                if self.can_afford(HATCHERY) and  not self.already_pending(HATCHERY):
                    await self.expand_now()
                    self.numBase += 1



    async def scouting_management(self):
        #target = list of Point2 based on priorities
        #First start by sending our first overlord directly into the enemy's base. Must be not scouting (action_scouting = 0) and wasn't scouting in the last 80 seconds (as defined by overlord_timer)

        #1st phase: able to send 1 overlord to each expansion.
        #2nd phase: determine sending zergling or overlord to the location



        #self.target_base_order
        if self.action_scouting == 0 and self.time >= self.overlord_timer:
            self.action_scouting = 1
            print("Sending overlord at ", self.time_formatted)
            #assign all overlord to the list
            for overlord in self.units(OVERLORD).idle:
                self.overlord_list.append(overlord)


            i = 0 #counter used for sending overlord to expansions

            #loop through all overlord available. Only send enough overlord to cover the number of enemy possible base.
            while i < len(self.overlord_list):
                if i < len(self.target_base_order):
                    self.do(self.overlord_list[i].move(self.target_base_order[i]))
                i+= 1



            #manual movement
            #go_to_position = position.Point2(position.Pointlike((x, y)))
            #self.do(self.overlord_list[0].move(go_to_position))

            #send to enemy base
            #print("First overlord in list", self.overlord_list[0])               #returns the first overlord's [name, tag]
            #self.do(self.overlord_list[0].move(self.enemy_start_locations[0]))   #successfully moved the overlord



        #check to see if overlord is dead
        if len(self.overlord_list) >= 1:
            for overlord in self.overlord_list:
                if overlord not in self.units(OVERLORD):
                    print("One of the overlord is dead, resetting everything")
                    #reset everything
                    self.action_scouting = 0
                    self.overlord_list.clear()  #reset the list
                    self.overlord_timer = self.time + 80                        #time is in seconds. We're going to send next overlord in 80 seconds.
                    print("Next overlord scout = ", self.overlord_timer, "which is:", self.overlord_timer/60, "min")
                    self.train_overlord()







    async def overlord_management(self):
        """
            Creates overlords whenever we're reaching towards population cap.
            Assume the timing of the base determines what stage of the game we're at.

            We also manage scouting with overlord. Currently sending one to the main base of enemy. Send new one every 80 secs when previous one dies.
            todo: scout multiple base; scouting route.
        """

        #start = self.start_location()


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











    async def queen(self):
        #build some queen, maximum = numBase
        if self.units(QUEEN).amount <= self.numBase*3:
            if self.can_afford(QUEEN) and self.structures(SPAWNINGPOOL).exists and not self.already_pending(QUEEN):
                self.do(self.townhalls.first.train(QUEEN))

        #queen inject - assign townhall to list
        for th in self.townhalls:
            if th not in self.townhall_order:
                self.townhall_order.append(th)

        #queen inject - assign queen to list
        if len(self.queen_inject) <= self.numBase:
            self.queen_creep.clear()                    #prevent two roles
            for queen in self.units(QUEEN).idle:
                if queen not in self.queen_inject:
                    self.queen_inject.append(queen)

        #queen inject - queen[1] on townhall[1] etc
        i = 0
        while i < len(self.queen_inject):
            if i < len(self.townhall_order):
                abilities = await self.get_available_abilities(self.queen_inject[i])
                if AbilityId.EFFECT_INJECTLARVA in abilities:
                    self.do(self.queen_inject[i](EFFECT_INJECTLARVA, self.townhall_order[i]))
            i += 1



        #queen creep - assign queen to creep list
        for queen in self.units(QUEEN).idle:
            if queen not in self.queen_inject:
                self.queen_creep.append(queen)


        #queen creep - find legal placement and place.
        for queen in self.queen_inject:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities and queen.is_idle:
                x = random.randrange(0, round(self.game_info.map_size[0], 0))
                y = random.randrange(0, round(self.game_info.map_size[1], 0))
                print("creating position")
                position_placement = position.Point2(position.Pointlike((x, y)))

                if self.can_place(BUILD_CREEPTUMOR_QUEEN, position) and self.has_creep(position_placement):
                    print("can place here: ", position_placement)
                    time.sleep(25)
                    abc = await self.do(queen(BUILD_CREEPTUMOR_QUEEN, position))    #problem here
                    print(abc)
                    #print(self.do(queen))




        #Reassign - check to see if queen is dead
        if len(self.queen_inject) >= 1:
            for queen in self.queen_inject:
                if queen not in self.units(QUEEN):
                    print("One of the queen is dead")
                    self.queen_inject.clear()  #reset the list
                    self.queen_creep.clear()

        #Reassign - check to see if townhall is dead
        if len(self.townhall_order) >= 1:
            for th in self.townhall_order:
                if th not in self.townhalls:
                    print("One of the townhall is dead")
                    self.townhall.clear()  #reset the list






        #map_center = self.game_info.map_center
        #position_towards_map_center = self.start_location.towards(map_center, distance=5)
        #await self.build(UnitTypeId.CREEPTUMORQUEEN, near=position_towards_map_center, placement_step=1)



        #CREEPTUMOR
        #CREEPTUMORQUEEN

        #queen do creep
        #print("position = ", position_towards_map_center)

        #for queen in self.queen_creep:
        #    self.do(queen(BUILD_CREEPTUMOR_QUEEN, position_towards_map_center))
        #    self.build(UnitTypeId.CREEPTUMORQUEEN, near=position_towards_map_center, placement_step=1)




    async def spawningpool_build(self):
        #always have spawningpool
        if not (self.structures(SPAWNINGPOOL).exists or self.already_pending(SPAWNINGPOOL)):
            if self.can_afford(SPAWNINGPOOL):
                await self.build(SPAWNINGPOOL, near=self.townhalls.first.position.towards(self.game_info.map_center,5))
                #near=self.townhalls.first.position.towards(mineral_patch,-5))

    async def intel(self):
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


        """
        for enemy_building in self.known_enemy_structures:
            pos = enemy_building.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
        """






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


    async def base_management(self):
        hq = self.townhalls.first
        await self.spawningpool_build()

        """ #old code
        #upgrade zergling speed
        if self.structures(SPAWNINGPOOL).ready.exists:
            pool = self.structures(SPAWNINGPOOL).ready.first
            abilities = await self.get_available_abilities(pool)
            if AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST in abilities and self.can_afford(AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST):
                self.do(pool(AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST))
        """


        #HATCHERY technology
        self.research(UpgradeId.ZERGLINGMOVEMENTSPEED)


        #upgrade to LAIR
        if self.structures(SPAWNINGPOOL).ready.exists:
            if not (self.townhalls(LAIR).exists or self.already_pending(LAIR)) and hq.is_idle:
                if self.can_afford(LAIR):
                    self.do(hq.build(LAIR))

        #LAIR technology
        #hydra done in its own function


        #upgrade to HIVE
        if self.structures(LAIR).ready.exists and self.structures(INFESTATIONPIT).ready.exists:
            if not (self.townhalls(HIVE).exists or self.already_pending(HIVE)) and hq.is_idle:
                if self.can_afford(HIVE):
                    self.do(hq.build(HIVE))


        #Hive technology
        if self.structures(HIVE).exists:
            if self.structures(SPAWNINGPOOL).ready.exists:
                pool = self.structures(SPAWNINGPOOL).ready.first
                abilities = await self.get_available_abilities(pool)
                if AbilityId.RESEARCH_ZERGLINGADRENALGLANDS in abilities and self.can_afford(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS):
                    self.do(pool(AbilityId.RESEARCH_ZERGLINGADRENALGLANDS))





    async def infestation_pit(self):
        if self.structures(LAIR).ready.exists  and not (self.structures(INFESTATIONPIT).exists or self.already_pending(INFESTATIONPIT)):
            if self.can_afford(INFESTATIONPIT):
                await self.build(INFESTATIONPIT, near=self.townhalls.first.position.towards(self.game_info.map_center,5))






#use this for playing main bot.
def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"), [
        Bot(Race.Zerg, Riceling()),
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


