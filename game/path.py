import math
import random
import copy
import pygame
import track_set_types
from constants import *
from station import Station
from track import Track
from train import Train
from obstacle import Obstacle
from board_item_types import TrainSpeed_Multipliers

from timer import Timer

class Path:
    def __init__(self, board_tiles, board_rect, end_call, train_type, grid_dimensions, map):
        # Prevents updates on nonexisting game objects
        self.path_initated = False

        # Transfer board info
        self.board_tiles = board_tiles
        self.board_rect = board_rect
        self.end_call = end_call
        self.train_type = train_type
        self.grid_rows, self.grid_cols = grid_dimensions
        self.speed_multipliers = copy.deepcopy(TrainSpeed_Multipliers)

        # Create path objects
        self.prev_highlight, self.highlight = '', ''
        self.powerup_time = 0

        # clock
        self.start_spawning_train = False
        self.spawn_trains = False

        self.clock = None
        self.map = map

        # create a list for the train that will store in each cart
        self.train = []

        self.tiles_under = []
        self.create_stations()
        self.create_station_track()
    
    def add_tile_under(self, tile):
        x, y = tile
        if tile in self.tiles_under: return
        if tile not in self.tiles_under:
            self.tiles_under.append(tile)
            self.board_tiles[y][x].under_path = self

    def remove_tile_under(self, tile):
        x, y = tile
        self.tiles_under.remove(tile)

        self.board_tiles[y][x].under_path = None

    # Added By Kelvin Huang, April 28, 2024 
    # delete all reference to this path so the __del__ function works
    def remove_all_under(self):
        # Modified by Kelvin Huang, April 29, 2024
        # adjust deletion of references to work with multiple carts 

        # start from the end of the list to the beginning
        for index in range(len(self.tiles_under) - 1, -1, -1):
            # change it so ever path the train under to become None
            x, y = self.tiles_under[index]
            self.board_tiles[y][x].under_path = None

            # remove that tile x, y values that store in the list
            self.tiles_under.remove(self.tiles_under[index])
        
        # for testing
        '''
        for row in self.board_tiles:
            for tile in row:
                print(tile.under_path, end=" ")
            print("\n")
        '''
    # Creates start and end stations and saves their locations
    # start and end arent positions but are actually tile locatons (col, row)
    def create_stations(self):
        # Find big enough distanced station spots
        
        # check for surrounding station around the random generate point if there is one with in 2 block it will regenerate another one
        def surrounding_station(point):
            col_range = [point[0] - 2, point[0] + 2]
            if col_range[0] < 0: col_range[0] = 0
            if col_range[1] > self.grid_cols - 1: col_range[1] = self.grid_cols - 1

            row_range = [point[1] - 2, point[1] + 2]
            if row_range[0] < 0: row_range[0] = 0
            if row_range[1] > self.grid_rows - 1: row_range[1] = self.grid_rows - 1
            
            for i in range(row_range[0], row_range[1] + 1):
                for j in range(col_range[0], col_range[1] + 1):
                    if isinstance(self.board_tiles[i][j].attached, Station):
                        return True
            return False
        
        # check if train is near the edge of the board
        def near_edge(point):
            return (point[0] < 2 or self.grid_cols - 3 < point[0]) or (point[1] < 2 or self.grid_rows - 3 < point[1])
        
        start, end = (0, 0), (0, 0)

        searching_for_station = True

        # we don't want this while loop to run too much times so if the location is deems semi acceptable it will switch these
        # boolean variable to True so it would generate another of the point
        # point are acceptable if there are no surrounding station within 2 blocks
        # point lean towards the edge of the board preferable at most 2 blocks from the edge
        acceptable_start = False
        acceptable_end = False

        while searching_for_station:
            if acceptable_start == False:
                start = (random.randint(0, self.grid_cols - 1), random.randint(0, self.grid_rows - 1))

            if acceptable_end == False:
                end = (random.randint(0, self.grid_cols - 1), random.randint(0, self.grid_rows - 1))
            
            distance = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)

            if distance > 4:
                sur_start = surrounding_station(start)
                sur_end = surrounding_station(end)

                valid_start_terrain = self.board_tiles[start[1]][start[0]].terrain != 'water'
                valid_end_terrain = self.board_tiles[end[1]][end[0]].terrain != 'water'

                # check if there are station around start position

                if sur_start == False and near_edge(start) and valid_start_terrain: # and not invalid_in_front(start) | Add for front checking feature
                    acceptable_start = True

                if sur_end == False and near_edge(start) and valid_end_terrain:
                    acceptable_end = True
            
            if acceptable_start and acceptable_end: searching_for_station = False

                                                            # Modified by Matthew Selvaggi May-21-24
        self.color = random.choice(Colors.random_colors)    # Added modification to generate a unique color for start/end
        if self.map['type'] == 'vanilla':
            start_image = TerrainSprites.grass
            end_image = TerrainSprites.grass
        else:
            start_image = TerrainSprites.snow
            end_image = TerrainSprites.snow

        # starting station
        rect_x = self.board_rect.left + OUTER_GAP + start[0] * (TRACK_WIDTH + INNER_GAP)
        rect_y = self.board_rect.top + OUTER_GAP + start[1] * (TRACK_HEIGHT + INNER_GAP)
        station_rect = pygame.Rect(rect_x, rect_y, TRACK_WIDTH, TRACK_HEIGHT)
        self.start_station = Station(
            image = start_image, 
            rect = station_rect, 
            orientation = self.train_orient(start)
        )
        self.board_tiles[start[1]][start[0]].attached = self.start_station
        
        
        # add clock                                                                         # Modified by Kelvin Huang, May 13, 2024
        radius = 25                                                                         # add timer before train spawns
        duration = 3
        self.clock = Timer(rect_x + radius, rect_y + radius, radius, duration)

        # ending station
        rect_x = self.board_rect.left + OUTER_GAP + end[0] * (TRACK_WIDTH + INNER_GAP)
        rect_y = self.board_rect.top + OUTER_GAP + end[1] * (TRACK_HEIGHT + INNER_GAP)
        station_rect = pygame.Rect(rect_x, rect_y, TRACK_WIDTH, TRACK_HEIGHT)
        self.end_station = Station(
            image = end_image, 
            rect = station_rect, 
            orientation = self.train_orient(end)
        )
        self.board_tiles[end[1]][end[0]].attached = self.end_station
        
        # Save stations and locations
        self.start, self.end = start, end
        col, row = start
        self.start_station_tile = self.board_tiles[row][col]
        col, row = end
        self.end_station_tile = self.board_tiles[row][col]

        self.add_tile_under([start[0], start[1]])
        #self.add_tile_under(self.end_station_tile)
    
    # Determine starting train orientation 
    def train_orient(self, location):
        x, y = location
        orient = [0, 90, 180, 270]
        if x == 0 or self.check_water(x - 1, y):
            orient.remove(180)
        if x == self.grid_cols - 1 or self.check_water(x + 1, y):
            orient.remove(0)

        if y == 0 or self.check_water(x, y - 1):
            orient.remove(90)
        if y == self.grid_rows - 1 or self.check_water(x, y + 1):
            orient.remove(270)

        return random.choice(orient)
    
    def check_water(self, x, y):
        if x == -1 or x == self.grid_cols or y == -1 or y == self.grid_rows:
            return True
        return self.board_tiles[y][x].terrain == 'water'
    
    # generate station track based on train initial angle and location of starting station
    def create_station_track(self):
        deg = self.start_station.orientation
        self.start_x = int(round(self.start[0] + math.cos(math.radians(deg)), 1))
        self.start_y = int(round(self.start[1] - math.sin(math.radians(deg)), 1))

        x = self.start_x
        y = self.start_y
        possible_tracks = [track_set_types.vertical, track_set_types.horizontal, track_set_types.left, track_set_types.right, track_set_types.ileft, track_set_types.iright]
        if x == 0 or x == self.grid_rows - 1 or deg == 90 or deg == 270 or (deg == 0 and self.check_water(x + 1, y)) or (deg == 180 and self.check_water(x - 1, y)):
            possible_tracks.remove(track_set_types.horizontal)
        if y == 0 or y == self.grid_rows - 1 or deg == 0 or deg == 180 or (deg == 90 and self.check_water(x, y - 1)) or (deg == 270 and self.check_water(x, y + 1)):
            possible_tracks.remove(track_set_types.vertical)

        if x == 0 or y == self.grid_rows - 1 or deg == 180 or deg == 270 or (deg == 90 and self.check_water(x - 1, y)) or (deg == 0 and self.check_water(x, y + 1)):
            possible_tracks.remove(track_set_types.left)
        if x == 0 or y == 0 or deg == 90 or deg == 180 or (deg == 0 and self.check_water(x, y - 1)) or (deg == 270 and self.check_water(x - 1, y)):
            possible_tracks.remove(track_set_types.ileft)

        if x == self.grid_cols - 1 or y == self.grid_rows - 1 or deg == 0 or deg == 270 or (deg == 90 and self.check_water(x + 1, y)) or (deg == 180 and self.check_water(x, y + 1)):
            possible_tracks.remove(track_set_types.right)
        if x == self.grid_cols - 1 or y == 0 or deg == 0 or deg == 90 or (deg == 270 and self.check_water(x + 1, y)) or (deg == 180 and self.check_water(x, y - 1)):
            possible_tracks.remove(track_set_types.iright)
        
        track_rect = pygame.Rect(self.board_tiles[y][x].rect.left, self.board_tiles[y][x].rect.top, TRACK_WIDTH, TRACK_HEIGHT)
        track = Track(track_rect, random.choice(possible_tracks))
        self.board_tiles[y][x].attached = track
    
    def create_train(self):
        starting_orient = self.start_station.orientation

        # build the head for the train
        self.train.append(
            Train(
                type = self.train_type, 
                board_rect = self.board_rect,
                degree = starting_orient, 
                start = self.start
            )
        )

        # multiple cart
        self.max_carts = 5
        self.total_cart = self.max_carts
        self.time = (pygame.Surface.get_width(self.train[0].surface) + 5) / self.train[0].speed
        self.timer = self.time
        #print("time =", self.time)

    def toggle_speed_multiplier(self, type, active):
        #print(self.speed_multipliers['fast_forward']['active'])

        # Modified by Kelvin Huang on 4/16/2024
        if self.spawn_trains == False: return
        cart = self.train[0]
        new_speed = cart.speed

        multiplier = self.speed_multipliers[type]['multiplier']
        already_active = self.speed_multipliers[type]['active']
        
        if active == already_active: 
            return
        if active: # activate
            # adjust the timer and time it takes for a new cart to spawn according to change in speed
            new_speed = cart.speed * multiplier
            
        else: # deactivate
            # adjust the timer and time it takes for a new cart to spawn according to change in speed 
            new_speed = cart.speed / multiplier

        self.speed_multipliers[type]['active'] = active

        self.timer *= (cart.speed/new_speed)
        self.time *= (cart.speed/new_speed)

        for train_instance in self.train:
            train_instance.speed = new_speed

    # Update
    def update(self):
        if self.clock != None:                          # Modified by Kelvin Huang, May 13, 2024
            if self.clock.tick():                       # Controls when to start spawning trains
                self.clock = None
                self.start_spawning_train = True

        if (self.prev_highlight != '' and 'hover' not in self.prev_highlight) or \
            (self.highlight != '' and 'hover' not in self.highlight): self.powerup_time += 1
        
        dfreeze = self.speed_multipliers['deep-freeze']
        if dfreeze['active'] and self.powerup_time >= dfreeze['time-limit']:
            print(self.powerup_time, ': disabled deep freeze')
            self.toggle_speed_multiplier('deep-freeze', False)
            self.powerup_time = 0

        freeze = self.speed_multipliers['freeze']
        if freeze['active'] and self.powerup_time >= freeze['time-limit']:
            print(self.powerup_time, ': disabled freeze')
            self.toggle_speed_multiplier('freeze', False)
            self.powerup_time = 0
        
        if not freeze['active'] and not dfreeze['active']: 
            if 'hover' in self.highlight:
                self.prev_highlight = ''
            else:
                self.highlight = ''
                self.prev_highlight = ''

        starting_orient = self.start_station.orientation
        #if self.current_tile and self.train:

        if self.start_spawning_train == True:   # Modified by Kelvin Huang, May 13, 2024
            self.create_train()                 # Starting spawning the train
            self.start_spawning_train = False   # close it off so it doesn't spawn another train
            self.spawn_trains = True

        if self.spawn_trains == True:           # start spawning carts of train
            for cart in self.train:
                self.check(cart)
                cart.update()
            
            if self.total_cart > 1:
                self.timer -= 1
                if self.timer <= 0:
                    self.total_cart -= 1
                    self.timer = self.time
                    self.train.append(
                        Train(
                            type = self.train_type, 
                            board_rect = self.board_rect,
                            degree = starting_orient, 
                            start = self.start,
                            speed = self.train[0].speed
                        )
                    )

    # Continusly called: checks what to do based on new tiles
    def check(self, cart):
        # declare some helpful variables
        train_width = pygame.Surface.get_width(cart.surface)
        train_height = pygame.Surface.get_height(cart.surface)
        x_no_margin = cart.x - self.board_rect.left - OUTER_GAP
        y_no_margin = cart.y - self.board_rect.top - OUTER_GAP

        x_correction = (train_width/2) * math.cos(math.radians(cart.degree))
        y_correction = (train_width/2) * math.sin(math.radians(cart.degree))        

        # find tile indexes corresponding to train
        front_x = int((x_no_margin + x_correction - INNER_GAP * ((x_no_margin + x_correction) // (TRACK_HEIGHT + INNER_GAP))) // TRACK_HEIGHT)
        front_y = int((y_no_margin - y_correction - INNER_GAP * ((y_no_margin - y_correction) // (TRACK_WIDTH + INNER_GAP))) // TRACK_WIDTH)

        back_x = int((x_no_margin - x_correction - INNER_GAP * ((x_no_margin - x_correction) // (TRACK_HEIGHT + INNER_GAP))) // TRACK_HEIGHT)
        back_y = int((y_no_margin + y_correction - INNER_GAP * ((y_no_margin +  y_correction) // (TRACK_WIDTH + INNER_GAP))) // TRACK_WIDTH)
        
        center_x = int((x_no_margin - INNER_GAP * (x_no_margin // (TRACK_HEIGHT + INNER_GAP))) // TRACK_HEIGHT)
        center_y = int((y_no_margin - INNER_GAP * (y_no_margin // (TRACK_WIDTH + INNER_GAP))) // TRACK_WIDTH)

        # Only cares to end game if train reaches end station
        def find_if_under_station():
            # Modified by Kelvin Huang, May 1, 2024
            # Deleted check if same tile and index validation from the checking direction function and moving it up here
            if (center_x, center_y) == cart.current_tile: 
                return 'same tile'
            
            valid_index = (0 <= center_y <= self.grid_rows - 1) and (0 <= center_x <= self.grid_cols - 1)
            if not valid_index:
                return False
            
            tile = self.board_tiles[center_y][center_x]
            train_under_tile = tile.rect.collidepoint(cart.x, cart.y)
            if not train_under_tile: return "continue"

            # Modified by Kelvin Huang, May 1, 2024
            # start clipping the cart so the cart doesn't peak out the edge of the station
            if (center_x, center_y) == self.end and cart.clipped == False:
                cart.clip()
                
            # the whole cart enter the station
            attached_item = self.board_tiles[back_y][back_x].attached
            if attached_item != self.end_station: return 'not on end station'

            #correct_direction = round(math.sin(math.radians(cart.degree + 180)), 5) == round(math.sin(math.radians(attached_item.orientation)), 5)
            #if not correct_direction: return

            if len(self.train) == 1:
                return True
            else: 
                self.train.remove(cart)
                SFX.scomplete.play()

        # Modified by Kelvin Huang, April 28, 2024
        # deleting path condition
        still_fine = find_if_under_station()
        if still_fine == 'same tile' or still_fine == 'continue':
            return
        elif still_fine == "not on end station":
            pass
        elif still_fine == True:
            self.delete(True)
            return
        elif still_fine == False:
            self.delete(False)
            return

        # Checks next tile for direction
        # Also finds end conditions: True is a failure to find a direction that should not end the path
        def find_new_direction():
            tile = self.board_tiles[center_y][center_x]
            attached_item = tile.attached

            if tile.terrain == 'ice':
                self.toggle_speed_multiplier('ice', True)
            else: self.toggle_speed_multiplier('ice', False)

            if tile.slowed:
                self.toggle_speed_multiplier('slow', True)
            else: self.toggle_speed_multiplier('slow', False)

            if attached_item == None: return (False, 'not a track or station')
            if attached_item == self.end_station: return (True, 'ending station')
            if isinstance(attached_item, Obstacle): return (False, 'train crash into obstacle')
            if tile.terrain == 'water': return (False, 'train over water')
            
            if cart.direction == "forward" and not isinstance(attached_item, Station):
                new_direction = attached_item.directions[int(cart.degree % 360 / 90)]             
            else: return (True, 'turning')
            if new_direction == 'crash': return (False, 'direction found was not correct for train')

            cart.direction = new_direction

            # Modified by Kelvin Huang, April 29, 2024
            # Adjust code to work with multiple cart

            # will only start deleting the references when the last cart leave the previous tile
            if self.total_cart == 1 and cart == self.train[len(self.train) - 1]:
                x, y = cart.current_tile
                self.remove_tile_under([x, y])

            cart.current_tile = (center_x, center_y)
            # only add tile to reference list when the front of the train move to a new tile
            if cart == self.train[0]:
                self.add_tile_under([center_x, center_y])
            
            return (True, 'found new track direction')
        
        still_fine, condition = find_new_direction()

        if not still_fine:
            self.delete(False)
    
    def delete(self, condition):
        self.end_call(self, condition)

    # Deletion of path doesnt leave behind objects
    def __del__(self): # Modified by Kelvin Huang, April 28, 2024 got __del__ function to work and replace the previous delete function with __del__
        # delete stations
        if self.start:
            col, row = self.start
            self.board_tiles[row][col].attached = None
            self.board_tiles[row][col].under_path = None
        if self.end:
            col, row = self.end
            self.board_tiles[row][col].attached = None
            self.board_tiles[row][col].under_path = None

        self.board_tiles[self.start_y][self.start_x].attached = None

        print("delete")
        # delete train
        del self.train

    # Rendering
    def draw(self, game_surf):
        for cart in self.train:
            cart.draw(game_surf)
        
    # Modified by Matthew Selvaggi
    # Added additional changes to draw a rect around to
    # allow user to understand endpoint for respective train
        self.start_station_tile.draw_attached(game_surf)
        self.end_station_tile.draw_attached(game_surf)

        start_rect = self.start_station_tile.rect
        end_rect = self.end_station_tile.rect

        pygame.draw.rect(game_surf, self.color, start_rect, 3)
        pygame.draw.rect(game_surf, self.color, end_rect, 3)

        if self.clock != None:
            self.clock.draw(game_surf)