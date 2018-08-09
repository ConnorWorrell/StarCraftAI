import sc2
from sc2 import run_game, maps, Race, Difficulty, position, Result, game_state
from sc2.player import Bot, Computer
from sc2.constants import CORRUPTOR, BROODLORD, DRONE, HYDRALISK, INFESTOR, LARVA, MUTALISK, OVERLORD, OVERSEER, QUEEN, \
    ROACH, ULTRALISK, ZERGLING, BANELING, BROODLING, CHANGELING, INFESTEDTERRAN, BANELINGNEST, CREEPTUMOR, \
    EVOLUTIONCHAMBER, EXTRACTOR, HATCHERY, LAIR, HIVE, HYDRALISKDEN, INFESTATIONPIT, NYDUSNETWORK, ROACHWARREN, \
    SPAWNINGPOOL, SPINECRAWLER, SPIRE, GREATERSPIRE, SPORECRAWLER, ULTRALISKCAVERN, EFFECT_INJECTLARVA, BUILD_CREEPTUMOR_QUEEN, \
    AbilityId, CREEPTUMORQUEEN, CREEPTUMORBURROWED, BUILD_CREEPTUMOR_TUMOR, BuffId, QUEENSPAWNLARVATIMER
import random
import cv2
import numpy as np
import time
import math

