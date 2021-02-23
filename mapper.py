import json

def recursion(item, pos):
  global lowest_empty_row
  global grid

  i = 0
  print(item["name"], pos)

  # end of branch condition
  if item["upgrade-to"] == "N/A":
    print("No upgrades")
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
      print(weapon, "is not s'n's")
      grid[next_cell[1]][next_cell[0]] = "O"#item["name"]+" (Dual Sword)

    else:
      recursion(next_weapon, next_cell)

    print(i)
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

rhandle     = open('mhfu data\\sns-data.txt', 'r')
weapon_list = json.load(rhandle)
rhandle.close()

whandle = open('sns-map.txt', 'w')

start_item        = weapon_list[69]
current_pos       = [0,0]
lowest_empty_row  = 1

grid = [
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', ''],
  ['', '', '', '', '', '', '', '', '', '', '', '']
]

recursion(start_item, current_pos)
print(grid)

whandle.close()
