"""
- Version 1.3: Due to the current Rush/Cheese Meta, I implemented a more defensive build order and in return deactivated
the 2-Base Immortal BO.

- Version 1.4: Switched from randomly chosen build orders to scouting based build order. Yet, still not completely with
a neural network but with basic rules, provided by a neural network.

- Version 1.5: Added a simple neural network to chose build orders based on scouting information.
Local tests with hundreds of games revealed that win rates compared to random choosing increased from 44% to 71%.
Bots used locally: YoBot, Tyr, Tyrz, 5minBot, BlinkerBot, NaughtyBot, SarsaBot, SeeBot, ramu,
Micromachine, Kagamine, AviloBot, EarlyAggro, Voidstar, ReeBot

- Version 1.6: Adapted early game rush defense in order to deal better with 12 pools (e.g. by CheeZerg).
Trained a new neural network with 730 games against the newest versions of most bots available.
Also refined scouting on 4 player maps and tuned the late game emergency strategy to prevent ties.

- Version 1.6.1: Bugfixes and new Model

- Version 1.7: Added a One-Base defence into Void-Ray build in order to deal with other very aggressive builds

- Version 1.7.1: Bugfixes and improved Voidray micro

- Version 1.7.2: Newly trained model

- Version 1.7.3 - 4: Small Bugfixes

- Version 1.7.5: Slightly improved Rush defence

- Version 1.8: Improved scouting with more scouting parameters, new model and various bug fixes / small improvements

- Version 1.9: Improved building placement and attack priorities. Oracle harass for Stargate build

- Version 2.0: Updated to Python 3.7.4 and to Burnys Python-sc2 vom 20.09.2019

- Version 2.1: Switched to game_step = 4. Added a Random Forrest Classifier and a manual BO-Choice to the chat to compare the results with those of the DNN
                Tried to increase survivalbility of the scout
"""
import math
import random
import time
import pickle
import keras
import numpy as np

import sc2
import sc2.units
import sc2.game_info
from sc2.constants import (
    ADEPT,
    ADEPTPHASESHIFT,
    ADEPTPHASESHIFT_ADEPTPHASESHIFT,
    ARCHON,
    ASSIMILATOR,
    CHRONOBOOSTENERGYCOST,
    COLOSSUS,
    CYBERNETICSCORE,
    DARKSHRINE,
    DARKTEMPLAR,
    EFFECT_CHRONOBOOSTENERGYCOST,
    EFFECT_VOIDRAYPRISMATICALIGNMENT,
    FORGE,
    FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1,
    FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2,
    FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3,
    FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1,
    FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2,
    FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3,
    FORGERESEARCH_PROTOSSSHIELDSLEVEL1,
    GATEWAY,
    GUARDIANSHIELD,
    GUARDIANSHIELD_GUARDIANSHIELD,
    HARVEST_RETURN,
    IMMORTAL,
    MORPH_ARCHON,
    MORPH_WARPGATE,
    NEXUS,
    OBSERVER,
    ORACLE,
    ORACLESTASISTRAP_ORACLEBUILDSTASISTRAP,
    ORACLESTASISTRAPACTIVATE_ACTIVATESTASISWARD,
    BUILD_STASISTRAP,
    BEHAVIOR_PULSARBEAMON,
    BEHAVIOR_PULSARBEAMOFF,
    PHOTONCANNON,
    PROBE,
    PYLON,
    RALLY_UNITS,
    RESEARCH_BLINK,
    RESEARCH_CHARGE,
    RESEARCH_EXTENDEDTHERMALLANCE,
    RESEARCH_PROTOSSGROUNDARMOR,
    RESEARCH_PROTOSSGROUNDWEAPONS,
    RESEARCH_PROTOSSSHIELDS,
    RESEARCH_WARPGATE,
    ROBOTICSBAY,
    ROBOTICSFACILITY,
    SENTRY,
    SHIELDBATTERY,
    STALKER,
    STARGATE,
    TWILIGHTCOUNCIL,
    VOIDRAY,
    WARPGATE,
    WARPGATETRAIN_ZEALOT,
    ZEALOT,
)
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb

HEADLESS = False


