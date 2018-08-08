import sc2
from sc2 import run_game, maps, Race, Difficulty, position, Result
from sc2.player import Bot, Computer
from sc2.constants import CORRUPTOR, BROODLORD, DRONE, HYDRALISK, INFESTOR, LARVA, MUTALISK, OVERLORD, OVERSEER, QUEEN, \
    ROACH, ULTRALISK, ZERGLING, BANELING, BROODLING, CHANGELING, INFESTEDTERRAN, BANELINGNEST, CREEPTUMOR, \
    EVOLUTIONCHAMBER, EXTRACTOR, HATCHERY, LAIR, HIVE, HYDRALISKDEN, INFESTATIONPIT, NYDUSNETWORK, ROACHWARREN, \
    SPAWNINGPOOL, SPINECRAWLER, SPIRE, GREATERSPIRE, SPORECRAWLER, ULTRALISKCAVERN, EFFECT_INJECTLARVA, BUILD_CREEPTUMOR_QUEEN, \
    AbilityId, CREEPTUMORQUEEN, CREEPTUMORBURROWED, BUILD_CREEPTUMOR_TUMOR
import random
import cv2
import numpy as np
import time

class SentdeBot(sc2.BotAI):
    def __init__(self):
        self.MostNeededTroop = 0
        self.EarlySpawnPool = 0

    async def on_step(self, iteration):
        self.ElapsedTime = (self.state.game_loop / 22.4) / 60  # Time in min since start of game
        await self.manufacture()
        await self.distribute_workers()
        await self.Queen_Control()
        await self.Creep_Control()

    def EvaluateArmy(self):
        if(len(self.units(OVERLORD)) + self.already_pending(OVERLORD) < 2 or (self.supply_left < 6 and not self.already_pending(OVERLORD) and self.ElapsedTime > 1)):
            self.MostNeededTroop = 1 #Overlord
        elif len(self.units(DRONE)) < len(self.units(HATCHERY))*16 and (self.ElapsedTime > 1.3 or (self.already_pending(SPAWNINGPOOL) and self.already_pending(HATCHERY))) or len(self.units(DRONE)) < 14 and self.ElapsedTime < 1.3:
            self.MostNeededTroop = 2 #Drone
        elif len(self.units(SPAWNINGPOOL)) < 1 and not self.already_pending(SPAWNINGPOOL):
            self.MostNeededTroop = 3 #SpawningPool
        elif len(self.units(HATCHERY)) < 2 and not self.already_pending(HATCHERY):
            self.MostNeededTroop = 4  # Hatchery
        else:
            self.MostNeededTroop = 6  # Zerglings

        if(len(self.units(SPAWNINGPOOL)) < 1 and not self.already_pending(SPAWNINGPOOL) and self.ElapsedTime > .6 and self.EarlySpawnPool == 0):
            self.MostNeededTroop = 3
            self.EarlySpawnPool = 1

        if(self.ElapsedTime < 2 and len(self.units(EXTRACTOR)) + self.already_pending(EXTRACTOR) < 1 and len(self.units(SPAWNINGPOOL)) > 0 and (self.already_pending(HATCHERY) or len(self.units(HATCHERY)) > 1)):
            self.MostNeededTroop = 5


    async def manufacture(self):

        for hatchers in self.units(HATCHERY).ready.noqueue:
            if self.can_afford(QUEEN) and self.minerals > 150 and len(self.units(SPAWNINGPOOL)) > 0 and len(self.units(QUEEN)) < 2 * len(self.units(HATCHERY)):
                await self.do(hatchers.train(QUEEN))
                print(str(self.ElapsedTime) + " Queen")

        for larvae in self.units(LARVA).ready:
            self.EvaluateArmy()
            if self.MostNeededTroop == 1 and self.can_afford(OVERLORD):
                print(str(self.ElapsedTime) + " Overlord")
                await self.do(larvae.train(OVERLORD))

            elif self.MostNeededTroop == 2 and self.can_afford(DRONE) and self.supply_left > 0:
                print(str(self.ElapsedTime) + " Drone")
                await self.do(larvae.train(DRONE))

            elif self.MostNeededTroop == 3 and self.can_afford(SPAWNINGPOOL):
                print(str(self.ElapsedTime) + " SpawningPool")
                Hatchery = self.units(HATCHERY).ready.random
                await self.build(SPAWNINGPOOL, near=Hatchery)

            elif self.MostNeededTroop == 4 and self.can_afford(HATCHERY):
                print(str(self.ElapsedTime) + " Hatchery")
                await self.expand_now()

            elif self.MostNeededTroop == 5 and self.can_afford(EXTRACTOR):
                vaspene = self.state.vespene_geyser.closer_than(15.0, self.units(HATCHERY).ready[0])
                worker = self.select_build_worker(vaspene[0].position)
                if worker is not None:
                    print(str(self.ElapsedTime) + " Extractor")
                    await self.do(worker.build(EXTRACTOR, vaspene[0]))

            elif self.MostNeededTroop == 6 and self.can_afford(ZERGLING):
                print(str(self.ElapsedTime) + " Zergling")
                await self.do(larvae.train(ZERGLING))

    def random_location_variance(self, OrigionalLocation, Offset):
        x = OrigionalLocation[0]
        y = OrigionalLocation[1]

        x +=((random.randrange(-Offset,Offset)))
        y += ((random.randrange(-Offset, Offset)))

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]

        go_to = position.Point2(position.Pointlike((x,y)))
        return go_to

    async def Queen_Control(self):
        hatchery = self.units(HATCHERY).ready.first
        for queen in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities: #sptray hatcherys
                await self.do(queen(EFFECT_INJECTLARVA, hatchery))

            if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities:# Randomly place creep near queens
                await self.do(queen(BUILD_CREEPTUMOR_QUEEN, self.random_location_variance(queen.position, 2)))

    async def Creep_Control(self):
        for creep in self.units(CREEPTUMORBURROWED).idle:
            abilities = await self.get_available_abilities(creep)
            if AbilityId.BUILD_CREEPTUMOR_TUMOR in abilities:
                await self.do(creep(BUILD_CREEPTUMOR_TUMOR, self.random_location_variance(creep.position, 7)))

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Zerg, SentdeBot()),
    Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)