import json

def recursion(item, pos):
  global lowest_empty_row
  global grid

  i = 0
  #print(item["name"], pos)

  # if starting a new weapon tree, move lowest row position down 1
  if pos[0] == 0:
    lowest_empty_row += 1
    
  # end of branch condition
  if item["upgrade-to"] == "N/A":
    #print("No upgrades")
    grid[pos[1]][pos[0]] = "X"#item["name"]
    return True

  # main loop, iterate over available upgrades
  for weapon in item["upgrade-to"]:
    next_weapon = find_weapon_in_list(weapon)

    # assign the next cell, dropping a row if needed
    if i == 0:
      next_cell = [pos[0]+1, pos[1]]
    else:
      grid[lowest_empty_row][pos[0]] = "+"
      next_cell = [pos[0]+1, lowest_empty_row]
      lowest_empty_row += 1

    # upgrade is not a sword and shield
    if next_weapon == "ds":
      #print(weapon, "is not s'n's")
      grid[next_cell[1]][next_cell[0]] = "O"#item["name"]+" (Dual Sword)

    else:
      recursion(next_weapon, next_cell)

    #print(i)
    i += 1
  
  # finally, add weapon to grid
  grid[pos[1]][pos[0]] = "X"#item["name"]

def find_weapon_in_list(name):
  for weapon in weapon_list:
    if weapon["name"] == name:
      return weapon
    else:
      continue
  return "ds"

def find_branches():
  starting_weapons = []
  unique_weapons = []
  g_weapons = []
  for weapon in weapon_list:
    if weapon["upgrade-from"] == "N/A" and weapon["upgrade-to"] == "N/A":
      if weapon["name"].endswith("G"):
        g_weapons.append(weapon["name"])
      else:
        unique_weapons.append(weapon["name"])
    elif weapon["upgrade-from"] == "N/A":
      starting_weapons.append(weapon)
  return [starting_weapons, unique_weapons, g_weapons]

# import the json file
rhandle     = open('mhfu-weapon-trees\\sns-data.txt', 'r')
weapon_list = json.load(rhandle)
rhandle.close()

# handler for eventual grid dump
whandle = open('sns-map.txt', 'w')

# initialize globals
start_item        = weapon_list[69]
lowest_empty_row  = 0

grid = []
for x in range(49):
  grid.append(['', '', '', '', '', '', '', '', '', '', '', ''])

result = find_branches()

for starter in result[0]:
  print(starter["name"])
  recursion(starter, [0,lowest_empty_row])

print(grid)
whandle.close()
