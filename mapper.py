import json

weapon_type_one = "sns"
weapon_type_two = "db"


def recursion(item, pos, grid_num):
  global lowest_empty_row
  global grids

  i = 0
  #print(item["name"], pos)

  # if starting a new weapon tree, move lowest row position down 1
  if pos[0] == 0:
    lowest_empty_row += 1

  # if starting a new weapon tree from an alternate weapon type, move over 1
  if pos[0] == 0 and item["upgrade-from"] != "N/A":
    if type(item["upgrade-from"]) is list:
      if find_weapon_in_list(item["upgrade-from"][0])["type"] != item["type"]:
        prev_weapon = find_weapon_in_list(item["upgrade-from"][0])
      elif find_weapon_in_list(item["upgrade-from"][1])["type"] != item["type"]:
        prev_weapon = find_weapon_in_list(item["upgrade-from"][1])
    else:
      prev_weapon = find_weapon_in_list(item["upgrade-from"])

    if prev_weapon["type"] != item["type"]:
      print('alt-start success')
      grids[grid_num][pos[1]][pos[0]] = prev_weapon["name"] + f' ({prev_weapon["type"]})'
      pos[0] += 1

    
  # end of branch condition
  if item["upgrade-to"] == "N/A":
    #print("No upgrades")
    grids[grid_num][pos[1]][pos[0]] = item["name"]
    return True

  # main loop, iterate over available upgrades
  for weapon in item["upgrade-to"]:
    next_weapon = find_weapon_in_list(weapon)

    # assign the next cell, dropping a row if needed
    if i == 0:
      next_cell = [pos[0]+1, pos[1]]
    else:
      grids[grid_num][lowest_empty_row][pos[0]] = "+"
      next_cell = [pos[0]+1, lowest_empty_row]
      lowest_empty_row += 1
  
    # upgrade is not the current weapon type
    if next_weapon["type"] != item["type"]:
      grids[grid_num][next_cell[1]][next_cell[0]] = weapon + f' ({next_weapon["type"]})'

    else:
      recursion(next_weapon, next_cell, grid_num)

    #print(i)
    i += 1
  
  # finally, add weapon to grid
  grids[grid_num][pos[1]][pos[0]] = item["name"]

def find_weapon_in_list(name):
  for weapon in total_list:
    if weapon["name"] == name:
      return weapon
    else:
      continue
  return "error"

def find_branches(weapon_list):
  starting_weapons = []
  from_alt_weapons = []
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
    elif type(weapon["upgrade-from"]) is list: 
      if weapon_type_map[weapon["upgrade-from"][0]] != weapon["type"]:
        from_alt_weapons.append(weapon)
      if weapon_type_map[weapon["upgrade-from"][1]] != weapon["type"]:
        from_alt_weapons.append(weapon)
    elif weapon_type_map[weapon["upgrade-from"]] != weapon["type"]:
      from_alt_weapons.append(weapon)
  return [starting_weapons, from_alt_weapons, unique_weapons, g_weapons]

# import the json file
try:
  rhandle      = open(f'{weapon_type_one}-{weapon_type_two}-data.json', 'r')
except:
  rhandle      = open(f'{weapon_type_two}-{weapon_type_one}-data.json', 'r')
weapon_lists = json.load(rhandle)
rhandle.close()

# initialize globals
lowest_empty_row  = 0
weapon_type_map   = {}
total_list = weapon_lists[0].copy()
total_list.extend(weapon_lists[1])

# create quick reference for each weapon's type
for weapon in total_list:
  weapon_type_map[ weapon["name"] ] = weapon["type"]

grids = [ [],[] ]
for x in range(100):
  grids[0].append(['', '', '', '', '', '', '', '', '', '', '', ''])
for x in range(100):
  grids[1].append(['', '', '', '', '', '', '', '', '', '', '', ''])

result_one = find_branches(weapon_lists[0])
result_two = find_branches(weapon_lists[1])


for starter in result_one[0]:
  recursion(starter, [0,lowest_empty_row], 0)

for alt_start in result_one[1]:
  recursion(alt_start, [0,lowest_empty_row], 0)

lowest_empty_row = 0

for starter in result_two[0]:
  recursion(starter, [0,lowest_empty_row], 1)
for alt_start in result_two[1]:
  recursion(alt_start, [0,lowest_empty_row], 1)


# clip the grids
while grids[0][len(grids[0])-1] == ['', '', '', '', '', '', '', '', '', '', '', '']:
  grids[0].pop()
print(len(grids[0]), "is the new grid 0 length")

while grids[1][len(grids[1])-1] == ['', '', '', '', '', '', '', '', '', '', '', '']:
  grids[1].pop()
print(len(grids[1]), "is the new grid 1 length")

with open(f'{weapon_type_one}-data.js', 'w') as file1:
  file1.write(f'const {weapon_type_one}Data = {json.dumps(weapon_lists[0])}\nexport default {weapon_type_one}Data')

with open(f'{weapon_type_two}-data.js', 'w') as file2:
  file2.write(f'const {weapon_type_two}Data = {json.dumps(weapon_lists[1])}\nexport default {weapon_type_two}Data')

with open(f'{weapon_type_one}-map.js', 'w') as file3:
  file3.write(f'const {weapon_type_one}Map = {json.dumps(grids[0])}\nexport default {weapon_type_one}Map')

with open(f'{weapon_type_two}-map.js', 'w') as file4:
  file4.write(f'const {weapon_type_two}Map = {json.dumps(grids[1])}\nexport default {weapon_type_two}Map')
