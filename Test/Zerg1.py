import sc2
from sc2 import run_game, maps, Race, Difficulty, position, Result, game_state, ActionResult
from sc2.player import Bot, Computer
from sc2.constants import CORRUPTOR, BROODLORD, DRONE, HYDRALISK, INFESTOR, LARVA, MUTALISK, OVERLORD, OVERSEER, QUEEN, \
    ROACH, ULTRALISK, ZERGLING, BANELING, BROODLING, CHANGELING, INFESTEDTERRAN, BANELINGNEST, CREEPTUMOR, \
    EVOLUTIONCHAMBER, EXTRACTOR, HATCHERY, LAIR, HIVE, HYDRALISKDEN, INFESTATIONPIT, NYDUSNETWORK, ROACHWARREN, \
    SPAWNINGPOOL, SPINECRAWLER, SPIRE, GREATERSPIRE, SPORECRAWLER, ULTRALISKCAVERN, EFFECT_INJECTLARVA, BUILD_CREEPTUMOR_QUEEN, \
    AbilityId, CREEPTUMORQUEEN, CREEPTUMORBURROWED, BUILD_CREEPTUMOR_TUMOR, BuffId, QUEENSPAWNLARVATIMER, ZERGBUILD_CREEPTUMOR
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
        self.UnCreepable = []
        self.RequestVisibilty = []
        self.PositionsVisibiltySent = []
        self.OverlordsSent = []
        self.expansionLocationsSorted = []
        self.Initial = 0

    async def on_step(self, iteration):
        #pos = self.start_location.position.towards(self.enemy_start_locations[0], 7)
        #print(self.state.creep.is_set(pos))
        self.ElapsedTime = (self.state.game_loop / 22.4) / 60  # Time in min since start of game
        await self.manufacture()#Commands for making units
        await self.distribute_workers()
        await self.Queen_Control()
        await self.Creep_Control()
        await self.Intel()
        await self.Overlord_Control()

        if(self.Initial == 0):
            for location in self.expansion_locations:
                self.expansionLocationsSorted.append([location, self.enemy_start_locations[0].distance_to(location)])
            self.expansionLocationsSorted.sort(key=lambda x: x[1])
            self.Initial = 1
            print(self.expansionLocationsSorted)

    async def Intel(self):
        self.CreepMap = np.reshape(np.array(list(self.state.creep.data)), (self.state.creep.height, self.state.creep.width))
        self.VisMap = np.reshape(np.array(list(self.state.visibility.data)), (self.state.visibility.height, self.state.visibility.width))
        self.UnitMap = np.zeros((self.state.visibility.height, self.state.visibility.width))
        #self.PlaceMap = np.reshape(np.array(list(self.game_info.placement_grid)), (self.state.visibility.height, self.state.visibility.width))
        #map_ramps
        #playable_area
        #pathing_grid

        if (self.units(QUEEN).exists and -1 > 0):
            unit = self.units(QUEEN)[0]
            print(str(unit.position) + " " + str(
                self.VisMap[int(self.state.creep.height - unit.position[1])][int(unit.position[0])]))

        for unit in self.units:
            self.UnitMap[int(self.state.creep.height - unit.position[1])][int(unit.position[0])] = 2

        UnitImage = np.array(self.UnitMap * 255, dtype=np.uint8)
        VisImage = np.array(self.VisMap * 127, dtype=np.uint8)
        CreepImage = np.array(self.CreepMap * 255, dtype=np.uint8)
        #PlaceImage = np.array(self.PlaceMap * 255, dtype=np.uint8)

        #resized = cv2.resize(VisMap, (200,200))  # size image up for display on screen
        cv2.imshow('Units', UnitImage)
        cv2.imshow('Visibility', VisImage)
        cv2.imshow('Creep', CreepImage)
        #cv2.imshow('Creep', PlaceImage)
        cv2.waitKey(1)

                    #print(str(await self.can_place(ZERGBUILD_CREEPTUMOR, position.Point2(position.Pointlike(([ x, y ]))))) + " " + str(x) + " " + str(y))


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
                #none = 1
                await self.do(hatchers.train(QUEEN))
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
            if not queen.tag in self.incomingBuffingQueens and queen.energy > 25:# Randomly place creep near queens
                test = 1
                #await self.do(queen(BUILD_CREEPTUMOR_QUEEN, self.random_location_variance(queen.position, 2)))

    async def Creep_Control(self):#Control the tumors that queens lay
        for creep in self.units(CREEPTUMORBURROWED).idle:
            abilities = await self.get_available_abilities(creep)#Check if expandable
            if AbilityId.BUILD_CREEPTUMOR_TUMOR in abilities:#expand randomly !!!!!!!!!!!!!!!!Change to be smart
                CreepPos = creep.position
                #if self.state.creep
                #await self.do(creep(BUILD_CREEPTUMOR_TUMOR, pos))
                BestPosition = []
                BestLength = 10000
                MaxRange = 13
                Positions = []
                for PossibleCreepPositionX in range(MaxRange):
                    for PossibleCreepPositionY in range(MaxRange):
                        Positions.append(position.Point2(position.Pointlike((PossibleCreepPositionX + CreepPos[0] - int(MaxRange/2),PossibleCreepPositionY + CreepPos[1] - int(MaxRange/2)))))

                random.shuffle(Positions)
                Length = 0
                pos = self.enemy_start_locations[0].position
                for position1 in Positions:
                    #for OtherCreep in self.units(CREEPTUMORBURROWED):
                    Length = math.sqrt(((position1[0] - pos[0]) * (position1[0] - pos[0])) + ((position1[1] - pos[1]) * (position1[1] - pos[1])))
                    LengthActual = math.sqrt(((position1[0] - CreepPos[0]) * (position1[0] - CreepPos[0])) + ((position1[1] - CreepPos[1]) * (position1[1] - CreepPos[1])))
                    print(BestLength)
                    if((Length < BestLength and Length != 0) and position1 not in self.UnCreepable and abs(LengthActual <= MaxRange)):
                        BestLength = Length
                        print(BestLength)
                        BestPosition = position1

                if(BestPosition != []):
                    err = await self.do(creep(BUILD_CREEPTUMOR_TUMOR, position.Point2(position.Pointlike((BestPosition[0],BestPosition[1])))))
                    print(err)
                    if(err == ActionResult.CantSeeBuildLocation):
                        self.RequestVisibilty.append(BestPosition)
                    elif(err):
                        self.UnCreepable.append(BestPosition)
        #print(self.UnCreepable)
        #d = await self._client.query_pathing(th.position, el)

    async def Overlord_Control(self):

        for Overlord in range(len(self.units(OVERLORD).idle)):
            if(self.units(OVERLORD).idle[Overlord] not in self.OverlordsSent and self.expansionLocationsSorted != []):
                print(len(self.expansionLocationsSorted))
                print(len(self.OverlordsSent))
                if(len(self.expansionLocationsSorted) > len(self.OverlordsSent)):
                    Position = self.expansionLocationsSorted[len(self.OverlordsSent)][0]
                    await self.do(self.units(OVERLORD)[Overlord].attack(Position))
                    self.OverlordsSent.append(self.units(OVERLORD)[Overlord].tag)

        for Position in self.RequestVisibilty:
            if Position not in self.PositionsVisibiltySent:
                await self.do(self.units(OVERLORD).idle[0].attack(Position))
                self.PositionsVisibiltySent.append(Position)

run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Zerg, SentdeBot()),
    Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)