class MadBot(sc2.BotAI):
    def __init__(self):
        self.combinedActions = []
        self.MAX_WORKERS = 44
        self.do_something_after = 0
        self.do_something_scout = 0
        self.do_something_after_exe = 0
        self.do_something_after_trap1 = 0
        self.do_something_after_trap2 = 0
        self.MAX_EXE = 2
        self.MAX_GATES = 3
        self.MAX_ROBOS = 1
        self.MAX_GAS = 4
        self.enemy_natural = None
        self.first_gas_taken = False
        self.early_game_finished = False
        self.warpgate_started = False
        self.lance_started = False
        self.blink_started = False
        self.charge_started = False
        self.first_attack = False
        self.first_attack_finished = False
        self.gathered = False
        self.second_attack = False
        self.final_attack = False
        self.second_gathered = False
        self.proxy_built = False
        self.first_pylon_built = False
        self.armor_upgrade = 0
        self.weapon_upgrade = 0
        self.dts_detected = False
        self.harass_started = False

        self.scout = []
        self.remembered_enemy_units = []
        self.remembered_enemy_units_by_tag = {}
        self.units_to_ignore = [
            UnitTypeId.KD8CHARGE,
            UnitTypeId.EGG,
            UnitTypeId.LARVA,
            UnitTypeId.OVERLORD,
            UnitTypeId.BROODLING,
            UnitTypeId.INTERCEPTOR,
            UnitTypeId.CREEPTUMOR,
            UnitTypeId.CREEPTUMORBURROWED,
            UnitTypeId.CREEPTUMORQUEEN,
            UnitTypeId.CREEPTUMORMISSILE,
        ]
        self.units_to_ignore_defend = [
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
            UnitTypeId.CREEPTUMORMISSILE,
        ]

        self.defend_around = [PYLON, NEXUS, ASSIMILATOR]
        self.threat_proximity = 11
        self.prg = []
        self.prg2 = []
        self.back_home_early = False
        self.defend_early = False
        self.back_home = False
        self.defend = False
        self.k = 0

        self.train_data = []
        self.scout_data = []
        self.build_order = []

        self.won = False

        self.model = keras.models.load_model("MadAI_20_09_2019")
        self.RF_model = pickle.load(open('MadAI_RF_23_09_2019.sav', 'rb'))

        # Only run once at game start

    async def on_game_start(self):
        # self.build_order = random.randrange(0, 5)
        # if self.build_order == 0:
        #     print('--- 2-Base Colossus BO chosen ---')
        # elif self.build_order == 3:
        #     print('--- 2-Base Adept/Immortal BO chosen ---')
        # elif self.build_order == 2:
        #     print('--- 4-Gate Proxy BO chosen ---')
        # elif self.build_order == 1:
        #     print('--- One-Base Defend into DT BO chosen ---')
        # elif self.build_order == 4:
        #     print('--- One-Base Defend into Voidrays BO chosen ---')
        # else:
        #     print('--- ???????? ---')

        for worker in self.workers:
            closest_mineral_patch = self.mineral_field.closest_to(worker)
            self.do(worker.gather(closest_mineral_patch))


        # Save base locations for later
        self.k = len(self.enemy_start_locations)
        self.enemy_natural = await self.find_enemy_natural()
        # print('Enemy Natural @', self.enemy_natural)

    def on_end(self, game_result):
        print("OnGameEnd() was called.")
        if str(game_result) == "Result.Victory":
            result = 1
        else:
            result = 0
        if self.early_game_finished and result == 1:
            self.train_data.append(
                [
                    self.build_order,
                    self.scout_data[0],
                    self.scout_data[1],
                    self.scout_data[2],
                    self.scout_data[3],
                    self.scout_data[4],
                    self.scout_data[5],
                    self.scout_data[6],
                    self.scout_data[7],
                    self.scout_data[8],
                    self.scout_data[9],
                    self.scout_data[10],
                    self.scout_data[11],
                    self.scout_data[12],
                    self.scout_data[13],
                    self.scout_data[14],
                    self.scout_data[15],
                    self.scout_data[16],
                    self.scout_data[17],
                    self.scout_data[18],
                    self.scout_data[19],
                    self.scout_data[20],
                    self.scout_data[21],
                    self.scout_data[22],
                    self.scout_data[23],
                    self.scout_data[24],
                    self.scout_data[25],
                    self.scout_data[26],  # ])
                    self.scout_data[27],
                    self.scout_data[28],
                    self.scout_data[29],
                    self.scout_data[30],
                    self.scout_data[31],
                    self.scout_data[32],
                    self.scout_data[33],
                    self.scout_data[34],
                    self.scout_data[35],
                    self.scout_data[36],
                    self.scout_data[37],
                    self.scout_data[38],
                    self.scout_data[39],
                    self.scout_data[40],
                    self.scout_data[41],
                    self.scout_data[42],
                    self.scout_data[43],
                    self.scout_data[44],
                    self.scout_data[45],
                    self.scout_data[46],
                    self.scout_data[47],
                    self.scout_data[48],
                    self.scout_data[49],
                    self.scout_data[50],
                    self.scout_data[51],
                    self.scout_data[52],
                    self.scout_data[53],
                ]
            )

        np.save("data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))

    async def on_step(self, iteration):

        self.combinedActions = []

        if iteration == 0:
            print("Game started")
            await self.on_game_start()

        # Early Game
        if not self.early_game_finished:
            # print('--- Early Game Started ---')
            await self.build_workers()
            await self.build_pylons()
            await self.build_assimilators()
            await self.build_first_gates()
            await self.first_gate_units()
            await self.chrono_boost()
            await self.defend_early_rush()
            await self.distribute_workers()
            await self.remember_enemy_units()
        # Mid Game
        elif self.early_game_finished and not self.first_attack_finished and self.build_order == 0:
            self.MAX_GATES = 7
            await self.build_workers()
            await self.build_pylons()
            await self.distribute_workers()
            await self.build_assimilators()
            await self.chrono_boost()
            await self.defend_early_rush()
            await self.expand()
            await self.scout_obs()
            await self.morph_warpgates()
            await self.micro_units()
            await self.build_proxy_pylon_2base_colossus()
            await self.two_base_colossus_buildings()
            await self.two_base_colossus_upgrade()
            await self.two_base_colossus_offensive_force()
            await self.two_base_colossus_unit_control()
            await self.remember_enemy_units()
            await self.game_won()
        elif self.early_game_finished and self.build_order == 3:
            self.MAX_WORKERS = 32
            self.MAX_GAS = 2
            await self.build_workers()
            await self.build_pylons()
            await self.distribute_workers()
            await self.build_assimilators()
            await self.chrono_boost()
            await self.defend_early_rush()
            await self.expand()
            await self.morph_warpgates()
            await self.micro_units()
            await self.immortal_adept_buildings()
            await self.immortal_adept_offensive_force()
            await self.immortal_adept_unit_control()
            await self.build_proxy_pylon()
            await self.remember_enemy_units()
            await self.game_won()
        elif self.early_game_finished and self.build_order == 2:
            self.MAX_WORKERS = 20
            self.MAX_GATES = 4
            await self.build_workers()
            await self.build_pylons()
            await self.distribute_workers()
            await self.build_assimilators()
            await self.chrono_boost()
            await self.defend_early_rush()
            await self.morph_warpgates()
            await self.micro_units()
            await self.build_proxy_pylon_four_gate()
            await self.four_gate_buildings()
            await self.four_gate_offensive_force()
            await self.four_gate_unit_control()
            await self.remember_enemy_units()
            await self.game_won()
        elif self.early_game_finished and self.build_order == 1:
            self.MAX_WORKERS = 20
            await self.build_workers()
            await self.build_pylons()
            await self.chrono_boost()
            await self.defend_early_rush()
            await self.morph_warpgates()
            await self.build_assimilators()
            await self.micro_units()
            await self.build_proxy_pylon_dt()
            await self.one_base_dt_buildings()
            await self.one_base_dt_offensive_force()
            await self.dt_unit_control()
            await self.distribute_workers()
            await self.remember_enemy_units()
            await self.game_won()
        elif self.early_game_finished and self.build_order == 4:
            self.MAX_WORKERS = 20
            self.MAX_GATES = 2
            await self.build_workers()
            await self.build_pylons()
            await self.chrono_boost()
            await self.defend_early_rush()
            await self.morph_warpgates()
            await self.build_assimilators()
            await self.micro_units()
            await self.one_base_vr_buildings()
            await self.one_base_vr_offensive_force()
            await self.vr_unit_control()
            await self.distribute_workers()
            await self.remember_enemy_units()
            await self.game_won()
        # Late Game
        elif self.first_attack_finished and self.build_order == 0:
            self.MAX_WORKERS = 50
            self.MAX_EXE = 3  # Increase Exes to 3 TODO: and build a new one every ~3 Minutes
            self.MAX_GATES = 8
            await self.build_workers()
            await self.build_pylons()
            await self.distribute_workers()
            await self.build_assimilators()
            await self.chrono_boost()
            await self.expand()
            await self.scout_obs()
            await self.morph_warpgates()
            await self.micro_units()
            await self.game_won()
            if len(self.structures(NEXUS)) == 3:
                await self.two_base_colossus_offensive_force()
                await self.two_base_colossus_unit_control_lategame()
                await self.two_base_colossus_upgrade_lategame()
        # Destroy Terran BM after 20min
        if self.time / 60 >= 20:
            self.build_order = 99
            self.MAX_EXE = 4
            self.MAX_GAS = 8
            self.MAX_WORKERS = 50
            await self.distribute_workers()
            await self.build_pylons()
            await self.expand()
            await self.build_assimilators()
            await self.destroy_lifted_buildings()

    async def game_won(self):
        if (
            not self.won
            and len(self.enemy_structures(NEXUS))
            + len(self.enemy_structures(UnitTypeId.COMMANDCENTER))
            + len(self.enemy_structures(UnitTypeId.ORBITALCOMMAND))
            + len(self.enemy_structures(UnitTypeId.HATCHERY))
            + len(self.enemy_structures(UnitTypeId.LAIR))
            + len(self.enemy_structures(UnitTypeId.HIVE))
            == 0
        ):
            self.won = True
            self.train_data.append(
                [
                    self.build_order,
                    self.scout_data[0],
                    self.scout_data[1],
                    self.scout_data[2],
                    self.scout_data[3],
                    self.scout_data[4],
                    self.scout_data[5],
                    self.scout_data[6],
                    self.scout_data[7],
                    self.scout_data[8],
                    self.scout_data[9],
                    self.scout_data[10],
                    self.scout_data[11],
                    self.scout_data[12],
                    self.scout_data[13],
                    self.scout_data[14],
                    self.scout_data[15],
                    self.scout_data[16],
                    self.scout_data[17],
                    self.scout_data[18],
                    self.scout_data[19],
                    self.scout_data[20],
                    self.scout_data[21],
                    self.scout_data[22],
                    self.scout_data[23],
                    self.scout_data[24],
                    self.scout_data[25],
                    self.scout_data[26],  # ])
                    self.scout_data[27],
                    self.scout_data[28],
                    self.scout_data[29],
                    self.scout_data[30],
                    self.scout_data[31],
                    self.scout_data[32],
                    self.scout_data[33],
                    self.scout_data[34],
                    self.scout_data[35],
                    self.scout_data[36],
                    self.scout_data[37],
                    self.scout_data[38],
                    self.scout_data[39],
                    self.scout_data[40],
                    self.scout_data[41],
                    self.scout_data[42],
                    self.scout_data[43],
                    self.scout_data[44],
                    self.scout_data[45],
                    self.scout_data[46],
                    self.scout_data[47],
                    self.scout_data[48],
                    self.scout_data[49],
                    self.scout_data[50],
                    self.scout_data[51],
                    self.scout_data[52],
                    self.scout_data[53],
                ]
            )

            # np.save("data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))

    async def build_workers(self):
        if (len(self.structures(NEXUS)) * 22) > len(self.units(PROBE)) and len(self.units(PROBE)) < self.MAX_WORKERS:
            for nexus in self.structures(NEXUS).ready.idle:
                if self.can_afford(PROBE):
                    self.do(nexus.train(PROBE))

    async def build_pylons(self):
        if self.supply_used == 14 and self.can_afford(PYLON) and not self.first_pylon_built:
            # pylon_placement_positions = self.main_base_ramp.corner_depots
            # nexus = self.structures(NEXUS)
            # pylon_placement_positions = {d for d in pylon_placement_positions if nexus.closest_distance_to(d) > 1}
            # target_pylon_location = pylon_placement_positions.pop()
            target_pylon_location = self.main_base_ramp.protoss_wall_pylon
            await self.build(PYLON, near=target_pylon_location)
            self.first_pylon_built = True
        elif (
            17 < self.supply_used <= 20
            and not self.already_pending(PYLON)
            and self.already_pending(GATEWAY)
            and self.supply_left < 6
        ):
            nexuses = self.structures(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(PYLON, near=self.structures(NEXUS).first.position.towards(self.game_info.map_center, 5))
                    # Pylon Block enemy expansion
                    # p = await self.find_placement(PYLON, self.enemy_natural, 4, False, 1)
                    # if p is None:
                    #     return False
                    #
                    # builder = self.units(PROBE).furthest_to(self.structures(NEXUS).first)
                    # if builder is None:
                    #     return False
                    # self.do(builder.build(PYLON, p), subtract_cost=True)

        elif (
            self.structures(NEXUS).amount > 1
            and self.can_afford(PYLON)
            and not self.already_pending(PYLON)
            and self.supply_used < 36
            and self.supply_left < 12
        ):
            await self.build(PYLON, near=self.structures(NEXUS)[1].position.towards(self.game_info.map_center, 5))
        elif 20 < self.supply_used < 61 and self.supply_left < 8 and not self.already_pending(PYLON):
            nexuses = self.structures(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(
                        PYLON,
                        near=nexuses.random.position.random_on_distance(random.randrange(1, 15)),
                        max_distance=10,
                        random_alternative=False,
                        placement_step=3,
                    )
        elif 60 < self.supply_used < 188 and self.supply_left < 16 and not self.already_pending(PYLON):
            nexuses = self.structures(NEXUS).ready
            if nexuses.exists:
                if self.can_afford(PYLON):
                    await self.build(
                        PYLON,
                        near=nexuses.random.position.towards(self.game_info.map_center, random.randrange(1, 20)),
                        max_distance=10,
                        random_alternative=False,
                        placement_step=3,
                    )

    async def build_assimilators(self):
        if len(self.structures(ASSIMILATOR)) < self.MAX_GAS:
            for nexus in self.structures(NEXUS).ready:
                vaspenes = self.vespene_geyser.closer_than2(15.0, nexus)
                for vaspene in vaspenes:
                    if not self.can_afford(ASSIMILATOR):
                        break
                    worker = self.select_build_worker(vaspene.position)
                    if worker is None:
                        break
                    if not self.gas_buildings or not self.gas_buildings.closer_than2(1, vaspene):
                        if self.supply_used >= 17 and not self.first_gas_taken:
                            self.do(worker.build(ASSIMILATOR, vaspene))

                            self.first_gas_taken = True
                            break
                        elif self.supply_used >= 25 and self.first_gas_taken:
                            self.do(worker.build(ASSIMILATOR, vaspene))

                            break
                        elif self.supply_used >= 35:
                            self.do(worker.build(ASSIMILATOR, vaspene))
        # if self.structures(ASSIMILATOR).ready.exists: # Sofort 3 Arbeiter zuweisen wenn Assimilator fertig

    async def build_first_gates(self):
        if self.structures(PYLON).ready.exists:
            if (
                self.can_afford(GATEWAY)
                and self.supply_used >= 16
                and not self.structures(GATEWAY)
                and not self.already_pending(GATEWAY)
            ):
                await self.build(
                    GATEWAY,
                    near=self.main_base_ramp.protoss_wall_buildings[0]
                )
                # # Use Gateway Probe as Scout
                # self.scout = self.units(PROBE).furthest_to(self.structures(NEXUS).first)
                # move_to = self.enemy_start_locations[0].random_on_distance(random.randrange(1, 3))
                # print(move_to)
                # self.do(self.scout.move(move_to))

            if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(
                        CYBERNETICSCORE,
                        near=self.main_base_ramp.protoss_wall_buildings[1]
                    )

            if (
                self.structures(CYBERNETICSCORE).ready.exists
                and self.can_afford(RESEARCH_WARPGATE)
                and not self.warpgate_started
            ):
                ccore = self.structures(CYBERNETICSCORE).ready.first
                self.do(ccore(RESEARCH_WARPGATE))
                self.warpgate_started = True

    async def first_gate_units(self):
        if self.structures(GATEWAY).ready.exists:
            for gw in self.structures(GATEWAY).ready.idle:
                if self.can_afford(ZEALOT) and self.supply_used <= 22:
                    self.do(gw.train(ZEALOT))
                elif (
                    self.can_afford(ZEALOT)
                    and self.supply_left > 1
                    and not self.structures(CYBERNETICSCORE).ready.exists
                    and (
                        len(self.enemy_structures(UnitTypeId.HATCHERY)) >= 1
                        or len(self.remembered_enemy_units.of_type(UnitTypeId.ZERGLING)) > 1
                    )
                ):
                    self.do(gw.train(ZEALOT))
                elif self.minerals > 525 and self.supply_left > 1:
                    self.do(gw.train(ZEALOT))
                if self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 0:
                    if (
                        len(self.enemy_structures(UnitTypeId.HATCHERY)) >= 1
                        or len(self.remembered_enemy_units.of_type(UnitTypeId.ZERGLING)) > 1
                    ):
                        self.do(gw.train(ZEALOT))
                    else:
                        self.do(gw.train(STALKER))
                if self.structures(CYBERNETICSCORE).ready.exists and not self.early_game_finished:
                    print("--- Early Game Finished --- @:", self.time)
                    workercount = len(
                        self.remembered_enemy_units.of_type({UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV})
                    )

                    enemy_pylon_pos = []
                    for pylon in range(len(self.enemy_structures(PYLON))):
                        enemy_pylon_pos.append(self.enemy_structures(PYLON)[pylon].position)
                    enemy_gateway_pos = []
                    for gateway in range(len(self.enemy_structures(GATEWAY))):
                        enemy_gateway_pos.append(self.enemy_structures(GATEWAY)[gateway].position)
                    enemy_forge_pos = []
                    for forge in range(len(self.enemy_structures(FORGE))):
                        enemy_forge_pos.append(self.enemy_structures(FORGE)[forge].position)
                    enemy_cannon_pos = []
                    for cannon in range(len(self.enemy_structures(PHOTONCANNON))):
                        enemy_cannon_pos.append(self.enemy_structures(PHOTONCANNON)[cannon].position)
                    enemy_depot_pos = []
                    for depot in range(len(self.enemy_structures(UnitTypeId.SUPPLYDEPOT))):
                        enemy_depot_pos.append(self.enemy_structures(UnitTypeId.SUPPLYDEPOT)[depot].position)
                    enemy_depotlow_pos = []
                    for depotlow in range(len(self.enemy_structures(UnitTypeId.SUPPLYDEPOTLOWERED))):
                        enemy_depotlow_pos.append(
                            self.enemy_structures(UnitTypeId.SUPPLYDEPOTLOWERED)[depotlow].position
                        )
                    enemy_bunker_pos = []
                    for bunker in range(len(self.enemy_structures(UnitTypeId.BUNKER))):
                        enemy_bunker_pos.append(self.enemy_structures(UnitTypeId.BUNKER)[bunker].position)
                    enemy_barracks_pos = []
                    for barracks in range(len(self.enemy_structures(UnitTypeId.BARRACKS))):
                        enemy_barracks_pos.append(self.enemy_structures(UnitTypeId.BARRACKS)[barracks].position)
                    enemy_factory_pos = []
                    for factory in range(len(self.enemy_structures(UnitTypeId.FACTORY))):
                        enemy_factory_pos.append(self.enemy_structures(UnitTypeId.FACTORY)[factory].position)
                    enemy_pool_pos = []
                    for pool in range(len(self.enemy_structures(UnitTypeId.SPAWNINGPOOL))):
                        enemy_pool_pos.append(self.enemy_structures(UnitTypeId.SPAWNINGPOOL)[pool].position)
                    enemy_spine_pos = []
                    for spine in range(len(self.enemy_structures(UnitTypeId.SPINECRAWLER))):
                        enemy_spine_pos.append(self.enemy_structures(UnitTypeId.SPINECRAWLER)[spine].position)

                    if len(self.enemy_structures(PYLON)) >= 1:
                        pylon1_pos = enemy_pylon_pos[0][0] + enemy_pylon_pos[0][1]
                    else:
                        pylon1_pos = 0
                    if len(self.enemy_structures(PYLON)) >= 2:
                        pylon2_pos = enemy_pylon_pos[1][0] + enemy_pylon_pos[1][1]
                    else:
                        pylon2_pos = 0
                    if len(self.enemy_structures(PYLON)) >= 3:
                        pylon3_pos = enemy_pylon_pos[2][0] + enemy_pylon_pos[2][1]
                    else:
                        pylon3_pos = 0
                    if len(self.enemy_structures(GATEWAY)) >= 1:
                        gate1_pos = enemy_gateway_pos[0][0] + enemy_gateway_pos[0][1]
                    else:
                        gate1_pos = 0
                    if len(self.enemy_structures(GATEWAY)) >= 2:
                        gate2_pos = enemy_gateway_pos[1][0] + enemy_gateway_pos[1][1]
                    else:
                        gate2_pos = 0
                    if len(self.enemy_structures(FORGE)) >= 1:
                        forge1_pos = enemy_forge_pos[0][0] + enemy_forge_pos[0][1]
                    else:
                        forge1_pos = 0
                    if len(self.enemy_structures(PHOTONCANNON)) >= 1:
                        cannon1_pos = enemy_cannon_pos[0][0] + enemy_cannon_pos[0][1]
                    else:
                        cannon1_pos = 0
                    if len(self.enemy_structures(PHOTONCANNON)) >= 2:
                        cannon2_pos = enemy_cannon_pos[1][0] + enemy_cannon_pos[1][1]
                    else:
                        cannon2_pos = 0
                    if len(self.enemy_structures(PHOTONCANNON)) >= 3:
                        cannon3_pos = enemy_cannon_pos[2][0] + enemy_cannon_pos[2][1]
                    else:
                        cannon3_pos = 0
                    if len(self.enemy_structures(PHOTONCANNON)) >= 4:
                        cannon4_pos = enemy_cannon_pos[3][0] + enemy_cannon_pos[3][1]
                    else:
                        cannon4_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SUPPLYDEPOT)) >= 1:
                        depot1_pos = enemy_depot_pos[0][0] + enemy_depot_pos[0][1]
                    else:
                        depot1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SUPPLYDEPOT)) >= 2:
                        depot2_pos = enemy_depot_pos[1][0] + enemy_depot_pos[1][1]
                    else:
                        depot2_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SUPPLYDEPOT)) >= 3:
                        depot3_pos = enemy_depot_pos[2][0] + enemy_depot_pos[2][1]
                    else:
                        depot3_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SUPPLYDEPOTLOWERED)) >= 1:
                        depotlow1_pos = enemy_depotlow_pos[0][0] + enemy_depotlow_pos[0][1]
                    else:
                        depotlow1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SUPPLYDEPOTLOWERED)) >= 2:
                        depotlow2_pos = enemy_depotlow_pos[1][0] + enemy_depotlow_pos[1][1]
                    else:
                        depotlow2_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SUPPLYDEPOTLOWERED)) >= 3:
                        depotlow3_pos = enemy_depotlow_pos[2][0] + enemy_depotlow_pos[2][1]
                    else:
                        depotlow3_pos = 0
                    if len(self.enemy_structures(UnitTypeId.BUNKER)) >= 1:
                        bunker1_pos = enemy_bunker_pos[0][0] + enemy_bunker_pos[0][1]
                    else:
                        bunker1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.BARRACKS)) >= 1:
                        barracks1_pos = enemy_barracks_pos[0][0] + enemy_barracks_pos[0][1]
                    else:
                        barracks1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.BARRACKS)) >= 2:
                        barracks2_pos = enemy_barracks_pos[1][0] + enemy_barracks_pos[1][1]
                    else:
                        barracks2_pos = 0
                    if len(self.enemy_structures(UnitTypeId.BARRACKS)) >= 3:
                        barracks3_pos = enemy_barracks_pos[2][0] + enemy_barracks_pos[2][1]
                    else:
                        barracks3_pos = 0
                    if len(self.enemy_structures(UnitTypeId.FACTORY)) >= 1:
                        factory1_pos = enemy_factory_pos[0][0] + enemy_factory_pos[0][1]
                    else:
                        factory1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SPAWNINGPOOL)) >= 1:
                        pool1_pos = enemy_pool_pos[0][0] + enemy_pool_pos[0][1]
                    else:
                        pool1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SPINECRAWLER)) >= 1:
                        spine1_pos = enemy_spine_pos[0][0] + enemy_spine_pos[0][1]
                    else:
                        spine1_pos = 0
                    if len(self.enemy_structures(UnitTypeId.SPINECRAWLER)) >= 2:
                        spine2_pos = enemy_spine_pos[1][0] + enemy_spine_pos[1][1]
                    else:
                        spine2_pos = 0

                    self.scout_data = [
                        len(self.enemy_structures(NEXUS)),
                        len(self.enemy_structures(PYLON)),
                        len(self.enemy_structures(GATEWAY)),
                        len(self.enemy_structures(CYBERNETICSCORE)),
                        len(self.enemy_structures(ASSIMILATOR)),
                        len(self.enemy_structures(UnitTypeId.COMMANDCENTER)),
                        len(self.enemy_structures(UnitTypeId.ORBITALCOMMAND)),
                        len(self.enemy_structures(UnitTypeId.SUPPLYDEPOT)),
                        len(self.enemy_structures(UnitTypeId.SUPPLYDEPOTLOWERED)),
                        len(self.enemy_structures(UnitTypeId.BARRACKS)),
                        len(self.enemy_structures(UnitTypeId.TECHLAB)),
                        len(self.enemy_structures(UnitTypeId.REACTOR)),
                        len(self.enemy_structures(UnitTypeId.REFINERY)),
                        len(self.enemy_structures(UnitTypeId.FACTORY)),
                        len(self.enemy_structures(UnitTypeId.HATCHERY)),
                        len(self.enemy_structures(UnitTypeId.SPINECRAWLER)),
                        len(self.enemy_structures(UnitTypeId.SPAWNINGPOOL)),
                        len(self.enemy_structures(UnitTypeId.ROACHWARREN)),
                        len(self.enemy_structures(UnitTypeId.EXTRACTOR)),
                        workercount,
                        len(self.remembered_enemy_units.of_type(UnitTypeId.ZEALOT)),
                        len(self.remembered_enemy_units.of_type(UnitTypeId.STALKER)),
                        len(self.remembered_enemy_units.of_type(UnitTypeId.MARINE)),
                        len(self.remembered_enemy_units.of_type(UnitTypeId.REAPER)),
                        len(self.remembered_enemy_units.of_type(UnitTypeId.ZERGLING)),
                        len(self.remembered_enemy_units.of_type(UnitTypeId.ROACH)),
                        len(self.enemy_structures(UnitTypeId.PHOTONCANNON)),
                        len(self.enemy_structures(UnitTypeId.BUNKER)),
                        len(self.enemy_structures(FORGE)),
                        self.enemy_start_locations[0][0] + self.enemy_start_locations[0][1],
                        pylon1_pos,
                        pylon2_pos,
                        pylon3_pos,
                        gate1_pos,
                        gate2_pos,
                        forge1_pos,
                        cannon1_pos,
                        cannon2_pos,
                        cannon3_pos,
                        cannon4_pos,
                        depot1_pos,
                        depot2_pos,
                        depot3_pos,
                        depotlow1_pos,
                        depotlow2_pos,
                        depotlow3_pos,
                        bunker1_pos,
                        barracks1_pos,
                        barracks2_pos,
                        barracks3_pos,
                        factory1_pos,
                        pool1_pos,
                        spine1_pos,
                        spine2_pos,
                    ]

                    # print(self.scout_data)
                    self.early_game_finished = True
                    # await self.chat_send("(glhf) MadAI v2.1")

                    choice_data = [
                        self.scout_data[0],
                        self.scout_data[1],
                        self.scout_data[2],
                        self.scout_data[3],
                        self.scout_data[4],
                        self.scout_data[5],
                        self.scout_data[6],
                        self.scout_data[7],
                        self.scout_data[8],
                        self.scout_data[9],
                        self.scout_data[10],
                        self.scout_data[11],
                        self.scout_data[12],
                        self.scout_data[13],
                        self.scout_data[14],
                        self.scout_data[15],
                        self.scout_data[16],
                        self.scout_data[17],
                        self.scout_data[18],
                        self.scout_data[19],
                        self.scout_data[20],
                        self.scout_data[21],
                        self.scout_data[22],
                        self.scout_data[23],
                        self.scout_data[24],
                        self.scout_data[25],
                        self.scout_data[26],
                        self.scout_data[27],
                        self.scout_data[28],
                        self.scout_data[29],
                        self.scout_data[30],
                        self.scout_data[31],
                        self.scout_data[32],
                        self.scout_data[33],
                        self.scout_data[34],
                        self.scout_data[35],
                        self.scout_data[36],
                        self.scout_data[37],
                        self.scout_data[38],
                        self.scout_data[39],
                        self.scout_data[40],
                        self.scout_data[41],
                        self.scout_data[42],
                        self.scout_data[43],
                        self.scout_data[44],
                        self.scout_data[45],
                        self.scout_data[46],
                        self.scout_data[47],
                        self.scout_data[48],
                        self.scout_data[49],
                        self.scout_data[50],
                        self.scout_data[51],
                        self.scout_data[52],
                        self.scout_data[53],
                    ]

                    new_choice_data = np.array(choice_data).reshape(-1, 54, 1)

                    prediction = self.model.predict(new_choice_data)
                    # choice = np.argmax(prediction[0])
                    # print(prediction[0])
                    # self.build_order = choice

                    self.build_order = random.randrange(0, 5)

                    RF_predictions = self.RF_model.predict_proba([choice_data])
                    # await self.chat_send("Random Forest results: " + str(RF_predictions[0]))

                    if len(self.enemy_structures(NEXUS)) > 1 or len(self.enemy_structures(UnitTypeId.COMMANDCENTER)) > 1 or len(self.enemy_structures(UnitTypeId.COMMANDCENTER))+len(self.enemy_structures(UnitTypeId.ORBITALCOMMAND)) > 1 or len(self.enemy_structures(UnitTypeId.HATCHERY)) > 1:
                        manual_0 = 0
                        manual_1 = 0
                        manual_2 = 1
                        manual_3 = 0
                        manual_4 = 0
                        # await self.chat_send(
                        #     "Greedy Expasion detected!"
                        # )
                    elif len(self.enemy_structures(GATEWAY)) > 2 or len(self.enemy_structures(UnitTypeId.BARRACKS)) > 2 or len(self.remembered_enemy_units.of_type(UnitTypeId.ZERGLING)) > 2:
                        manual_0 = 0
                        manual_1 = 0.5
                        manual_2 = 0
                        manual_3 = 0
                        manual_4 = 0.5
                        # await self.chat_send(
                        #     "Aggressive build detected!"
                        # )
                    elif len(self.enemy_structures(UnitTypeId.SPINECRAWLER)) > 0 or len(self.enemy_structures(UnitTypeId.PHOTONCANNON)) > 0 or len(self.enemy_structures(UnitTypeId.BUNKER)) > 0 or len(self.enemy_structures(FORGE)) > 0:
                        manual_0 = 0.5
                        manual_1 = 0
                        manual_2 = 0
                        manual_3 = 0.5
                        manual_4 = 0
                        # await self.chat_send(
                        #     "Turtle build detected!"
                        # )
                    else:
                        manual_0 = 0.2
                        manual_1 = 0.2
                        manual_2 = 0.2
                        manual_3 = 0.2
                        manual_4 = 0.2
                        # await self.chat_send("Scout found nothing interesting!")

                    await self.chat_send(
                        "2-Base Colossus: ["
                        + str(round(prediction[0][0] * 100, 2))
                        + " / "
                        + str(round(RF_predictions[0][0] * 100, 2))
                        + " / "
                        + str(manual_0 * 100)
                        + " / "
                        + str(round((prediction[0][0] + RF_predictions[0][0] + manual_0) * 100 / 3, 2))
                        + "]; 1-Base DTs: ["
                        + str(round(prediction[0][1] * 100, 2))
                        + " / "
                        + str(round(RF_predictions[0][1] * 100, 2))
                        + " / "
                        + str(manual_1 * 100)
                        + " / "
                        + str(round((prediction[0][1] + RF_predictions[0][1] + manual_1) * 100 / 3, 2))
                        + "]; 4-Gate Proxy: ["
                        + str(round(prediction[0][2] * 100, 2))
                        + " / "
                        + str(round(RF_predictions[0][2] * 100, 2))
                        + " / "
                        + str(manual_2 * 100)
                        + " / "
                        + str(round((prediction[0][2] + RF_predictions[0][2] + manual_2) * 100 / 3, 2))
                        + "]; 2-Base Immortals: ["
                        + str(round(prediction[0][3] * 100, 2))
                        + " / "
                        + str(round(RF_predictions[0][3] * 100, 2))
                        + " / "
                        + str(manual_3 * 100)
                        + " / "
                        + str(round((prediction[0][3] + RF_predictions[0][3] + manual_3) * 100 / 3, 2))
                        + "]; 1-Base Voidrays: ["
                        + str(round(prediction[0][4] * 100, 2))
                        + " / "
                        + str(round(RF_predictions[0][4] * 100, 2))
                        + " / "
                        + str(manual_4 * 100)
                        + " / "
                        + str(round((prediction[0][4] + RF_predictions[0][4] + manual_4) * 100 / 3, 2))
                        + "]"
                    )
                    choice = np.argmax([round((prediction[0][0] + RF_predictions[0][0] + manual_0) * 100 / 3, 2),
                                        round((prediction[0][1] + RF_predictions[0][1] + manual_1) * 100 / 3, 2),
                                        round((prediction[0][2] + RF_predictions[0][2] + manual_2) * 100 / 3, 2),
                                        round((prediction[0][3] + RF_predictions[0][3] + manual_3) * 100 / 3, 2),
                                        round((prediction[0][4] + RF_predictions[0][4] + manual_4) * 100 / 3, 2)])

                    if choice == 0:
                        print("--- 2-Base Colossus BO chosen ---")
                        await self.chat_send(
                            "(glhf) MadAI v2.1: 2-Base Colossus BO chosen!"
                        )
                    elif choice == 1:
                        print("--- One-Base Defend into DT BO chosen ---")
                        await self.chat_send(
                            "(glhf) MadAI v2.1: Rush-Defend into DT BO chosen!"
                        )
                    elif choice == 2:
                        print("--- 4-Gate Proxy BO chosen ---")
                        await self.chat_send(
                            "(glhf) MadAI v2.1: 4-Gate Proxy BO chosen!"
                        )
                    elif choice == 3:
                        print("--- 2-Base Immortal BO chosen ---")
                        await self.chat_send(
                            "(glhf) MadAI v2.1: 2-Base Immortal BO chosen!"
                        )
                    elif choice == 4:
                        print("--- One-Base Defend into Voidrays BO chosen ---")
                        await self.chat_send(
                            "(glhf) MadAI v2.1: Rush-Defend into Voidrays BO chosen!"
                        )

                    # if self.build_order == 0:
                    #     print("--- 2-Base Colossus BO chosen ---")
                    #     await self.chat_send(
                    #         "(glhf) MadAI v2.1: 2-Base Colossus BO chosen! Certainties: 2-Base Colossus: "
                    #         + str(round(prediction[0][0] * 100, 2))
                    #         + "%; "
                    #         + "1-Base DTs: "
                    #         + str(round(prediction[0][1] * 100, 2))
                    #         + "%; "
                    #         + "4-Gate Proxy: "
                    #         + str(round(prediction[0][2] * 100, 2))
                    #         + "%; "
                    #         + "2-Base Immortals: "
                    #         + str(round(prediction[0][3] * 100, 2))
                    #         + "%; "
                    #         + "1-Base Voidrays: "
                    #         + str(round(prediction[0][4] * 100, 2))
                    #         + "%"
                    #     )
                    # elif self.build_order == 1:
                    #     print("--- One-Base Defend into DT BO chosen ---")
                    #     await self.chat_send(
                    #         "(glhf) MadAI v2.1: Rush-Defend into DT BO chosen! Certainties: 2-Base Colossus: "
                    #         + str(round(prediction[0][0] * 100, 2))
                    #         + "%; "
                    #         + "1-Base DTs: "
                    #         + str(round(prediction[0][1] * 100, 2))
                    #         + "%; "
                    #         + "4-Gate Proxy: "
                    #         + str(round(prediction[0][2] * 100, 2))
                    #         + "%; "
                    #         + "2-Base Immortals: "
                    #         + str(round(prediction[0][3] * 100, 2))
                    #         + "%; "
                    #         + "1-Base Voidrays: "
                    #         + str(round(prediction[0][4] * 100, 2))
                    #         + "%"
                    #     )
                    # elif self.build_order == 2:
                    #     print("--- 4-Gate Proxy BO chosen ---")
                    #     await self.chat_send(
                    #         "(glhf) MadAI v2.1: 4-Gate Proxy BO chosen! Certainties: 2-Base Colossus: "
                    #         + str(round(prediction[0][0] * 100, 2))
                    #         + "%; "
                    #         + "1-Base DTs: "
                    #         + str(round(prediction[0][1] * 100, 2))
                    #         + "%; "
                    #         + "4-Gate Proxy: "
                    #         + str(round(prediction[0][2] * 100, 2))
                    #         + "%; "
                    #         + "2-Base Immortals: "
                    #         + str(round(prediction[0][3] * 100, 2))
                    #         + "%; "
                    #         + "1-Base Voidrays: "
                    #         + str(round(prediction[0][4] * 100, 2))
                    #         + "%"
                    #     )
                    # elif self.build_order == 3:
                    #     print("--- 2-Base Immortal BO chosen ---")
                    #     await self.chat_send(
                    #         "(glhf) MadAI v2.1: 2-Base Immortal BO chosen! Certainties: 2-Base Colossus: "
                    #         + str(round(prediction[0][0] * 100, 2))
                    #         + "%; "
                    #         + "1-Base DTs: "
                    #         + str(round(prediction[0][1] * 100, 2))
                    #         + "%; "
                    #         + "4-Gate Proxy: "
                    #         + str(round(prediction[0][2] * 100, 2))
                    #         + "%; "
                    #         + "2-Base Immortals: "
                    #         + str(round(prediction[0][3] * 100, 2))
                    #         + "%; "
                    #         + "1-Base Voidrays: "
                    #         + str(round(prediction[0][4] * 100, 2))
                    #         + "%"
                    #     )
                    # elif self.build_order == 4:
                    #     print("--- One-Base Defend into Voidrays BO chosen ---")
                    #     await self.chat_send(
                    #         "(glhf) MadAI v2.1: Rush-Defend into Voidrays BO chosen! Certainties: 2-Base Colossus: "
                    #         + str(round(prediction[0][0] * 100, 2))
                    #         + "%; "
                    #         + "1-Base DTs: "
                    #         + str(round(prediction[0][1] * 100, 2))
                    #         + "%; "
                    #         + "4-Gate Proxy: "
                    #         + str(round(prediction[0][2] * 100, 2))
                    #         + "%; "
                    #         + "2-Base Immortals: "
                    #         + str(round(prediction[0][3] * 100, 2))
                    #         + "%; "
                    #         + "1-Base Voidrays: "
                    #         + str(round(prediction[0][4] * 100, 2))
                    #         + "%"
                    #     )
                    # else:
                    #     self.build_order = random.randrange(0, 5)
                    #     await self.chat_send("(glhf) MadBot v2.1: Neural Network broke, choosing random Build Order")

                    # await self.chat_send(
                    #     "Random Forest results: 2-Base Colossus: " + str(RF_predictions[0][0])*100
                    #     + "%; "
                    #     + "1-Base DTs: "
                    #     + str(RF_predictions[0][1])*100
                    #     + "%; "
                    #     + "4-Gate Proxy: "
                    #     + str(RF_predictions[0][2]) * 100
                    #     + "%; "
                    #     + "2-Base Immortals: "
                    #     + str(RF_predictions[0][3]) * 100
                    #     + "%; "
                    #     + "1-Base Voirdrays: "
                    #     + str(RF_predictions[0][4]) * 100
                    #     + "% "
                    # )
                    #print(self.scout_data)

    async def defend_early_rush(self):
        # defend if there is a 12 pool or worker rush
        if len(self.units(ZEALOT)) < 2:
            for zl in self.units(ZEALOT).idle:
                self.do(
                    zl.attack(
                        self.structures(NEXUS)
                        .closest_to(self.game_info.map_center)
                        .position.towards(self.game_info.map_center, random.randrange(8, 10))
                    )
                )

        if (
            len(self.units(ZEALOT)) + len(self.units(STALKER)) + len(self.units(ADEPT)) < 2 and self.enemy_units
        ) or self.back_home_early:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore_defend
                    ).closer_than2(11, structure.position)
                    # print(threats)
                    if threats:
                        break
                if threats:
                    break
            # print(len(threats))
            # Don't chase the enemy with probes!
            # if self.structures(NEXUS).exists and self.defend_early:
            #     for pr in self.units(PROBE).ready.further_than(15, self.structures(NEXUS).first.position):
            #         if len(self.scout) == 1 and pr.tag != self.scout[0].tag:
            #             self.do(
            #                 pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
            #             )
            #         elif len(self.scout) == 0:
            #             self.do(
            #                 pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
            #             )
            # Full rush incoming. Pull all probes
            if len(threats) >= 7:
                # print('Full')
                self.defend_early = True
                self.back_home_early = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for pr in self.units(PROBE):
                    if pr.shield_percentage > 0.1:
                        self.do(pr.attack(defence_target))
                    elif self.structures(NEXUS).exists:
                        self.do(
                            pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
                        )
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            # 12 Pool or some kind of stuff
            elif 1 < len(threats) < 7 and not self.prg:
                # print('Half')
                self.defend_early = True
                self.back_home_early = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                self.prg = self.units(PROBE).random_group_of(round(len(self.units(PROBE)) / 3))
                for pr in self.prg:
                    if pr.shield_percentage > 0.1:
                        self.do(pr.attack(defence_target))
                    elif self.structures(NEXUS).exists:
                        self.do(
                            pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
                        )
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif 1 < len(threats) < 7 and self.prg:
                #print('Half')
                self.defend_early = True
                self.back_home_early = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for pr in self.prg:
                    if pr.shield_percentage > 0.1:
                        self.do(pr.attack(defence_target))
                    elif self.structures(NEXUS).exists:
                        self.do(
                            pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
                        )
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            # Just some harass. Pull only two probes
            elif len(threats) == 1 and not self.defend_early and not self.prg2 and len(self.units(PROBE)) > 1:
                #print('Two')
                self.defend_early = True
                self.back_home_early = True
                defence_target = threats[0]
                self.prg2 = self.units(PROBE).random_group_of(2)
                for pr in self.prg2:
                    self.do(pr.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif len(threats) == 1 and self.prg2 and len(self.units(PROBE)) > 1:
                #print('Three')
                self.defend_early = True
                self.back_home_early = True
                defence_target = threats[0]
                for pr in self.prg2:
                    self.do(pr.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            # Threat is gone for now. Go back to work
            elif (self.prg or self.prg2) and not threats and self.back_home_early:
                #print('Back1')
                if self.structures(NEXUS).exists:
                    if self.prg:
                        for pr in self.prg:
                            self.do(
                                pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
                            )
                        for zl in self.units(ZEALOT):
                            self.do(
                                zl.move(
                                    self.structures(NEXUS)
                                    .closest_to(self.game_info.map_center)
                                    .position.towards(self.game_info.map_center, random.randrange(8, 10))
                                )
                            )
                        self.prg = []
                    elif self.prg2:
                        for pr in self.prg2:
                            self.do(
                                pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
                            )
                        for zl in self.units(ZEALOT):
                            self.do(
                                zl.move(
                                    self.structures(NEXUS)
                                    .closest_to(self.game_info.map_center)
                                    .position.towards(self.game_info.map_center, random.randrange(8, 10))
                                )
                            )
                        self.prg2 = []

                self.defend_early = False
                self.back_home_early = False
            # Everything is fine again. Go back to work
            elif not threats and self.back_home_early:
                #print('Back2')
                self.back_home_early = False
                self.defend_early = False
                if self.structures(NEXUS).exists:
                    for pr in self.units(PROBE):
                        self.do(
                            pr.gather(self.mineral_field.closest_to(self.structures(NEXUS).first))
                        )
                    for zl in self.units(ZEALOT):
                        self.do(
                            zl.move(
                                self.structures(NEXUS)
                                .closest_to(self.game_info.map_center)
                                .position.towards(self.game_info.map_center, random.randrange(8, 10))
                            )
                        )

            # Some Cheese detected (e.g. YoBot & NaugthyBot). Pull some Probes!
            # if self.enemy_structures.closer_than2(100, self.structures(NEXUS).first) and len(self.prg2) == 0:
            #     self.prg2 = self.units(PROBE).random_group_of(4)
            #     for pr2 in self.prg2:
            #         # if len(self.enemy_units.of_type({PYLON, UnitTypeId.SCV})) > 0:
            #         #     self.do(pr2.attack(self.enemy_units.of_type(
            #         #         {PYLON, UnitTypeId.SCV}).closest_to(pr2.position)))
            #         #     print('Attacking Drone')
            #         # else:
            #         self.do(pr2.attack(
            #                 self.enemy_structures.closest_to(self.structures(NEXUS).first).position.random_on_distance(
            #                     random.randrange(1, 3))))
            #         print('Attacking Base')
            # elif len(self.prg2) > 0 and len(self.enemy_structures.closer_than2(120, self.structures(NEXUS).first)) == 0:
            #     for pr2 in self.prg2:
            #         self.do(pr2.gather(self.state.vespene_geyser.closest_to(self.structures(NEXUS).first)))
            #     self.prg2 = []



    async def remember_enemy_units(self):

        if self.first_pylon_built and self.structures(PYLON).exists and self.scout == []:
            self.scout = [self.units(PROBE).furthest_to(self.structures(NEXUS).first)]
            for scout in self.scout:
                self.do(scout.move(self.enemy_natural.random_on_distance(random.randrange(1, 5))))
            # print(self.scout)
            # print(self.enemy_start_locations)
        elif (
            len(self.scout) == 1
            and len(self.enemy_start_locations) == 1
            and not (self.first_attack or self.proxy_built)
        ):
            if self.time > self.do_something_scout:
                wait = 500
                self.do_something_scout = self.time + wait
                for scout in self.scout:
                    # print('Sending Scout')
                    move_to1 = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(1, 3))
                    move_to2 = self.enemy_natural.random_on_distance(random.randrange(1, 5))
                    move_to3 = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(1, 3))
                    move_to4 = self.enemy_natural.random_on_distance(random.randrange(5, 10))
                    move_to5 = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(1, 3))
                    move_to6 = self.enemy_natural.towards(self.game_info.map_center, random.randrange(1, 10))
                    move_to7 = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(1, 3))
                    move_to8 = self.enemy_natural.random_on_distance(random.randrange(1, 15))
                    move_to9 = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(1, 5))
                    move_to10 = self.enemy_natural.random_on_distance(random.randrange(10, 20))
                    self.do(scout.move(move_to1))
                    self.do(scout.move(move_to2, queue=True))
                    self.do(scout.move(move_to3, queue=True))
                    self.do(scout.move(move_to4, queue=True))
                    self.do(scout.move(move_to5, queue=True))
                    self.do(scout.move(move_to6, queue=True))
                    self.do(scout.move(move_to7, queue=True))
                    self.do(scout.move(move_to8, queue=True))
                    self.do(scout.move(move_to9, queue=True))
                    self.do(scout.move(move_to10, queue=True))

        elif (
            len(self.scout) == 1 and len(self.enemy_start_locations) > 1 and not (self.first_attack or self.proxy_built)
        ):
            if self.time > self.do_something_scout:
                "TODO: Far from perfect. Needs more work!"
                self.k = self.k - 1
                pos = [0, 2, 1]
                wait = 50
                self.do_something_scout = self.time + wait
                if self.k >= 0:
                    move_to = self.enemy_start_locations[pos[self.k]]
                    for scout in self.scout:
                        self.do(scout.move(move_to))
                # else:
                #     move_to = random.sample(list(self.enemy_start_locations), k=1)[0]
                #     print('2')

        # Look through all currently seen units and add them to list of remembered units (override existing)
        for unit in self.enemy_units:
            unit.is_known_this_step = True
            self.remembered_enemy_units_by_tag[unit.tag] = unit

        # Convert to an sc2 Units object and place it in self.remembered_enemy_units
        self.remembered_enemy_units = sc2.units.Units([], self._game_data)
        for tag, unit in list(self.remembered_enemy_units_by_tag.items()):
            # Make unit.is_seen = unit.is_visible
            if unit.is_known_this_step:
                unit.is_seen = unit.is_visible  # There are known structures that are not visible
                unit.is_known_this_step = False  # Set to false for next step
            else:
                unit.is_seen = False

            # # Units that are not visible while we have friendly units nearby likely don't exist anymore, so delete them
            # if not unit.is_seen and self.units.closer_than2(7, unit).exists:
            #     del self.remembered_enemy_units_by_tag[tag]
            #     continue

            self.remembered_enemy_units.append(unit)



    async def expand(self):
        if (
            self.structures(NEXUS).exists
            and self.structures(NEXUS).amount < self.MAX_EXE
            and self.can_afford(NEXUS)
            and self.time > self.do_something_after_exe
        ):
            self.do_something_after_exe = self.time + 20
            location = await self.get_next_expansion()

            await self.build(NEXUS, near=location, max_distance=10, random_alternative=False, placement_step=1)
            # await self.expand_now()

    async def scout_obs(self):
        if len(self.units(OBSERVER)) == 1:
            obs = self.units(OBSERVER)[0]
            if (self.first_attack or self.gathered) and self.units(COLOSSUS).ready.exists:
                target = (
                    self.units(COLOSSUS)
                    .ready.closest_to(self.enemy_start_locations[0])
                    .position.towards(self.enemy_start_locations[0], random.randrange(5, 7))
                )
            elif self.structures(NEXUS).exists and self.units(STALKER).exists:
                target = self.units(STALKER).random
            else:
                target = self.game_info.map_center
            self.do(obs.move(target))

        elif len(self.units(OBSERVER)) == 2:
            scout = self.units(OBSERVER)[1]
            if scout.is_idle:
                # move_to = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(1, 20))
                move_to = self.enemy_start_locations[0].random_on_distance(random.randrange(20, 50))
                self.do(scout.move(move_to))

        if len(self.units(OBSERVER)) < 1 and not self.lance_started:
            for rf in self.structures(ROBOTICSFACILITY).ready.idle:
                if self.can_afford(OBSERVER) and self.supply_left > 0:
                    self.do(rf.train(OBSERVER))

        if len(self.units(OBSERVER)) < 2 and self.lance_started:
            for rf in self.structures(ROBOTICSFACILITY).ready.idle:
                if self.can_afford(OBSERVER) and self.supply_left > 0:
                    self.do(rf.train(OBSERVER))

    async def chrono_boost(self):
        if self.structures(NEXUS).ready.exists:
            nexus = self.structures(NEXUS).ready.random
            if not self.structures(GATEWAY).ready.exists and not self.structures(WARPGATE).ready.exists:
                if not nexus.has_buff(CHRONOBOOSTENERGYCOST) and self.supply_used > 14:
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, nexus))
            elif self.charge_started > 0 and self.time - self.charge_started <= 100:
                twi = self.structures(TWILIGHTCOUNCIL).ready.first
                if not twi.has_buff(CHRONOBOOSTENERGYCOST):
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, twi))
            elif not self.structures(CYBERNETICSCORE).ready.exists and self.structures(GATEWAY).ready.exists:
                gate = self.structures(GATEWAY).ready.first
                if not nexus.has_buff(CHRONOBOOSTENERGYCOST) and not self.structures(GATEWAY).ready.idle:
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, gate))
            elif (
                self.structures(WARPGATE).ready.exists
                and not self.structures(ROBOTICSFACILITY).ready.exists
                and not self.structures(STARGATE).ready.exists
                and not self.structures(GATEWAY).ready.exists
            ):
                warpgate = self.structures(WARPGATE).ready.random
                if not warpgate.has_buff(CHRONOBOOSTENERGYCOST):
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, warpgate))
            elif (
                not self.structures(ROBOTICSFACILITY).ready.exists
                and not self.structures(STARGATE).ready.exists
                and self.structures(CYBERNETICSCORE).ready.exists
                and self.early_game_finished
            ):
                ccore = self.structures(CYBERNETICSCORE).ready.first
                if not ccore.has_buff(CHRONOBOOSTENERGYCOST):
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, ccore))
            elif self.structures(ROBOTICSFACILITY).ready.exists:
                robo = self.structures(ROBOTICSFACILITY).ready.first
                if not robo.has_buff(CHRONOBOOSTENERGYCOST) and not self.structures(ROBOTICSFACILITY).ready.idle:
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, robo))
            elif self.structures(STARGATE).ready.exists:
                star = self.structures(STARGATE).ready.first
                if not star.has_buff(CHRONOBOOSTENERGYCOST) and not self.structures(STARGATE).ready.idle:
                    abilities = await self.get_available_abilities(nexus)
                    if EFFECT_CHRONOBOOSTENERGYCOST in abilities:
                        self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, star))

    async def morph_warpgates(self):
        for gateway in self.structures(GATEWAY).ready:
            abilities = await self.get_available_abilities(gateway)
            if MORPH_WARPGATE in abilities and self.can_afford(MORPH_WARPGATE):
                self.do(gateway(MORPH_WARPGATE))

        if len(self.enemy_units.of_type(UnitTypeId.REAPER)) >= 2:
            if self.structures(CYBERNETICSCORE).ready.exists and self.early_game_finished:
                if self.structures(NEXUS).exists:
                    nexus = self.structures(NEXUS).random
                else:
                    nexus = self.structures.structure.random
                if self.structures(SHIELDBATTERY).closer_than2(6, nexus).amount < 1:
                    if self.structures(PYLON).ready.closer_than2(5, nexus).amount < 1:
                        if self.can_afford(PYLON) and not self.already_pending(PYLON):
                            await self.build(PYLON, near=nexus)
                    else:
                        if self.can_afford(SHIELDBATTERY) and not self.already_pending(SHIELDBATTERY):
                            await self.build(
                                SHIELDBATTERY,
                                near=nexus.position.towards(self.game_info.map_center, random.randrange(-5, -1)),
                            )
        elif len(self.enemy_units.of_type(UnitTypeId.BANSHEE)) >= 1:
            if self.structures(CYBERNETICSCORE).ready.exists and self.early_game_finished:
                if self.structures(NEXUS).exists:
                    nexus = self.structures(NEXUS).random
                else:
                    nexus = self.structures.structure.random
                if self.structures(SHIELDBATTERY).closer_than2(7, nexus).amount < 2 and len(self.structures(SHIELDBATTERY)) < 3:
                    if self.structures(PYLON).ready.closer_than2(5, nexus).amount < 1:
                        if self.can_afford(PYLON) and not self.already_pending(PYLON):
                            await self.build(PYLON, near=nexus)
                    else:
                        if self.can_afford(SHIELDBATTERY) and not self.already_pending(SHIELDBATTERY):
                            await self.build(
                                SHIELDBATTERY,
                                near=nexus.position.towards(self.game_info.map_center, random.randrange(-5, -1)),
                            )

    async def micro_units(self):
        # Some Cheese detected (e.g. YoBot & NaugthyBot). Pull some Probes!
        # if self.time < 240 and self.enemy_structures.closer_than2(120, self.structures(NEXUS).first) and len(self.prg2) > 0:
        #     for pr2 in self.prg2:
        #         self.do(pr2.attack(
        #             self.enemy_structures.closest_to(self.structures(NEXUS).first).position.random_on_distance(
        #                 random.randrange(1, 3))))
        # elif len(self.prg2) > 0 and not self.enemy_structures.closer_than2(120, self.structures(NEXUS).first):
        #     for pr2 in self.prg2:
        #         self.do(pr2.gather(self.state.vespene_geyser.closest_to(self.structures(NEXUS).first)))
        #     self.prg2 = []

        # Stalker-Micro without Blink
        for st in self.units(STALKER):
            # Unit is damaged severely, retreat if possible!
            if st.shield_percentage < 0.1:
                threats = self.enemy_units.not_structure.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(st.ground_range + st.radius, st.position)
                if threats.exists and st.position != threats.closest_to(st).position:
                    distance = await self._client.query_pathing(
                        st.position, st.position.towards(threats.closest_to(st).position, -2)
                    )
                    if distance is None:
                        # Path is blocked, fight for your life!
                        self.do(st.attack(threats.closest_to(st.position)))

                    else:
                        self.do(st.move(st.position.towards(threats.closest_to(st).position, -2)))

            # Unit is under fire! If possible, kite enemy to minimize damage
            elif st.is_attacking and st.shield_percentage < 1:
                threats = self.enemy_units.not_structure.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(st.ground_range + st.radius, st.position)
                if threats.exists:
                    if (
                        st.ground_range + st.radius
                        > threats.closest_to(st).ground_range + threats.closest_to(st).radius
                    ):
                        if st.ground_range + st.radius > st.distance_to(threats.closest_to(st)):
                            if st.weapon_cooldown > 0 and st.position != threats.closest_to(st).position:
                                distance = await self._client.query_pathing(
                                    st.position, st.position.towards(threats.closest_to(st).position, -1)
                                )
                                if distance is None:
                                    # Path is blocked, fight for your life!
                                    self.do(st.attack(threats.closest_to(st.position)))

                                else:
                                    self.do(
                                        st.move(st.position.towards(threats.closest_to(st).position, -1))
                                    )
            # Snipe targets which are a oneshot
            else:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(st.ground_range + st.radius, st.position)
                for threat in threats:
                    if threat.health <= 13:
                        # print('Attacking preferred Enemy', threat, 'with health:', threat.health)
                        self.do(st.attack(threat))

        # Adept-Micro
        for ad in self.units(ADEPT):
            # Unit is damaged severely, retreat if possible!
            if ad.shield_percentage < 0.1:
                threats = self.enemy_units.not_structure.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(ad.ground_range + ad.radius, ad.position)
                if threats.exists and ad.position != threats.closest_to(ad).position:
                    distance = await self._client.query_pathing(
                        ad.position, ad.position.towards(threats.closest_to(ad).position, -1)
                    )
                    if distance is None:
                        # Path is blocked, fight for your life!
                        self.do(ad.attack(threats.closest_to(ad.position)))
                        # print('- Adept is Blocked! Fighting! -')
                    else:
                        self.do(ad.move(ad.position.towards(threats.closest_to(ad).position, -1)))
                        # print('- Microing Adept! -')
            # Unit is under fire! If possible, kite enemy to minimize damage
            elif ad.is_attacking and ad.shield_percentage < 1:
                threats = self.enemy_units.not_structure.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(ad.ground_range + ad.radius, ad.position)
                if threats.exists:
                    if (
                        ad.ground_range + ad.radius
                        > threats.closest_to(ad).ground_range + threats.closest_to(ad).radius
                    ):
                        if ad.ground_range + ad.radius > ad.distance_to(threats.closest_to(ad)):
                            if ad.weapon_cooldown > 0 and ad.position != threats.closest_to(ad).position:
                                distance = await self._client.query_pathing(
                                    ad.position, ad.position.towards(threats.closest_to(ad).position, -1)
                                )
                                if distance is None:
                                    # Path is blocked, fight for your life!
                                    self.do(ad.attack(threats.closest_to(ad.position)))
                                    # print('- Adept is Blocked! Fighting! -')
                                else:
                                    # print('- Kiting Enemy -')
                                    self.do(
                                        ad.move(ad.position.towards(threats.closest_to(ad).position, -1))
                                    )
            # Snipe targets which are a oneshot
            else:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(ad.ground_range + ad.radius, ad.position)
                for threat in threats:
                    if threat.health <= 10:
                        # print('Attacking preferred Enemy', threat, 'with health:', threat.health)
                        self.do(ad.attack(threat))

            # Prioritize targets with a specific armor type
            # elif self.first_attack:
            #     threats = self.enemy_units.closer_than2(st.ground_range + st.radius, st.position)
            #     for threat in threats:
            #         if threat.is_armored:
            #             print('- Attacking preferred Enemy -', threat)
            #             self.do(st.attack(threat))

        # Immortal-Micro
        for im in self.units(IMMORTAL):
            # Unit is damaged severely, retreat if possible!
            if im.shield_percentage < 0.1:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(im.ground_range + im.radius, im.position)
                if threats.exists and im.position != threats.closest_to(im).position:
                    distance = await self._client.query_pathing(
                        im.position, im.position.towards(threats.closest_to(im).position, -2)
                    )
                    if distance is None:
                        # Path is blocked, fight for your life!
                        self.do(im.attack(threats.closest_to(im.position)))
                        # print('- Immortal is Blocked! Fighting! -')
                    else:
                        self.do(im.move(im.position.towards(threats.closest_to(im).position, -2)))
                        # print('- Microing Immortal! -')
            # Unit is under fire! If possible, kite enemy to minimize damage
            elif im.is_attacking and im.shield_percentage < 1:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(im.ground_range + im.radius, im.position)
                if threats.exists:
                    if (
                        im.ground_range + im.radius
                        > threats.closest_to(im).ground_range + threats.closest_to(im).radius
                    ):
                        if im.ground_range + im.radius > im.distance_to(threats.closest_to(im)):
                            if im.weapon_cooldown > 0 and im.position != threats.closest_to(im).position:
                                distance = await self._client.query_pathing(
                                    im.position, im.position.towards(threats.closest_to(im).position, -2)
                                )
                                if distance is None:
                                    # Path is blocked, fight for your life!
                                    self.do(im.attack(threats.closest_to(im.position)))
                                    # print('- Immortal is Blocked! Fighting! -')
                                else:
                                    # print('- Kiting Enemy -')
                                    self.do(
                                        im.move(im.position.towards(threats.closest_to(im).position, -2))
                                    )
            # Prioritize targets with a specific armor type
            elif self.first_attack:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(im.ground_range + im.radius, im.position)
                for threat in threats:
                    if threat.is_armored:
                        self.do(im.attack(threat))

        # Colossus-Micro
        for cl in self.units(COLOSSUS):
            # Unit is damaged severely, retreat if possible!
            if cl.shield_percentage < 0.1:
                threats = self.enemy_units.not_structure.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(cl.ground_range + cl.radius, cl.position)
                if threats.exists and cl.position != threats.closest_to(cl).position:
                    distance = await self._client.query_pathing(
                        cl.position, cl.position.towards(threats.closest_to(cl).position, -2)
                    )
                    if distance is None:
                        # Path is blocked, fight for your life!
                        self.do(cl.attack(threats.closest_to(cl.position)))
                        # print('- Colossus is Blocked! Fighting! -')
                    else:
                        self.do(cl.move(cl.position.towards(threats.closest_to(cl).position, -2)))
                        # print('- Microing Colossus! -')
            # Unit is under fire! If possible, kite enemy to minimize damage
            elif cl.is_attacking and cl.shield_percentage <= 1:
                threats = self.enemy_units.not_structure.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(cl.ground_range + cl.radius, cl.position)
                if threats.exists:
                    if (
                        cl.ground_range + cl.radius
                        > threats.closest_to(cl).ground_range + threats.closest_to(cl).radius
                    ):
                        if cl.ground_range + cl.radius > cl.distance_to(threats.closest_to(cl)):
                            if cl.weapon_cooldown > 0 and cl.position != threats.closest_to(cl).position:
                                distance = await self._client.query_pathing(
                                    cl.position, cl.position.towards(threats.closest_to(cl).position, -2)
                                )
                                if distance is None:
                                    # Path is blocked, fight for your life!
                                    self.do(cl.attack(threats.closest_to(cl.position)))
                                    # print('- Colossus is Blocked! Fighting! -')
                                else:
                                    # print('- Kiting Enemy -')
                                    self.do(
                                        cl.move(cl.position.towards(threats.closest_to(cl).position, -2))
                                    )

        # Sentry-Micro
        for se in self.units(SENTRY):
            # Unit is damaged severely, retreat if possible!
            threats = self.enemy_units.not_structure.filter(
                lambda unit: unit.type_id not in self.units_to_ignore
            ).closer_than2(10, se.position)
            if se.shield_percentage < 0.1:
                if threats.exists and se.position != threats.closest_to(se).position:
                    distance = await self._client.query_pathing(
                        se.position, se.position.towards(threats.closest_to(se).position, -1)
                    )
                    if distance is None:
                        # Path is blocked, fight for your life!
                        self.do(se.attack(threats.closest_to(se.position)))
                        # print('- Colossus is Blocked! Fighting! -')
                    else:
                        self.do(se.move(se.position.towards(threats.closest_to(se).position, -1)))
                        # print('- Microing Colossus! -')
            if threats.amount > 4 and not se.has_buff(GUARDIANSHIELD):
                if await self.can_cast(se, GUARDIANSHIELD_GUARDIANSHIELD):
                    self.do(se(GUARDIANSHIELD_GUARDIANSHIELD))
                    break

        # Voidray-Micro
        for vr in self.units(VOIDRAY):
            # Unit is damaged severely, retreat if possible!
            if vr.shield_percentage < 0.1:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(vr.air_range + vr.radius, vr.position)
                if threats.exists and vr.position != threats.closest_to(vr).position:
                    distance = await self._client.query_pathing(
                        vr.position, vr.position.towards(threats.closest_to(vr).position, -2)
                    )
                    if distance is None:
                        # Path is blocked, fight for your life!
                        self.do(vr.attack(threats.closest_to(vr.position)))
                        # print('- Immortal is Blocked! Fighting! -')
                    else:
                        self.do(vr.move(vr.position.towards(threats.closest_to(vr).position, -2)))
                        # print('- Microing Voidray! -')
            # Unit is under fire! If possible, kite enemy to minimize damage
            # elif vr.is_attacking and vr.shield_percentage < 0.5:
            #     threats = self.enemy_units.filter(lambda unit: unit.type_id not in self.units_to_ignore).closer_than2(vr.air_range + vr.radius, vr.position)
            #     if threats.exists:
            #         if vr.air_range + vr.radius > threats.closest_to(vr).air_range + threats.closest_to(
            #                 vr).radius:
            #             if vr.air_range + vr.radius > vr.distance_to(threats.closest_to(vr)):
            #                 if vr.weapon_cooldown > 0 and vr.position != threats.closest_to(vr).position:
            #                     distance = await self._client.query_pathing(vr.position, vr.position.towards(
            #                         threats.closest_to(vr).position, -2))
            #                     if distance is None:
            #                         # Path is blocked, fight for your life!
            #                         self.do(vr.attack(threats.closest_to(vr.position)))
            #                         # print('- Voidray is Blocked! Fighting! -')
            #                     else:
            #                         # print('- Kiting Enemy -')
            #                         self.do(
            #                             vr.move(vr.position.towards(threats.closest_to(vr).position, -2)))
            # Prioritize targets with a specific armor type
            elif not vr.is_attacking:
                threats = self.enemy_units.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                ).closer_than2(vr.air_range + vr.radius + 2, vr.position)
                # print(threats)
                if threats.exists:
                    for threat in threats:
                        if threat.is_armored and threat.can_attack_air:
                            if await self.can_cast(vr, EFFECT_VOIDRAYPRISMATICALIGNMENT):
                                self.do(vr(EFFECT_VOIDRAYPRISMATICALIGNMENT))
                            self.do(vr.attack(threat))
                            # print('Attacking Armored & Airdamage: ', threat)
                                # print('Full Damage!')
                        elif threat.can_attack_air:
                            self.do(vr.attack(threat))
                            # print('Attacking Airdamage: ', threat)
                            # if await self.can_cast(vr, EFFECT_VOIDRAYPRISMATICALIGNMENT):
                                # self.do(vr(EFFECT_VOIDRAYPRISMATICALIGNMENT))
                                # print('Full Damage!')
                        elif threat.is_armored:
                            if await self.can_cast(vr, EFFECT_VOIDRAYPRISMATICALIGNMENT):
                                self.do(vr(EFFECT_VOIDRAYPRISMATICALIGNMENT))
                            self.do(vr.attack(threat))
                            # print('Attacking Armored: ', threat)
                            # if await self.can_cast(vr, EFFECT_VOIDRAYPRISMATICALIGNMENT):
                                # self.do(vr(EFFECT_VOIDRAYPRISMATICALIGNMENT))
                                # print('Full Damage!')
                        else:
                            self.do(vr.attack(threat))
                            # print('Attacking else: ', threat)


        # Survive Base-Trade
        if self.structures(NEXUS).amount == 0:
            if self.can_afford(PYLON) and self.units(STALKER).exists:
                await self.build(PYLON, near=self.units(STALKER).random.position)

    # Specific Functions for Two Base Colossus Build Order

    async def build_proxy_pylon_2base_colossus(self):
        if self.lance_started and not self.proxy_built and self.can_afford(PYLON):
            p = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
            await self.build(PYLON, near=p)
            self.proxy_built = True

    async def two_base_colossus_buildings(self):
        if self.structures(PYLON).ready.exists:
            pylon = self.structures(PYLON).ready.random

            if (
                (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < (self.time / 60)
                and (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < self.MAX_GATES
                and self.structures(ROBOTICSFACILITY).ready.exists
            ):
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon, max_distance=10, random_alternative=False, placement_step=5)
                    # print('Gate #', len(self.structures(GATEWAY))+1, 'build @:', self.time)

            if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first))

            if self.structures(CYBERNETICSCORE).ready.exists and len(self.structures(NEXUS)) > 1:
                if len(self.structures(ROBOTICSFACILITY)) < self.MAX_ROBOS:
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(
                            ROBOTICSFACILITY, near=pylon, max_distance=10, random_alternative=False, placement_step=5
                        )

            if self.structures(ROBOTICSFACILITY).ready.exists:
                if not self.structures(ROBOTICSBAY):
                    if self.can_afford(ROBOTICSBAY) and not self.already_pending(ROBOTICSBAY):
                        await self.build(
                            ROBOTICSBAY,
                            near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first),
                            max_distance=10,
                            random_alternative=False,
                            placement_step=5,
                        )

    async def two_base_colossus_upgrade(self):
        if (
            self.structures(ROBOTICSBAY).ready.exists
            and self.can_afford(RESEARCH_EXTENDEDTHERMALLANCE)
            and not self.lance_started
            and self.units(COLOSSUS).ready
        ):
            bay = self.structures(ROBOTICSBAY).ready.first
            self.do(bay(RESEARCH_EXTENDEDTHERMALLANCE))
            self.lance_started = True

    async def two_base_colossus_offensive_force(self):
        for rf in self.structures(ROBOTICSFACILITY).ready.idle:
            if self.structures(ROBOTICSBAY).ready.exists and self.can_afford(COLOSSUS) and self.supply_left > 5:
                self.do(rf.train(COLOSSUS))

        for gw in self.structures(GATEWAY).ready.idle:
            if self.structures(GATEWAY).ready.exists and self.minerals > 600 and self.supply_left > 1:
                self.do(gw.train(ZEALOT))
            if (
                self.structures(ROBOTICSFACILITY).ready.exists
                and not self.already_pending(ROBOTICSBAY)
                and not self.structures(ROBOTICSBAY).ready.exists
            ):
                break
            elif self.structures(ROBOTICSBAY).ready.exists and self.structures(ROBOTICSFACILITY).ready.idle:
                break
            elif self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 1:
                self.do(gw.train(STALKER))
            elif self.structures(GATEWAY).ready.exists and self.minerals > 225 and self.supply_left > 1:
                self.do(gw.train(ZEALOT))

        for wg in self.structures(WARPGATE).ready:
            abilities = await self.get_available_abilities(wg)
            if WARPGATETRAIN_ZEALOT in abilities:
                pylon = self.structures(PYLON).ready.closest_to(self.game_info.map_center)
                pos = pylon.position.to2.random_on_distance(random.randrange(1, 6))
                warp_place = await self.find_placement(WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                if self.structures(WARPGATE).ready.exists and self.minerals > 600 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))
                if (
                    self.structures(ROBOTICSFACILITY).ready.exists
                    and not self.already_pending(ROBOTICSBAY)
                    and not self.structures(ROBOTICSBAY).ready.exists
                ):
                    break
                elif self.structures(ROBOTICSBAY).ready.exists and self.structures(ROBOTICSFACILITY).ready.idle:
                    break
                elif (
                    self.structures(CYBERNETICSCORE).ready.exists
                    and self.can_afford(SENTRY)
                    and self.units(STALKER).amount / (self.units(SENTRY).amount + 1) > 6
                    and self.supply_left > 1
                ):
                    self.do(wg.warp_in(SENTRY, warp_place))
                elif self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 1:
                    self.do(wg.warp_in(STALKER, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.minerals > 425 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.vespene > 400 and self.supply_left > 1:
                    self.do(wg.warp_in(SENTRY, warp_place))

    async def two_base_colossus_unit_control(self):

        # defend as long as there are not 2 colossi, then attack
        if len(self.units(COLOSSUS).ready) <= 1 and not self.first_attack:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore
                    ).closer_than2(self.threat_proximity, structure.position)
                    if threats:
                        break
                if threats:
                    break
            if threats and not self.defend:
                self.defend = True
                self.back_home = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for cl in self.units(COLOSSUS):
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif threats and self.defend:
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for cl in self.units(COLOSSUS).idle:
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY).idle:
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))
            elif not threats and self.back_home:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(5, 10))
                )
                for cl in self.units(COLOSSUS):
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))

        # attack_enemy_start
        elif len(self.units(COLOSSUS).ready) > 1 or (self.first_attack and not self.first_attack_finished):

            if self.time > self.do_something_after:
                all_enemy_base = self.enemy_structures.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                )
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                elif all_enemy_base.exists:
                    next_enemy_base = all_enemy_base.closest_to(self.game_info.map_center)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                else:
                    attack_target = self.game_info.map_center.random_on_distance(
                        random.randrange(12, 70 + int(self.time / 60))
                    )
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)

                if self.gathered and not self.first_attack:
                    for cl in self.units(COLOSSUS):
                        self.do(cl.attack(attack_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(attack_target))
                    for st in self.units(STALKER):
                        self.do(st.attack(attack_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(attack_target))
                    self.first_attack = True
                    print(
                        "--- First Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Zealots: ",
                        len(self.units(ZEALOT)),
                    )
                if gather_target and not self.first_attack:
                    for cl in self.units(COLOSSUS):
                        self.do(cl.attack(gather_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(gather_target))
                    for st in self.units(STALKER):
                        self.do(st.attack(gather_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(gather_target))
                    wait = 35
                    self.do_something_after = self.time + wait
                    self.gathered = True
                if self.first_attack:
                    for cl in self.units(COLOSSUS).idle:
                        self.do(cl.attack(attack_target))
                    for se in self.units(SENTRY).idle:
                        self.do(se.attack(attack_target))
                    for st in self.units(STALKER).idle:
                        self.do(st.attack(attack_target))
                    for zl in self.units(ZEALOT).idle:
                        self.do(zl.attack(attack_target))

        # seek & destroy
        if (
            self.first_attack
            and not self.enemy_structures.exists
            and self.time > self.do_something_after
            and self.time / 60 > 10
        ):

            for cl in self.units(COLOSSUS).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(cl.attack(attack_target))
            for se in self.units(SENTRY).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(se.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            self.do_something_after = self.time + 5

        if self.first_attack and len(self.units(COLOSSUS).ready) < 2:

            lategame_choice = 1 #random.randrange(0, 2)
            if lategame_choice == 0:
                self.first_attack_finished = True
                self.first_attack = False
                print("Lategame started @:", self.time)
            else:
                self.first_attack_finished = False
                self.first_attack = False
                print("Fully committing")

        # execute actions
        #

    async def two_base_colossus_unit_control_lategame(self):

        # defend as long as there is no +2 Armor-Upgrade or supply < 200
        if self.armor_upgrade < 2 and self.supply_used < 190:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore
                    ).closer_than2(self.threat_proximity, structure.position)
                    if threats:
                        break
                if threats:
                    break
            if threats and not self.defend:
                self.defend = True
                self.back_home = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for cl in self.units(COLOSSUS):
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif threats and self.defend:
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for cl in self.units(COLOSSUS).idle:
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY).idle:
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))
            elif not threats and self.back_home:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(5, 10))
                )
                for cl in self.units(COLOSSUS):
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))

        # attack_enemy_start
        elif self.armor_upgrade >= 2 or self.supply_used > 190:

            all_enemy_base = self.enemy_structures.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                )
            if all_enemy_base.exists and self.structures(NEXUS).exists:
                next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
            elif all_enemy_base.exists:
                next_enemy_base = all_enemy_base.closest_to(self.game_info.map_center)
                attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
            else:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )

            if not self.second_attack:
                for cl in self.units(COLOSSUS):
                    self.do(cl.attack(attack_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(attack_target))
                for st in self.units(STALKER):
                    self.do(st.attack(attack_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(attack_target))
                self.second_attack = True
                print(
                    "--- Second Attack started --- @: ",
                    self.time,
                    "with Stalkers: ",
                    len(self.units(STALKER)),
                    "and Zealots: ",
                    len(self.units(ZEALOT)),
                )
            if self.second_attack:

                for cl in self.units(COLOSSUS).idle:
                    self.do(cl.attack(attack_target))
                for se in self.units(SENTRY).idle:
                    self.do(se.attack(attack_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(attack_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(attack_target))

        # seek & destroy
        if self.second_attack and self.time / 60 > 20:

            for cl in self.units(COLOSSUS).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(cl.attack(attack_target))
            for se in self.units(SENTRY).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(se.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            self.do_something_after = self.time + 5

        # execute actions


    async def two_base_colossus_upgrade_lategame(self):
        if self.structures(NEXUS).exists:
            nexus = self.structures(NEXUS).random
        else:
            nexus = self.structures.structure.random
        # Build two Forges for double upgrades
        if self.structures(FORGE).amount < 2 and not self.already_pending(FORGE):
            if self.can_afford(FORGE):
                await self.build(FORGE, near=self.structures(PYLON).ready.random)

        # Always build a cannon in mineral line for defense
        if self.structures(FORGE).ready.exists:
            if self.structures(PHOTONCANNON).closer_than2(10, nexus).amount < 1:
                if self.structures(PYLON).ready.closer_than2(5, nexus).amount < 1:
                    if self.can_afford(PYLON) and not self.already_pending(PYLON):
                        await self.build(PYLON, near=nexus)
                else:
                    if self.can_afford(PHOTONCANNON) and not self.already_pending(PHOTONCANNON):
                        await self.build(
                            PHOTONCANNON,
                            near=nexus.position.towards(self.game_info.map_center, random.randrange(-10, -1)),
                        )

            forge = self.structures(FORGE).ready.random

            # Only if we're not upgrading anything yet
            if forge.idle and self.can_afford(
                FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1
            ):  # Das can_afford triggert nicht richtig
                # abilities = await self.get_available_abilities(forge)
                # print('Abilities:', abilities)
                if (
                    self.can_afford(FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1) and self.weapon_upgrade == 0
                ):  # and FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1 in abilities:
                    self.do(forge(RESEARCH_PROTOSSGROUNDWEAPONS))
                    self.weapon_upgrade += 1
                elif (
                    self.can_afford(FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1) and self.armor_upgrade == 0
                ):  # and FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1 in abilities:
                    self.do(forge(RESEARCH_PROTOSSGROUNDARMOR))
                    self.armor_upgrade += 1
                elif (
                    self.can_afford(FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2) and self.weapon_upgrade == 1
                ):  # and FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2 in abilities:
                    self.do(forge(RESEARCH_PROTOSSGROUNDWEAPONS))
                    self.weapon_upgrade += 1
                elif (
                    self.can_afford(FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2) and self.armor_upgrade == 1
                ):  # and FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2 in abilities:
                    self.do(forge(RESEARCH_PROTOSSGROUNDARMOR))
                    self.armor_upgrade += 1
                elif (
                    self.can_afford(FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3) and self.weapon_upgrade == 2
                ):  # and FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3 in abilities:
                    self.do(forge(RESEARCH_PROTOSSGROUNDWEAPONS))
                    self.weapon_upgrade += 1
                elif (
                    self.can_afford(FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3) and self.armor_upgrade == 2
                ):  # and FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3 in abilities:
                    self.do(forge(RESEARCH_PROTOSSGROUNDARMOR))
                    self.armor_upgrade += 1
                if (self.armor_upgrade == 3 or self.weapon_upgrade == 3) and self.can_afford(
                    FORGERESEARCH_PROTOSSSHIELDSLEVEL1
                ):  # and FORGERESEARCH_PROTOSSSHIELDSLEVEL1 in abilities:
                    self.do(forge(RESEARCH_PROTOSSSHIELDS))

        # Build a Twilight Council
        if not self.structures(TWILIGHTCOUNCIL).exists and not self.already_pending(TWILIGHTCOUNCIL):
            if self.can_afford(TWILIGHTCOUNCIL) and self.structures(CYBERNETICSCORE).ready.exists:
                await self.build(TWILIGHTCOUNCIL, near=self.structures(PYLON).ready.random)

        if self.structures(TWILIGHTCOUNCIL).ready.exists and self.can_afford(RESEARCH_CHARGE) and not self.charge_started:
            twi = self.structures(TWILIGHTCOUNCIL).ready.first
            self.do(twi(RESEARCH_CHARGE))
            self.charge_started = True

        if self.structures(PYLON).ready.exists:
            pylon = self.structures(PYLON).ready.random

            if (
                (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < (self.time / 60)
                and (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < self.MAX_GATES
                and self.structures(ROBOTICSFACILITY).ready.exists
            ):
                if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                    await self.build(GATEWAY, near=pylon)

        if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
            if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first))

    # Specific Functions for Two Base Immortal Adept Push

    async def immortal_adept_buildings(self):
        if self.structures(PYLON).ready.exists:
            pylon = self.structures(PYLON).ready.random

            if (
                len(self.units(IMMORTAL).ready) >= 1
                and not self.structures(ROBOTICSFACILITY).ready.idle
                and self.MAX_GATES <= 6
            ):
                self.MAX_GATES = 7

            if (self.already_pending(ROBOTICSFACILITY) or self.structures(ROBOTICSFACILITY).ready) and (
                len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))
            ) < self.MAX_GATES:
                if self.can_afford(GATEWAY):
                    await self.build(GATEWAY, near=pylon, max_distance=10, random_alternative=False, placement_step=5)

            if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first))

            if self.structures(CYBERNETICSCORE).ready.exists and len(self.structures(NEXUS)) > 1:
                if len(self.structures(ROBOTICSFACILITY)) < self.MAX_ROBOS:
                    if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                        await self.build(
                            ROBOTICSFACILITY, near=pylon, max_distance=10, random_alternative=False, placement_step=5
                        )

    async def build_proxy_pylon(self):
        if len(self.units(IMMORTAL).ready) >= 1 and not self.proxy_built and self.can_afford(PYLON):
            p = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
            await self.build(PYLON, near=p)
            self.proxy_built = True

    async def immortal_adept_offensive_force(self):
        for rf in self.structures(ROBOTICSFACILITY).ready.idle:
            if (
                len(self.units(IMMORTAL).ready) >= 2
                and not self.units(OBSERVER).ready
                and self.can_afford(OBSERVER)
                and self.supply_left > 1
            ):
                self.do(rf.train(OBSERVER))
            elif self.can_afford(IMMORTAL) and self.supply_left > 1:
                self.do(rf.train(IMMORTAL))

        for gw in self.structures(GATEWAY).ready.idle:
            if self.structures(GATEWAY).ready.exists and self.minerals > 600 and self.supply_left > 1:
                self.do(gw.train(ZEALOT))
            if self.structures(ROBOTICSBAY).ready.exists and self.structures(ROBOTICSFACILITY).ready.idle:
                break
            elif self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 1:
                self.do(gw.train(STALKER))
            elif self.structures(GATEWAY).ready.exists and self.minerals > 325 and self.supply_left > 1:
                self.do(gw.train(ZEALOT))

        for wg in self.structures(WARPGATE).ready:
            abilities = await self.get_available_abilities(wg)
            if WARPGATETRAIN_ZEALOT in abilities:
                pylon = self.structures(PYLON).ready.closest_to(self.game_info.map_center)
                pos = pylon.position.to2.random_on_distance(random.randrange(1, 6))
                warp_place = await self.find_placement(WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                if self.structures(WARPGATE).ready.exists and self.minerals > 600 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.vespene > 400 and self.supply_left > 1:
                    self.do(wg.warp_in(SENTRY, warp_place))
                if self.structures(ROBOTICSFACILITY).ready.exists and self.structures(ROBOTICSFACILITY).ready.idle:
                    break
                elif (
                    self.structures(CYBERNETICSCORE).ready.exists
                    and self.can_afford(SENTRY)
                    and (self.units(STALKER).amount + self.units(ZEALOT).amount) / (self.units(SENTRY).amount + 1) > 6
                    and self.supply_left > 1
                ):
                    self.do(wg.warp_in(SENTRY, warp_place))
                elif self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 1:
                    if self.remembered_enemy_units.of_type({UnitTypeId.CARRIER}):
                        self.do(wg.warp_in(STALKER, warp_place))
                    else:
                        build_what = random.randrange(0, 5)
                        # print('Build What:', build_what)
                        if build_what < 3:
                            self.do(wg.warp_in(ZEALOT, warp_place))
                        else:
                            self.do(wg.warp_in(STALKER, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.minerals > 325 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))

    async def immortal_adept_unit_control(self):

        # defend as long as there are not 2 immortals, then attack
        if len(self.units(IMMORTAL).ready) <= 1 and not self.first_attack:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore
                    ).closer_than2(self.threat_proximity, structure.position)
                    if threats:
                        break
                if threats:
                    break
            if threats and not self.defend:
                self.defend = True
                self.back_home = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for cl in self.units(IMMORTAL):
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif threats and self.defend:
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for cl in self.units(IMMORTAL).idle:
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY).idle:
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT).idle:
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))
            elif not threats and self.back_home:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(5, 10))
                )
                for cl in self.units(IMMORTAL):
                    self.do(cl.attack(defence_target))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))

        # attack_enemy_start
        elif len(self.units(IMMORTAL).ready) > 1:

            if self.time > self.do_something_after:
                all_enemy_base = self.enemy_structures.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                )
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                elif all_enemy_base.exists:
                    next_enemy_base = all_enemy_base.closest_to(self.game_info.map_center)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                else:
                    attack_target = self.game_info.map_center.random_on_distance(
                        random.randrange(12, 70 + int(self.time / 60))
                    )
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)

                if self.gathered and not self.first_attack:
                    for cl in self.units(IMMORTAL):
                        self.do(cl.attack(attack_target))
                    for st in self.units(STALKER):
                        self.do(st.attack(attack_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(attack_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(attack_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(attack_target))
                    for ob in self.units(OBSERVER):
                        self.do(ob.move(attack_target))
                    self.first_attack = True
                    print(
                        "--- First Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Adepts: ",
                        len(self.units(ADEPT)),
                        "and Zealots: ",
                        len(self.units(ZEALOT)),
                    )
                if gather_target and not self.first_attack:
                    for cl in self.units(IMMORTAL):
                        self.do(cl.attack(gather_target))
                    for st in self.units(STALKER):
                        self.do(st.attack(gather_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(gather_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(gather_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(gather_target))
                    wait = 38
                    self.do_something_after = self.time + wait
                    self.gathered = True
                if self.first_attack:
                    for cl in self.units(IMMORTAL).idle:
                        self.do(cl.attack(attack_target))
                    for st in self.units(STALKER).idle:
                        self.do(st.attack(attack_target))
                    for se in self.units(SENTRY).idle:
                        self.do(se.attack(attack_target))
                    for zl in self.units(ZEALOT).idle:
                        self.do(zl.attack(attack_target))
                    for ad in self.units(ADEPT).idle:
                        self.do(ad.attack(attack_target))
        if not self.units(IMMORTAL) and self.first_attack:
            self.first_attack = False
            self.gathered = False

            if len(self.units(OBSERVER).ready) >= 1 and self.units(IMMORTAL).ready.exists:
                for ob in self.units(OBSERVER):
                    self.do(
                        ob.move(
                            self.units(IMMORTAL)
                            .ready.closest_to(self.enemy_start_locations[0])
                            .position.towards(self.enemy_start_locations[0], random.randrange(5, 7))
                        )
                    )

        # seek & destroy
        if self.first_attack and not self.enemy_structures.exists and self.time > self.do_something_after:

            for cl in self.units(IMMORTAL).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(cl.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            for ad in self.units(ADEPT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(ad.attack(attack_target))
            self.do_something_after = self.time + 5

        # execute actions


    # Specific Functions for Four Gate Proxy Build

    async def build_proxy_pylon_four_gate(self):
        if (
            (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) >= 3
            and not self.proxy_built
            and self.can_afford(PYLON)
        ):
            # p = self.game_info.map_center.towards(self.enemy_start_locations[0], 27)
            p = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
            await self.build(PYLON, near=p)
            self.proxy_built = True

    async def four_gate_buildings(self):
        if self.structures(PYLON).ready.exists and self.structures(NEXUS).ready.exists:
            pylon = pylon = self.structures(PYLON).ready.random

            if (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < self.MAX_GATES:
                if self.can_afford(GATEWAY):
                    await self.build(GATEWAY, near=pylon, max_distance=10, random_alternative=True, placement_step=5)

        if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
            if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first))

    async def four_gate_offensive_force(self):

        if self.structures(GATEWAY).ready.exists:
            for gw in self.structures(GATEWAY).ready.idle:
                if self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 1:
                    if str(self.enemy_race) == "Race.Zerg":
                        build_what = random.randrange(0, 2)
                        if build_what == 0:
                            self.do(gw.train(STALKER))
                        else:
                            self.do(gw.train(ZEALOT))
                    else:
                        self.do(gw.train(STALKER))

        for wg in self.structures(WARPGATE).ready:
            abilities = await self.get_available_abilities(wg)
            if WARPGATETRAIN_ZEALOT in abilities:
                pylon = self.structures(PYLON).ready.closest_to(self.game_info.map_center)
                pos = pylon.position.to2.random_on_distance(random.randrange(1, 6))
                warp_place = await self.find_placement(WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                if (
                    self.structures(CYBERNETICSCORE).ready.exists
                    and self.can_afford(SENTRY)
                    and (self.units(STALKER).amount + self.units(ADEPT).amount) / (self.units(SENTRY).amount + 1) > 10
                    and self.supply_left > 1
                ):
                    self.do(wg.warp_in(SENTRY, warp_place))
                elif self.structures(CYBERNETICSCORE).ready.exists and self.can_afford(STALKER) and self.supply_left > 1:
                    if str(self.enemy_race) == "Race.Zerg":
                        build_what = random.randrange(1, 3)
                        if build_what == 0:
                            self.do(wg.warp_in(ADEPT, warp_place))
                        elif build_what == 1:
                            self.do(wg.warp_in(STALKER, warp_place))
                        else:
                            self.do(wg.warp_in(ZEALOT, warp_place))
                    else:
                        build_what = random.randrange(0, 3)
                        if build_what == 0:
                            self.do(wg.warp_in(ZEALOT, warp_place))
                        elif build_what == 1:
                            self.do(wg.warp_in(STALKER, warp_place))
                        else:
                            self.do(wg.warp_in(ZEALOT, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.minerals > 325 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.vespene > 200 and self.supply_left > 1:
                    self.do(wg.warp_in(SENTRY, warp_place))

    async def four_gate_unit_control(self):

        # defend nexus if there is no proxy pylon
        if not self.gathered and len(self.units(STALKER)) + len(self.units(ZEALOT)) + len(self.units(ADEPT)) < 10:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore
                    ).closer_than2(self.threat_proximity, structure.position)
                    if threats:
                        break
                if threats:
                    break
            if threats and not self.defend:
                self.defend = True
                self.back_home = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif threats and self.defend:
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for se in self.units(SENTRY).idle:
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT).idle:
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))
            elif not threats and self.back_home:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(5, 10))
                )
                for se in self.units(SENTRY):
                    self.do(se.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))

        # attack_enemy_start
        elif self.proxy_built:

            if self.time > self.do_something_after:
                all_enemy_base = self.enemy_structures.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                )
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = next_enemy_base.position.towards(self.structures(NEXUS).first.position, 40)
                elif all_enemy_base.exists:
                    next_enemy_base = all_enemy_base.closest_to(self.game_info.map_center)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                else:
                    attack_target = self.game_info.map_center.random_on_distance(
                        random.randrange(12, 70 + int(self.time / 60))
                    )
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)
                if (
                    self.gathered
                    and not self.first_attack
                    and len(self.units(STALKER)) + len(self.units(ZEALOT)) + len(self.units(ADEPT)) >= 10
                ):
                    for st in self.units(STALKER):
                        self.do(st.attack(attack_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(attack_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(attack_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(attack_target))
                    self.first_attack = True
                    print(
                        "--- First Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Adepts: ",
                        len(self.units(ADEPT)),
                        "and Zealots: ",
                        len(self.units(ZEALOT)),
                    )
                if (
                    gather_target
                    and not self.first_attack
                    and len(self.units(STALKER)) + len(self.units(ZEALOT)) + len(self.units(ADEPT)) >= 6
                ):
                    for st in self.units(STALKER):
                        self.do(st.attack(gather_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(gather_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(gather_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(gather_target))
                    wait = 32
                    self.do_something_after = self.time + wait
                    self.gathered = True
                if self.first_attack:
                    for st in self.units(STALKER).idle:
                        self.do(st.attack(attack_target))
                    for se in self.units(SENTRY).idle:
                        self.do(se.attack(attack_target))
                    for zl in self.units(ZEALOT).idle:
                        self.do(zl.attack(attack_target))
                    for ad in self.units(ADEPT).idle:
                        self.do(ad.attack(attack_target))

        # seek & destroy
        if self.first_attack and not self.enemy_structures.exists and self.time > self.do_something_after:

            for se in self.units(SENTRY).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(se.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            for ad in self.units(ADEPT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(ad.attack(attack_target))
            self.do_something_after = self.time + 5

        # execute actions


    # Specific Functions for One Base DT Build Order

    async def one_base_dt_buildings(self):
        # Build a Twilight Council
        if self.structures(PYLON).exists:
            if self.structures(NEXUS).exists:
                pylon = self.structures(PYLON).ready.closest_to(
                    self.structures(NEXUS).random.position.towards(self.game_info.map_center, random.randrange(1, 8))
                )
                nexus = self.structures(NEXUS).random
            else:
                pylon = self.structures(PYLON).ready.random
                nexus = self.structures(PYLON).ready.random
            if (
                len(self.structures(SHIELDBATTERY)) >= 1
                and len(self.structures(PHOTONCANNON)) >= 2
                and self.structures(DARKSHRINE).exists
            ):
                self.MAX_GATES = 3
            else:
                self.MAX_GATES = 2
            # Build a Forge for Cannons
            if self.structures(FORGE).amount < 1 and not self.already_pending(FORGE):
                if self.can_afford(FORGE):
                    await self.build(FORGE, near=self.structures(PYLON).ready.random)
            if (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < self.MAX_GATES:
                if self.can_afford(GATEWAY):
                    await self.build(
                        GATEWAY,
                        near=self.structures(PYLON).ready.random,
                        max_distance=10,
                        random_alternative=False,
                        placement_step=5,
                    )
            elif len(self.structures(SHIELDBATTERY)) < (
                len(self.units(ZEALOT)) + len(self.units(STALKER)) + len(self.units(ADEPT))
            ) / 2 and not self.structures(SHIELDBATTERY):
                if self.can_afford(SHIELDBATTERY) and self.structures(NEXUS).ready.exists:
                    position = await self.find_placement(
                        SHIELDBATTERY,
                        self.main_base_ramp.barracks_correct_placement.rounded,
                        max_distance=10,
                        random_alternative=True,
                        placement_step=4,
                    )
                    await self.build(SHIELDBATTERY, near=position)
            # Build a Forge for Cannons
            elif self.structures(FORGE).amount < 1 and not self.already_pending(FORGE):
                if self.can_afford(FORGE):
                    await self.build(FORGE, near=self.structures(PYLON).ready.random)
            elif (
                self.structures(FORGE).ready.exists
                and not self.structures(PHOTONCANNON)
                and not self.already_pending(PHOTONCANNON)
            ):
                if self.can_afford(PHOTONCANNON) and self.structures(NEXUS).ready.exists:
                    position = await self.find_placement(
                        PHOTONCANNON,
                        self.main_base_ramp.barracks_correct_placement.rounded,
                        max_distance=10,
                        random_alternative=False,
                        placement_step=3,
                    )
                    await self.build(PHOTONCANNON, near=position)
            # Always build a cannon in mineral line for defense
            elif self.structures(FORGE).ready.exists:
                if self.structures(PHOTONCANNON).closer_than2(7, nexus).amount < 1:
                    if self.structures(PYLON).ready.closer_than2(7, nexus).amount < 1:
                        if self.can_afford(PYLON) and not self.already_pending(PYLON):
                            await self.build(
                                PYLON,
                                near=nexus.position.towards(self.game_info.map_center, random.randrange(-6, -1)),
                                random_alternative=False,
                                placement_step=1,
                            )
                    else:
                        if self.can_afford(PHOTONCANNON) and not self.already_pending(PHOTONCANNON):
                            await self.build(
                                PHOTONCANNON,
                                near=nexus.position.towards(self.game_info.map_center, random.randrange(-6, -1)),
                                random_alternative=False,
                                placement_step=1,
                            )

            if (
                not self.structures(TWILIGHTCOUNCIL).exists
                and not self.already_pending(TWILIGHTCOUNCIL)
            ):
                if self.can_afford(TWILIGHTCOUNCIL) and self.structures(CYBERNETICSCORE).ready.exists:
                    await self.build(
                        TWILIGHTCOUNCIL,
                        near=self.structures(PYLON).ready.random,
                        max_distance=10,
                        random_alternative=False,
                        placement_step=5,
                    )

            if (
                not self.structures(DARKSHRINE).exists
                and not self.already_pending(DARKSHRINE)
            ):
                if self.can_afford(DARKSHRINE) and self.structures(TWILIGHTCOUNCIL).ready.exists:
                    await self.build(DARKSHRINE, near=self.structures(PYLON).ready.closest_to(
                    self.structures(NEXUS).random.position.towards(self.game_info.map_center, random.randrange(-7, 2))))

            if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first))

            if (
                len(self.units(DARKTEMPLAR)) >= 2
                and self.structures(TWILIGHTCOUNCIL).ready.exists
                and self.can_afford(RESEARCH_CHARGE)
                and not self.charge_started
            ):
                twi = self.structures(TWILIGHTCOUNCIL).ready.first
                self.do(twi(RESEARCH_CHARGE))
                self.charge_started = self.time
                # print(self.charge_started)

    async def build_proxy_pylon_dt(self):
        if self.structures(TWILIGHTCOUNCIL).ready.exists and not self.proxy_built and self.can_afford(PYLON):
            p = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
            await self.build(PYLON, near=p)
            self.proxy_built = True

    async def one_base_dt_offensive_force(self):

        for gw in self.structures(GATEWAY).ready.idle:
            if (
                self.structures(CYBERNETICSCORE).ready.exists
                and len(self.units(ZEALOT)) > 4
                and not self.already_pending(TWILIGHTCOUNCIL)
                and not self.structures(TWILIGHTCOUNCIL).ready.exists
                and self.minerals < 150
            ):
                break
            elif (
                self.structures(TWILIGHTCOUNCIL).ready.exists
                and not self.already_pending(DARKSHRINE)
                and not self.structures(DARKSHRINE).ready.exists
                and self.minerals < 150
            ):
                break
            elif (
                self.structures(GATEWAY).ready.exists
                and self.structures(DARKSHRINE).ready.exists
                and self.can_afford(DARKTEMPLAR)
                and self.supply_left > 1
            ):
                self.do(gw.train(DARKTEMPLAR))
            elif (
                self.structures(GATEWAY).ready.exists
                and self.structures(CYBERNETICSCORE).ready.exists
                and not self.units(STALKER)
                and self.can_afford(STALKER)
                and self.supply_left > 1
            ):
                self.do(gw.train(STALKER))
            elif (
                self.structures(GATEWAY).ready.exists
                and self.structures(CYBERNETICSCORE).ready.exists
                and self.units(STALKER)
                and len(self.units(ZEALOT)) / len(self.units(STALKER)) > 3
                and self.can_afford(STALKER)
                and self.supply_left > 1
            ):
                self.do(gw.train(STALKER))
            elif (
                self.structures(GATEWAY).ready.exists
                and self.structures(CYBERNETICSCORE).ready.exists
                and self.can_afford(ZEALOT)
                and self.supply_left > 1
            ):
                self.do(gw.train(ZEALOT))
            elif self.structures(GATEWAY).ready.exists and self.minerals > 250 and self.supply_left > 1:
                self.do(gw.train(ZEALOT))

        for wg in self.structures(WARPGATE).ready:
            abilities = await self.get_available_abilities(wg)
            if WARPGATETRAIN_ZEALOT in abilities:
                if self.structures(SHIELDBATTERY).ready.exists:
                    pylon = self.structures(PYLON).closest_to(self.structures(SHIELDBATTERY).random)
                else:
                    pylon = self.structures(PYLON).ready.random
                pos = pylon.position.to2.random_on_distance(random.randrange(1, 6))
                warp_place = await self.find_placement(WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                if (
                    self.structures(TWILIGHTCOUNCIL).ready.exists
                    and not self.already_pending(DARKSHRINE)
                    and not self.structures(DARKSHRINE).ready.exists
                    and self.minerals < 150
                ):
                    break
                elif self.structures(DARKSHRINE).ready.exists and self.minerals < 130 and self.vespene < 130:
                    break
                elif self.structures(DARKSHRINE).ready.exists and self.can_afford(DARKTEMPLAR) and self.supply_left > 1:
                    proxy_pylon = self.structures(PYLON).closest_to(self.enemy_start_locations[0])
                    pos = proxy_pylon.position.to2.random_on_distance(random.randrange(1, 6))
                    warp_place_dt = await self.find_placement(WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                    self.do(wg.warp_in(DARKTEMPLAR, warp_place_dt))
                elif len(self.units(DARKTEMPLAR)) >= 3 and self.can_afford(STALKER) and self.supply_left > 1:
                    self.do(wg.warp_in(STALKER, warp_place))
                elif not self.units(STALKER) and self.can_afford(STALKER) and self.supply_left > 1:
                    self.do(wg.warp_in(STALKER, warp_place))
                elif (
                    self.units(STALKER)
                    and len(self.units(ZEALOT)) / len(self.units(STALKER)) > 3
                    and self.can_afford(STALKER)
                    and self.supply_left > 1
                ):
                    self.do(wg.warp_in(STALKER, warp_place))
                elif (
                    self.structures(WARPGATE).ready.exists
                    and self.vespene > 150
                    and self.minerals > 150
                    and self.can_afford(STALKER)
                    and self.supply_left > 1
                ):
                    self.do(wg.warp_in(STALKER, warp_place))
                # elif self.structures(WARPGATE).ready.exists and self.vespene > 150 and self.minerals > 150 and len(self.enemy_units.of_type(UnitTypeId.BANSHEE)) >= 1 and self.can_afford(STALKER) and self.supply_left > 1:
                #     self.do(wg.warp_in(STALKER, warp_place))
                # elif self.structures(WARPGATE).ready.exists and self.vespene > 150 and self.minerals > 150 and len(self.enemy_units.of_type(UnitTypeId.BANSHEE)) == 0 and self.can_afford(ADEPT) and self.supply_left > 1:
                #     self.do(wg.warp_in(ADEPT, warp_place))
                elif self.structures(WARPGATE).ready.exists and self.minerals > 250 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))

    async def dt_unit_control(self):

        # defend nexus if there is no proxy pylon
        if not self.gathered:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore
                    ).closer_than2(self.threat_proximity, structure.position)
                    if threats:
                        break
                if threats:
                    break
            if threats and not self.defend:
                self.defend = True
                self.back_home = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif threats and self.defend:
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT).idle:
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))
            elif not threats and self.back_home and self.structures(NEXUS).exists:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(1, 2))
                )
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif not threats and self.structures(NEXUS).exists:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(1, 2))
                )
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT).idle:
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))

        # attack_enemy_start
        if self.proxy_built and len(self.units(DARKTEMPLAR)) >= 1:
            if self.time > self.do_something_after and self.enemy_structures.exists:
                all_enemy_base = self.enemy_structures
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target_exe = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    attack_target_main = self.enemy_start_locations[0].random_on_distance(random.randrange(1, 5))
                else:
                    attack_target_main = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(-5, -1))
                    attack_target_exe = attack_target_main
                if attack_target_main and not self.first_attack:
                    dt1 = self.units(DARKTEMPLAR)[0]
                    self.do(
                        dt1(
                            RALLY_UNITS,
                            self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(-5, -1)),
                        )
                    )
                    self.first_attack = True
                    print(
                        "--- First Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Dark-Templars: ",
                        len(self.units(DARKTEMPLAR)),
                        "and Adepts: ",
                        len(self.units(ADEPT)),
                        "and Zealots: ",
                        len(self.units(ZEALOT)),
                    )
                if self.first_attack:
                    for dt in self.units(DARKTEMPLAR).idle:
                        if self.enemy_structures.of_type(UnitTypeId.SPORECRAWLER):
                            # print('Attacking Spore')
                            self.do(
                                dt.attack(
                                    self.enemy_structures.of_type(UnitTypeId.SPORECRAWLER).closest_to(dt.position)
                                )
                            )
                        elif self.enemy_units.of_type({UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}):
                            # print('Attacking Drone')
                            self.do(
                                dt.attack(
                                    self.enemy_units.of_type(
                                        {UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}
                                    ).closest_to(dt.position)
                                )
                            )
                        else:
                            # print('Attacking Else')
                            self.do(dt.attack(attack_target_exe))

        # Switch to Archons
        if self.first_attack and not self.dts_detected and self.units(DARKTEMPLAR).random.shield < 1:
            self.dts_detected = True
            # print('DTs detected!!')

        if self.dts_detected:
            for dt in self.units(DARKTEMPLAR).idle:
                # Get back to Base to be morphed to Archons savely
                self.do(
                    dt.move(self.structures(PYLON).closest_to(self.structures(SHIELDBATTERY).random)))
            if len(self.units(DARKTEMPLAR).ready) >= 2:
                dt1 = self.units(DARKTEMPLAR).ready.random
                dt2 = next((dt for dt in self.units(DARKTEMPLAR).ready.closer_than2(10, dt1.position) if
                            dt.tag != dt1.tag), None)
                if dt2:
                    # print('trying morph')
                    command = raw_pb.ActionRawUnitCommand(
                        ability_id=MORPH_ARCHON.value,
                        unit_tags=[dt1.tag, dt2.tag],
                        queue_command=False
                    )
                    action = raw_pb.ActionRaw(unit_command=command)
                    await self._client._execute(action=sc_pb.RequestAction(
                        actions=[sc_pb.Action(action_raw=action)]
                    ))

        if self.charge_started > 0 and self.time - self.charge_started >= 90:
            if self.time > self.do_something_after:
                all_enemy_base = self.enemy_structures.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                )
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                elif all_enemy_base.exists:
                    next_enemy_base = all_enemy_base.closest_to(self.game_info.map_center)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                else:
                    attack_target = self.game_info.map_center.random_on_distance(
                        random.randrange(12, 70 + int(self.time / 60))
                    )
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)
                if self.gathered and not self.second_attack:
                    for st in self.units(STALKER):
                        self.do(st.attack(attack_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(attack_target))
                    for dt in self.units(DARKTEMPLAR):
                        self.do(dt.attack(attack_target))
                    for ar in self.units(ARCHON):
                        self.do(ar.attack(attack_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(attack_target))
                    self.second_attack = True
                    print(
                        "--- Second Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Darktemplars: ",
                        len(self.units(DARKTEMPLAR)),
                        "and Archons: ",
                        len(self.units(ARCHON)),
                        "and Adepts: ",
                        len(self.units(ADEPT)),
                        "and Zealots: ",
                        len(self.units(ZEALOT)),
                    )
                if gather_target and not self.second_attack and not self.enemy_units.of_type(UnitTypeId.BANSHEE):
                    for st in self.units(STALKER):
                        self.do(st.attack(gather_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(gather_target))
                    for dt in self.units(DARKTEMPLAR).idle:
                        self.do(dt.attack(gather_target))
                    for ar in self.units(ARCHON):
                        self.do(ar.attack(gather_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(gather_target))
                    wait = 30
                    self.do_something_after = self.time + wait
                    self.gathered = True
                if self.second_attack:
                    for st in self.units(STALKER).idle:
                        self.do(st.attack(attack_target))
                    for ad in self.units(ADEPT).idle:
                        self.do(ad.attack(attack_target))
                    for dt in self.units(DARKTEMPLAR).idle:
                        self.do(dt.attack(attack_target))
                    for ar in self.units(ARCHON).idle:
                        self.do(ar.attack(attack_target))
                    for zl in self.units(ZEALOT).idle:
                        self.do(zl.attack(attack_target))

        # if self.second_attack:
        #     threats = []
        #     for structure_type in self.defend_around:
        #         for structure in self.structures(structure_type):
        #             threats += self.enemy_units.filter(lambda unit: unit.type_id not in self.units_to_ignore).closer_than2(self.threat_proximity, structure.position)
        #             if threats:
        #                 break
        #         if threats:
        #             break
        #     if threats and not self.defend:
        #         self.defend = True
        #         self.back_home = True
        #         defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
        #         for se in self.units(DARKTEMPLAR).idle:
        #             self.do(se.attack(defence_target))
        #     elif threats and self.defend:
        #         defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
        #         for se in self.units(DARKTEMPLAR).idle:
        #             self.do(se.attack(defence_target))
        #     elif not threats and self.back_home and self.structures(NEXUS).exists:
        #         self.back_home = False
        #         self.defend = False
        #         defence_target = self.structures(NEXUS).closest_to(self.game_info.map_center).position.towards(
        #             self.game_info.map_center, random.randrange(8, 10))
        #         for se in self.units(DARKTEMPLAR).idle:
        #             self.do(se.attack(defence_target))
        #     elif not threats and self.structures(NEXUS).exists:
        #         self.back_home = False
        #         self.defend = False
        #         defence_target = self.structures(NEXUS).closest_to(self.game_info.map_center).position.towards(
        #             self.game_info.map_center, random.randrange(8, 10))
        #         for se in self.units(DARKTEMPLAR).idle:
        #             self.do(se.attack(defence_target))

        # Switch to Archons
        # if self.first_attack and len(self.units(DARKTEMPLAR)) < 2:
        # Currently not supported by the API =(
        #     return

        # seek & destroy
        if self.first_attack and not self.enemy_structures.exists and self.time > self.do_something_after:

            for se in self.units(DARKTEMPLAR).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(se.attack(attack_target))
            for ar in self.units(ARCHON).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60)))
                self.do(ar.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            for ad in self.units(ADEPT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(ad.attack(attack_target))
            self.do_something_after = self.time + 5

        # execute actions


    # Specific Functions for One Base VR Build Order

    async def one_base_vr_buildings(self):
        # Build a Twilight Council
        if self.structures(PYLON).exists:
            if self.structures(NEXUS).exists:
                pylon = self.structures(PYLON).ready.closest_to(
                    self.structures(NEXUS).random.position.towards(self.game_info.map_center, random.randrange(-8, 2))
                )
            else:
                pylon = self.structures(PYLON).ready.random
            if (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < self.MAX_GATES and len(self.structures(STARGATE)) > 0:
                if self.can_afford(GATEWAY):
                    await self.build(
                        GATEWAY,
                        near=self.structures(PYLON).ready.random,
                        max_distance=10,
                        random_alternative=False,
                        placement_step=5,
                    )
            elif (
                len(self.structures(SHIELDBATTERY))
                < (len(self.units(ZEALOT)) + len(self.units(STALKER)) + len(self.units(ADEPT))) / 2
                and len(self.structures(SHIELDBATTERY)) < 2
                and not self.already_pending(SHIELDBATTERY)
            ):
                if self.can_afford(SHIELDBATTERY) and self.structures(NEXUS).ready.exists:
                    position = await self.find_placement(
                        SHIELDBATTERY,
                        self.main_base_ramp.barracks_correct_placement.rounded,
                        max_distance=10,
                        random_alternative=False,
                        placement_step=4,
                    )
                    await self.build(SHIELDBATTERY, near=position)
            elif (
                self.structures(CYBERNETICSCORE).ready.exists
                and self.can_afford(STARGATE)
                and not self.already_pending(STARGATE)
                and not self.structures(STARGATE).ready
            ):
                await self.build(STARGATE, near=pylon, max_distance=10, random_alternative=False, placement_step=5)
            elif (
                self.structures(CYBERNETICSCORE).ready.exists
                and self.can_afford(STARGATE)
                and not self.already_pending(STARGATE)
                and len(self.structures(STARGATE).ready) < 2
                and self.vespene > 300
            ):
                await self.build(STARGATE, near=pylon, max_distance=10, random_alternative=False, placement_step=5)

            if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
                if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                    await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.closest_to(self.structures(NEXUS).first))

            if (
                len(self.units(VOIDRAY)) >= 2
                and not self.structures(TWILIGHTCOUNCIL).exists
                and not self.already_pending(TWILIGHTCOUNCIL)
            ):
                if self.can_afford(TWILIGHTCOUNCIL) and self.structures(CYBERNETICSCORE).ready.exists:
                    await self.build(
                        TWILIGHTCOUNCIL,
                        near=self.structures(PYLON).ready.random,
                        max_distance=10,
                        random_alternative=False,
                        placement_step=5,
                    )

            if (
                len(self.units(VOIDRAY)) >= 2
                and self.structures(TWILIGHTCOUNCIL).ready.exists
                and self.can_afford(RESEARCH_CHARGE)
                and not self.charge_started
            ):
                twi = self.structures(TWILIGHTCOUNCIL).ready.first
                self.do(twi(RESEARCH_CHARGE))
                self.charge_started = self.time
                # print(self.charge_started)

    async def one_base_vr_offensive_force(self):

        for sg in self.structures(STARGATE).ready.idle:
            if len(self.units(ORACLE)) < 1 and not self.harass_started and self.can_afford(ORACLE) and self.supply_left > 2:
                self.do(sg.train(ORACLE))
            elif self.can_afford(VOIDRAY) and self.supply_left > 3:
                self.do(sg.train(VOIDRAY))
            # if self.can_afford(VOIDRAY) and self.supply_left > 3:
            #     self.do(sg.train(VOIDRAY))

        for gw in self.structures(GATEWAY).ready.idle:
            if (
                self.structures(CYBERNETICSCORE).ready.exists
                and len(self.units(ZEALOT)) + len(self.units(STALKER)) > 8
                and not self.already_pending(STARGATE)
                and len(self.structures(STARGATE).ready) < 2
                and self.minerals < 150
            ):
                break
            elif (
                self.structures(STARGATE).ready.exists
                and not self.already_pending(TWILIGHTCOUNCIL)
                and not self.structures(TWILIGHTCOUNCIL).ready.exists
                and self.minerals < 150
            ):
                break
            elif self.structures(GATEWAY).ready.exists and self.structures(STARGATE).ready.exists and self.minerals < 250:
                break
            elif (
                self.structures(GATEWAY).ready.exists
                and self.structures(CYBERNETICSCORE).ready.exists
                and len(self.units(ZEALOT)) >= 3
                and len(self.units(STALKER)) <= 5
                and self.can_afford(STALKER)
                and self.supply_left > 1
            ):
                self.do(gw.train(STALKER))
            elif self.structures(GATEWAY).ready.exists and self.can_afford(ZEALOT) and self.supply_left > 1:
                self.do(gw.train(ZEALOT))
            elif self.structures(GATEWAY).ready.exists and self.minerals > 250 and self.supply_left > 1:
                self.do(gw.train(ZEALOT))

        for wg in self.structures(WARPGATE).ready:
            abilities = await self.get_available_abilities(wg)
            if WARPGATETRAIN_ZEALOT in abilities:
                if self.structures(SHIELDBATTERY).ready.exists:
                    pylon = self.structures(PYLON).closest_to(self.structures(SHIELDBATTERY).random)
                else:
                    pylon = self.structures(PYLON).ready.random
                pos = pylon.position.to2.random_on_distance(random.randrange(1, 6))
                warp_place = await self.find_placement(WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                if (
                    self.structures(STARGATE).ready.exists
                    and not self.already_pending(TWILIGHTCOUNCIL)
                    and not self.structures(TWILIGHTCOUNCIL).ready.exists
                    and self.minerals < 150
                ):
                    break
                elif self.structures(STARGATE).ready.exists and self.minerals < 250 and self.vespene < 150:
                    break
                elif len(self.units(VOIDRAY)) >= 10 and self.can_afford(STALKER) and self.supply_left > 1:
                    self.do(wg.warp_in(STALKER, warp_place))
                elif len(self.units(ZEALOT)) >= 3 and len(self.units(STALKER)) <= 5 and self.can_afford(STALKER) and self.supply_left > 1:
                    self.do(wg.warp_in(STALKER, warp_place))
                if self.structures(WARPGATE).ready.exists and self.minerals > 350 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, warp_place))

    async def vr_unit_control(self):

        if len(self.units(ORACLE)) >= 1 and not self.harass_started:
            save_target_main = self.enemy_start_locations[0].towards(self.game_info.map_center, -25)
            or1 = self.units(ORACLE)[0]
            print('X:', self.game_info.map_center[0] - self.start_location[0], 'Y:',
                  self.game_info.map_center[1] - self.start_location[1])
            if self.game_info.map_center[0] - self.start_location[0] < 0:
                safe_spot1 = 1
            else:
                safe_spot1 = (self.game_info.map_center[0] * 2) - 1
            if self.game_info.map_center[1] - self.start_location[1] > 0:
                safe_spot2 = 1
            else:
                safe_spot2 = (self.game_info.map_center[1] * 2) -1
            print((safe_spot1, safe_spot2))
            print(save_target_main)
            self.do(or1.move(Point2((safe_spot1, safe_spot2))))
            self.do(or1.move(save_target_main, queue=True))
            self.harass_started = True
            self.do_something_after_trap1 = self.time + 50
        elif len(self.units(ORACLE)) >= 1 and self.harass_started:
            if self.time > self.do_something_after_trap1:
                or1 = self.units(ORACLE)[0]
                attack_target_main = self.enemy_start_locations[0].towards(self.game_info.map_center, -3)
                save_target_main = self.enemy_start_locations[0].towards(self.game_info.map_center, -25)
                if or1.shield_percentage > 0.5 and or1.energy_percentage > 0.25:
                    print('Building Trap in mineral line')
                    self.do(or1(BEHAVIOR_PULSARBEAMON))
                    if self.enemy_units.of_type({UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}):
                        # print('Attacking Drone')
                        self.do(
                            or1.attack(
                                self.enemy_units.of_type(
                                    {UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}
                                ).closest_to(or1.position)
                            )
                        )
                    else:
                        # print('Attacking Else')
                        self.do(or1.attack(attack_target_main))


                    # self.do(or1(BUILD_STASISTRAP, attack_target_main))
                    # self.do_something_after_trap1 = self.time + 20
                    # self.do_something_after_trap2 = self.time + 10
                elif or1.shield_percentage < 0.1 or or1.energy_percentage < 0.02:
                    self.do(or1(BEHAVIOR_PULSARBEAMOFF))
                    self.do(or1.move(save_target_main))
                    print('Trap placed, moving out again')
            # elif self.time > self.do_something_after_trap2:
            #     or1 = self.units(ORACLE)[0]
            #     save_target_main = self.enemy_start_locations[0].towards(self.game_info.map_center, -25)
            #     self.do(or1.move(save_target_main))
            #     print('Trap placed, moving out again')

        # defend nexus if there is no proxy pylon
        if not self.gathered:
            threats = []
            for structure_type in self.defend_around:
                for structure in self.structures(structure_type):
                    threats += self.enemy_units.filter(
                        lambda unit: unit.type_id not in self.units_to_ignore
                    ).closer_than2(self.threat_proximity, structure.position)
                    if threats:
                        break
                if threats:
                    break
            if threats and not self.defend:
                self.defend = True
                self.back_home = True
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for vr in self.units(VOIDRAY):
                    self.do(vr.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif threats and self.defend:
                defence_target = threats[0].position.random_on_distance(random.randrange(1, 3))
                for vr in self.units(VOIDRAY).idle:
                    self.do(vr.attack(defence_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT).idle:
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))
            elif not threats and self.back_home and self.structures(NEXUS).exists:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(8, 10))
                )
                for vr in self.units(VOIDRAY):
                    self.do(vr.attack(defence_target))
                for st in self.units(STALKER):
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT):
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT):
                    self.do(zl.attack(defence_target))
            elif not threats and self.structures(NEXUS).exists:
                self.back_home = False
                self.defend = False
                defence_target = (
                    self.structures(NEXUS)
                    .closest_to(self.game_info.map_center)
                    .position.towards(self.game_info.map_center, random.randrange(8, 10))
                )
                for vr in self.units(VOIDRAY).idle:
                    self.do(vr.attack(defence_target))
                for st in self.units(STALKER).idle:
                    self.do(st.attack(defence_target))
                for ad in self.units(ADEPT).idle:
                    self.do(ad.attack(defence_target))
                for zl in self.units(ZEALOT).idle:
                    self.do(zl.attack(defence_target))

        # Attack!
        if self.charge_started > 0 and self.time - self.charge_started >= 90:
            if self.time > self.do_something_after:
                all_enemy_base = self.enemy_structures.filter(
                    lambda unit: unit.type_id not in self.units_to_ignore
                )
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = next_enemy_base.position.towards(self.structures(NEXUS).first.position, 40)
                elif all_enemy_base.exists:
                    next_enemy_base = all_enemy_base.closest_to(self.game_info.map_center)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 17)
                else:
                    attack_target = self.game_info.map_center.random_on_distance(
                        random.randrange(12, 70 + int(self.time / 60))
                    )
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)
                if self.gathered and not self.first_attack:
                    for st in self.units(STALKER):
                        self.do(st.attack(attack_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(attack_target))
                    for vr in self.units(VOIDRAY):
                        self.do(vr.attack(attack_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(attack_target))
                    self.first_attack = True
                    print(
                        "--- First Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Voidrays: ",
                        len(self.units(VOIDRAY)),
                        "and Adepts: ",
                        len(self.units(ADEPT)),
                        "and Zealots: ",
                        len(self.units(ZEALOT)),
                    )
                if gather_target and not self.first_attack:
                    for st in self.units(STALKER):
                        self.do(st.attack(gather_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(gather_target))
                    for vr in self.units(VOIDRAY):
                        self.do(vr.attack(gather_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(gather_target))
                    wait = 30
                    self.do_something_after = self.time + wait
                    self.gathered = True
                if self.first_attack:
                    for st in self.units(STALKER).idle:
                        self.do(st.attack(attack_target))
                    for ad in self.units(ADEPT).idle:
                        self.do(ad.attack(attack_target))
                    for vr in self.units(VOIDRAY).idle:
                        self.do(vr.attack(attack_target))
                    for zl in self.units(ZEALOT).idle:
                        self.do(zl.attack(attack_target))

        # seek & destroy
        if self.first_attack and not self.enemy_structures.exists and self.time > self.do_something_after:

            for vr in self.units(VOIDRAY).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(vr.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            for ad in self.units(ADEPT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(ad.attack(attack_target))
            self.do_something_after = self.time + 5

        # execute actions


    async def destroy_lifted_buildings(self):
        if (len(self.structures(GATEWAY)) + len(self.structures(WARPGATE))) < self.MAX_GATES:
            if self.can_afford(GATEWAY):
                await self.build(GATEWAY, near=self.structures(PYLON).ready.random)

        if self.structures(GATEWAY).ready.exists and not self.structures(CYBERNETICSCORE):
            if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                await self.build(CYBERNETICSCORE, near=self.structures(PYLON).ready.random)

        if self.structures(PYLON).ready.exists:
            pylon = self.structures(PYLON).ready.random
            if (
                self.structures(CYBERNETICSCORE).ready.exists
                and self.can_afford(STARGATE)
                and not self.already_pending(STARGATE)
                and len(self.structures(STARGATE).ready) < 3
            ):
                await self.build(STARGATE, near=pylon)

        for wg in self.structures(WARPGATE).ready:
            abilities = await self.get_available_abilities(wg)
            if WARPGATETRAIN_ZEALOT in abilities:
                if self.structures(WARPGATE).ready.exists and self.minerals > 850 and self.supply_left > 1:
                    self.do(wg.warp_in(ZEALOT, self.structures(PYLON).ready.random))

        if self.supply_left > 3:
            for sg in self.structures(STARGATE).ready.idle:
                if self.can_afford(VOIDRAY):
                    self.do(sg.train(VOIDRAY))

        elif self.supply_used > 196:
            if self.units(ZEALOT).exists:
                target = self.units(ZEALOT).random
            elif self.units(ADEPT).exists:
                target = self.units(ADEPT).random
            elif self.units(IMMORTAL).exists:
                target = self.units(IMMORTAL).random
            elif self.units(COLOSSUS).exists:
                target = self.units(COLOSSUS).random
            elif self.units(SENTRY).exists:
                target = self.units(SENTRY).random
            elif self.units(STALKER).exists:
                target = self.units(STALKER).random
            else:
                target = self.game_info.map_center

            for st in self.units(STALKER):
                self.do(st.attack(target))
            for se in self.units(SENTRY):
                self.do(se.attack(target))
            for zl in self.units(ZEALOT):
                self.do(zl.attack(target))
            for ad in self.units(ADEPT):
                self.do(ad.attack(target))

        if self.supply_used > 100:
            if self.time > self.do_something_after:
                all_enemy_base = self.enemy_structures
                if all_enemy_base.exists and self.structures(NEXUS).exists:
                    next_enemy_base = all_enemy_base.closest_to(self.structures(NEXUS).first)
                    attack_target = next_enemy_base.position.random_on_distance(random.randrange(1, 5))
                    gather_target = next_enemy_base.position.towards(self.structures(NEXUS).first.position, 40)
                else:
                    attack_target = self.enemy_start_locations[0].towards(
                        self.game_info.map_center, random.randrange(15, 20)
                    )
                    gather_target = self.game_info.map_center.towards(self.enemy_start_locations[0], 20)
                if self.gathered and not self.final_attack:
                    for st in self.units(STALKER):
                        self.do(st.attack(attack_target))
                    for vr in self.units(VOIDRAY):
                        self.do(vr.attack(attack_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(attack_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(attack_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(attack_target))
                    self.final_attack = True
                    print(
                        "--- Final Attack started --- @: ",
                        self.time,
                        "with Stalkers: ",
                        len(self.units(STALKER)),
                        "and Adepts: ",
                        len(self.units(ADEPT)),
                        "and Voidrays: ",
                        len(self.units(VOIDRAY)),
                    )
                if gather_target and not self.final_attack:
                    for st in self.units(STALKER):
                        self.do(st.attack(gather_target))
                    for vr in self.units(VOIDRAY):
                        self.do(vr.attack(gather_target))
                    for se in self.units(SENTRY):
                        self.do(se.attack(gather_target))
                    for zl in self.units(ZEALOT):
                        self.do(zl.attack(gather_target))
                    for ad in self.units(ADEPT):
                        self.do(ad.attack(gather_target))
                    wait = 30
                    self.do_something_after = self.time + wait
                    self.gathered = True
                if self.final_attack:
                    for st in self.units(STALKER).idle:
                        self.do(st.attack(attack_target))
                    for vr in self.units(VOIDRAY).idle:
                        self.do(vr.attack(attack_target))
                    for se in self.units(SENTRY).idle:
                        self.do(se.attack(attack_target))
                    for zl in self.units(ZEALOT).idle:
                        self.do(zl.attack(attack_target))
                    for ad in self.units(ADEPT).idle:
                        self.do(ad.attack(attack_target))

        # seek & destroy
        if self.final_attack and not self.enemy_structures.exists and self.time > self.do_something_after:

            for se in self.units(SENTRY).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(se.attack(attack_target))
            for vr in self.units(VOIDRAY).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(vr.attack(attack_target))
            for st in self.units(STALKER).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(st.attack(attack_target))
            for zl in self.units(ZEALOT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(zl.attack(attack_target))
            for ad in self.units(ADEPT).idle:
                attack_target = self.game_info.map_center.random_on_distance(
                    random.randrange(12, 70 + int(self.time / 60))
                )
                self.do(ad.attack(attack_target))
            self.do_something_after = self.time + 5

        # execute actions
    # Find enemy natural expansion location (Thanks @ CannonLover)
    async def find_enemy_natural(self):
        closest = None
        distance = math.inf
        for el in self.expansion_locations:
            if Point2(self.enemy_start_locations[0]).position.distance_to(el) < 15:
                continue

            # if any(map(is_near_to_expansion, )):
            # already taken
            #    continue

            d = await self._client.query_pathing(self.enemy_start_locations[0], el)
            if d is None:
                continue

            if d < distance:
                distance = d
                closest = el

        return closest