class SentdeBot(sc2.BotAI):
    def __init__(self):
        self.MostNeededTroop = 0
        self.EarlySpawnPool = 0
        self.incomingBuffHacheries = []
        self.incomingBuffingQueens = []

    async def on_step(self, iteration):
        #pos = self.start_location.position.towards(self.enemy_start_locations[0], 7)
        #print(self.state.creep.is_set(pos))
        self.ElapsedTime = (self.state.game_loop / 22.4) / 60  # Time in min since start of game
        await self.manufacture()#Commands for making units
        await self.distribute_workers()
        await self.Queen_Control()
        await self.Creep_Control()
        await self.Intel()

    async def Intel(self):
        VisMap = np.reshape(np.array(list(self.state.creep.data)), (self.state.creep.height, self.state.creep.width))

        image = np.array(VisMap * 255, dtype = np.uint8)


        #resized = cv2.resize(VisMap, (200,200))  # size image up for display on screen
        cv2.imshow('Intel', image)
        cv2.waitKey(1)

        if(self.units(QUEEN).exists):
            unit = self.units(QUEEN)[0]
            print(str(unit.position) + " " + str(VisMap[int(unit.position[0]), int(unit.position[1])]))


        #print("Break")

    def EvaluateArmy(self):#Figures out what needs to be made
        if(len(self.units(OVERLORD)) + self.already_pending(OVERLORD) < 2 or (self.supply_left < 6 and not self.already_pending(OVERLORD) and self.ElapsedTime > 1) or (self.supply_left < 10 and len(self.units(QUEEN)) > 0)):
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

        for hatchers in self.units(HATCHERY).ready.noqueue:#Manufacture queen if you have 2 bases and have prerequesetes
            if self.can_afford(QUEEN) and self.minerals > 150 and len(self.units(SPAWNINGPOOL).ready) > 0 and len(self.units(QUEEN)) < 2 * len(self.units(HATCHERY)):
                none = 1
                #await self.do(hatchers.train(QUEEN))
                #print(str(self.ElapsedTime) + " Queen")

        for larvae in self.units(LARVA).ready:
            self.EvaluateArmy()#Request build target and build it
            if self.MostNeededTroop == 1 and self.can_afford(OVERLORD):#Overlord
                #print(str(self.ElapsedTime) + " Overlord")
                await self.do(larvae.train(OVERLORD))

            elif self.MostNeededTroop == 2 and self.can_afford(DRONE) and self.supply_left > 0:#Drone
                #print(str(self.ElapsedTime) + " Drone")
                await self.do(larvae.train(DRONE))

            elif self.MostNeededTroop == 3 and self.can_afford(SPAWNINGPOOL):#Spawning Pool
                #print(str(self.ElapsedTime) + " SpawningPool")
                Hatchery = self.units(HATCHERY).ready.random
                await self.build(SPAWNINGPOOL, near=self.start_location.position.towards(self.enemy_start_locations[0], 4))

            elif self.MostNeededTroop == 4 and self.can_afford(HATCHERY):#Hatchery
                #print(str(self.ElapsedTime) + " Hatchery")
                await self.expand_now()

            elif self.MostNeededTroop == 5 and self.can_afford(EXTRACTOR):#Extractor
                vaspene = self.state.vespene_geyser.closer_than(15.0, self.units(HATCHERY).ready[0])
                worker = self.select_build_worker(vaspene[0].position)
                if worker is not None:
                    #print(str(self.ElapsedTime) + " Extractor")
                    await self.do(worker.build(EXTRACTOR, vaspene[0]))

            elif self.MostNeededTroop == 6 and self.can_afford(ZERGLING):#Zergling
                #print(str(self.ElapsedTime) + " Zergling")
                await self.do(larvae.train(ZERGLING))

    def random_location_variance(self, OrigionalLocation, Offset):#take in location and output location randomly offset from it
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

    async def Queen_Control(self):#Control the queen
        hatcherys = self.units(HATCHERY).ready

        #for hachery in hatcherys:
            #if(hachery.has_buff(BuffId.QUEENSPAWNLARVATIMER) == False):

        incomingBuffingQueensDupe = self.incomingBuffingQueens[:]
        for queen in self.units(QUEEN):
            if(queen.tag in incomingBuffingQueensDupe):
                #await self.do(self.units.find_by_tag(queen.tag)(EFFECT_INJECTLARVA, self.units.find_by_tag(self.incomingBuffHacheries[self.incomingBuffingQueens.index(queen.tag)])))
                #self.units.find_by_tag(queen.tag)
                incomingBuffingQueensDupe.remove(queen.tag)
        #print(incomingBuffingQueensDupe)
        for DeadQueens in incomingBuffingQueensDupe:
            #print("QueenDead")
            index = self.incomingBuffingQueens.index(DeadQueens)
            self.incomingBuffingQueens.remove(self.incomingBuffingQueens[index])
            self.incomingBuffHacheries.remove(self.incomingBuffHacheries[index])


        for hachery in hatcherys:
            #print(str(self.incomingBuffHacheries) + str(self.incomingBuffingQueens))
            if hachery.tag in self.incomingBuffHacheries and hachery.has_buff(BuffId.QUEENSPAWNLARVATIMER) == True:
                index = self.incomingBuffHacheries.index(hachery.tag)
                self.incomingBuffHacheries.remove(hachery.tag)
                self.incomingBuffingQueens.remove(self.incomingBuffingQueens[index])

            if (hachery.has_buff(BuffId.QUEENSPAWNLARVATIMER) == False) and not hachery.tag in self.incomingBuffHacheries and len(self.units(QUEEN).idle) > 0:
                lowestDist = 100
                queen = self.units(QUEEN).idle.random
                for queenCandidate in self.units(QUEEN).idle: #select which queen, !!!!!!!!!!!Change to closest
                    abilities = await self.get_available_abilities(queenCandidate)  # Check abilities
                    if AbilityId.EFFECT_INJECTLARVA in abilities and queenCandidate.energy > 25 and not queenCandidate.tag in self.incomingBuffingQueens:  # sptray hatcherys
                        Dist = math.sqrt(((queenCandidate.position[0] - hachery.position[0]) + abs(queenCandidate.position[1] - hachery.position[1])) * ((queenCandidate.position[0] - hachery.position[0]) + abs(queenCandidate.position[1] - hachery.position[1])))
                        #print(Dist)
                        if Dist < lowestDist:
                            lowestDist = Dist
                            queen = queenCandidate
                abilities = await self.get_available_abilities(queen)  # Check abilities
                if AbilityId.EFFECT_INJECTLARVA in abilities and queen.energy > 25 and not queen.tag in self.incomingBuffingQueens:  # sptray hatcherys
                    #print(lowestDist)
                    await self.do(queen(EFFECT_INJECTLARVA, hachery))
                    self.incomingBuffHacheries.append(hachery.tag)
                    self.incomingBuffingQueens.append(queen.tag)

        for queen in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(queen)  # Check abilities
            if AbilityId.BUILD_CREEPTUMOR_QUEEN in abilities and len(self.units(CREEPTUMORBURROWED)) < 4 and not queen.tag in self.incomingBuffingQueens and queen.energy > 25:# Randomly place creep near queens
                await self.do(queen(BUILD_CREEPTUMOR_QUEEN, self.random_location_variance(queen.position, 2)))

    async def Creep_Control(self):#Control the tumors that queens lay
        for creep in self.units(CREEPTUMORBURROWED).idle:
            abilities = await self.get_available_abilities(creep)#Check if expandable
            if AbilityId.BUILD_CREEPTUMOR_TUMOR in abilities:#expand randomly !!!!!!!!!!!!!!!!Change to be smart
                pos = creep.position.towards(self.enemy_start_locations[0], 7)
                #if self.state.creep
                #await self.do(creep(BUILD_CREEPTUMOR_TUMOR, pos))

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Zerg, SentdeBot()),
    Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)