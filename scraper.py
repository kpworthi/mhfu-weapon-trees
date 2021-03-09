import logging
import json
import re
import math
import sys
import getopt
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from bs4 import SoupStrainer

#
#'https://monsterhunter.fandom.com/wiki/MHF2_and_MHFU:_Light_Bowgun_List'
#'https://monsterhunter.fandom.com/wiki/wiki/MHF2_and_MHFU:_Heavy_Bowgun_List'

logging.basicConfig(
    filename=f'scrape-log.txt',
    filemode='w',
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

class Crawler:
    def __init__(self):
      self.visited_urls    = []
      self.weapon_list_one = []
      self.weapon_list_two = []
      self.all_names       = []
      self.urls_to_visit   = []
      self.verbose         = False

    def url_crawl(self, url, weapon_one, weapon_two):
      html = requests.get(url).text
      for url in self.init_weapon_info(url, html, weapon_one, weapon_two):
          self.urls_to_visit.append(url)

    def init_weapon_info(self, url, html, weapon_one, weapon_two):
      soup = BeautifulSoup(html, 'html.parser')
      rows = []
      tables = soup.find_all(class_="treetable")
      if len(tables) == 0:
        tables = soup.find_all('table', attrs={"align": "left"})

      for table in tables:
        cols = { "name": 0, "attack": 1, "attribute": 2, "sharpness": None, "affinity": 4, "slots": 5, "bonus": 6, "rarity": 7, "notes": None, "shelling": None }
        headers_checked = False;
        rows = table.find_all('tr')
        for row in rows:
          if len(row.find_all('td')) == 1: # skip title rows or info rows
            continue
          elif row.find('a') == None and row('td')[0].get_text(strip=True) == "Weapon Name" and not headers_checked: # grab header info
            col_num = 0
            for header in row('td'):
              if header.get_text(strip=True).lower() in cols:
                cols[header.get_text(strip=True).lower()] = col_num
              col_num += 1
            headers_checked = True
            if self.verbose == True: print(cols)
            continue
          elif row('td')[1].get_text(strip=True) == "": # ignore info rows
            if self.verbose == True: print('ignoring blank')
            continue
          elif row('a')[1].get_text(strip=True).startswith('Dummy'): # ignore 'Dummy' entries
            continue
          elif row.find_all('td')[0].find_all('a')[1].get_text(strip=True) in self.all_names: # skip duplicates
            if self.verbose == True: print("duplicate detected", row.find_all('td')[0].find_all('a')[1].get_text(strip=True))
            continue
          
          cells = row.find_all('td')
          current_weapon = {
            "name": cells[cols["name"]].find_all('a')[1].get_text(strip=True),
            "attack": cells[cols["attack"]].get_text(strip=True),
            "element": cells[cols["attribute"]].get_text(strip=True),
            "affinity": cells[cols["affinity"]].get_text(strip=True),
            "slots": cells[cols["slots"]].get_text(strip=True),
            "bonus": cells[cols["bonus"]].get_text(strip=True),
            "rarity": cells[cols["rarity"]].get_text(strip=True),
          }
          for prop in current_weapon: # Fill blanks
            if current_weapon[prop] == "": current_weapon[prop] = 'N/A'

          if cells[cols["attribute"]].find('img'): # If an image was used for an element rather than words
            current_weapon["element"] = cells[cols["attribute"]].img["alt"].split('.')[0]+" "+current_weapon["element"]

          if cols["sharpness"]: # adding sharpness for blademaster weapons
            current_weapon["sharpness"] = self.parse_sharpness(cells[cols["sharpness"]].find_all("img"))

          if cols["notes"]: # adding notes for hunting horns
            current_weapon["notes"] = self.parse_sharpness(cells[cols["notes"]].find_all("img"))

          if cols["shelling"]: # adding shelling for gunlances
            current_weapon["shelling"] = cells[cols["shelling"]].get_text(strip=True)
            if self.verbose == True: print(cells[cols["shelling"]].get_text(strip=True))

          weapon_link = cells[0].find_all('a')[1].get('href') # Grab link to use for getting materials
          if weapon_link and weapon_link.startswith('/'):
            weapon_link = urljoin(url, weapon_link)
          current_weapon["link"] = weapon_link

          # match the weapon to the appropriate table and add the type to the object
          if cells[0].find_all('a')[0].img['alt'] == f'{weapon_one}-Icon.png':
            current_weapon["type"] = weapon_one.lower()
            self.weapon_list_one.append(current_weapon)
          elif cells[0].find_all('a')[0].img['alt'] == f'{weapon_two}-Icon.png':
            current_weapon["type"] = weapon_two.lower()
            self.weapon_list_two.append(current_weapon)
          elif weapon_one == 'bow':
            current_weapon["type"] = weapon_one.lower()
            self.weapon_list_one.append(current_weapon)
          else: print("Weapon match failed!", current_weapon["name"])

          self.all_names.append(current_weapon["name"])
          
          if current_weapon["type"] == "ds": current_weapon["type"] = "db" # once again fix db / ds issue
          elif current_weapon["type"] == "hammer": current_weapon["type"] = "hm" # site does not abbreviate hammer
          elif current_weapon["type"] == "lance": current_weapon["type"] = "la" # site does not abbreviate lance
          if 'Shiny Rathalos Sword' in current_weapon["name"]: # broken links
            current_weapon["link"] = "https://monsterhunter.fandom.com/wiki/Shiny_Rathalos_Sword_(MHFU)"
          elif 'Striped Dragonga' in current_weapon["name"]:
            current_weapon["link"] = "https://monsterhunter.fandom.com/wiki/Striped_Dragonga_(MHFU)"

          yield weapon_link

    def get_addl_info(self, url, current_weapon, weapon_type):
      soup = BeautifulSoup(requests.get(url).text, 'html.parser')

      failure = False
      # Format 1
      try:
        if not current_weapon["type"] == 'bow':
          a_list    = soup.find_all('a', string=re.compile('MHFU: '))    # couple extra hoops to jump through
          table_two = a_list[len(a_list)-1].parent.parent.parent.parent  # to make sure we get the right tables.
        else:
          a_list    = soup.find_all('a', string=re.compile('Bow Weapon Tree'))    # bow pages are particularly unique
          table_two = a_list[len(a_list)-1].parent.parent.parent.parent.parent.parent
        main_table_list = soup.find_all('b', string="Description")
        table_one = main_table_list[len(main_table_list)-1].parent.parent.parent.parent.parent
        table_one_rows = table_one.find_all("tr")
        table_two_rows = table_two.find_all("tr")

        current_weapon["create-cost"]  = table_one_rows[2].find_all("td")[2].get_text(strip=True)
        current_weapon["upgrade-cost"] = table_one_rows[2].find_all("td")[3].get_text(strip=True)
        upgrade_links = table_two_rows[2].find_all("td")[0].find_all('a')
        if len(upgrade_links) > 1:
          current_weapon["upgrade-from"] = []
          for link in upgrade_links:
            if not link.has_attr('class') or link['class'] != ['image']: # make sure not to add image links to the array, resulting in empty entries
              current_weapon["upgrade-from"].append( link.get_text(strip=True) )
          if self.verbose == True: print('\ndouble origin', current_weapon["upgrade-from"])
        else:
          current_weapon["upgrade-from"] = table_two_rows[2].find_all("td")[0].get_text(strip=True)

        current_weapon["create-mats"]  = []
        current_weapon["upgrade-mats"] = []
        current_weapon["upgrade-to"]   = []

        # mats and upgrade list loop
        for cat in [[table_one_rows, 4, 2, "create-mats"],[table_one_rows, 4, 3, "upgrade-mats"],[table_two_rows, 2, 1 , "upgrade-to"]]:
          current_area = cat[0][ cat[1] ].find_all("td")[ cat[2] ]
          current_text = current_area.get_text(strip=True)

          if current_text == 'N/A' or current_text == 'None' or current_text == 'End of Tree':
            current_weapon[ cat[3] ] = 'N/A'

          else:
            if cat[3].endswith('mats'): # loop for grabbing items
              material_string = current_area.get_text().replace('  ', ' ')
              for item in re.findall("[A-Za-z\s\-\+\']+\s{0,2}\(\d+\)", material_string): # (#) qty format
                current_weapon[ cat[3] ].append(item.strip())
              if len(current_weapon[ cat[3] ]) == 0:
                for item in re.findall("[A-Za-z\s\-\+\']+\d{1,2}", material_string): # x# qty format
                  current_weapon[ cat[3] ].append(item.strip())

            else: # otherwise do the weapon's next upgrades by finding 'a' elements
              for weapon in current_area.find_all('a'):
                if not weapon.has_attr('class') or weapon['class'] != ['image']: # make sure not to add image links to the array, resulting in empty entries
                  current_weapon["upgrade-to"].append( weapon.get_text(strip=True) )
      except:
        logging.exception(f'Format 1 failed on: {url}')
        failure = True

      # Format 2
      if failure:
        try:
          current_weapon["create-cost"]  = soup.find_all(attrs={"data-source": "Creation Cost"})[1].get_text(strip=True)
          current_weapon["upgrade-cost"] = soup.find_all(attrs={"data-source": "Upgrade Cost"})[1].get_text(strip=True)
          if len(soup.find_all(attrs={"data-source": "Upgraded From"})[1].find_all('a')) > 2:
            current_weapon["upgrade-from"] = [
              soup.find_all(attrs={"data-source": "Upgraded From"})[1][1].get_text(strip=True),
              soup.find_all(attrs={"data-source": "Upgraded From"})[1][4].get_text(strip=True),
            ]
          else:
            current_weapon["upgrade-from"] = soup.find_all(attrs={"data-source": "Upgraded From"})[1].get_text(strip=True)
          current_weapon["create-mats"]  = []
          current_weapon["upgrade-mats"] = []
          current_weapon["upgrade-to"]   = []

          # "upgrade-mats" and "create-mats" loops
          for cat in [["Creation Materials", "create-mats"],["Upgrade Materials", "upgrade-mats"]]:
            current_area = soup.find_all(attrs={ "data-source": cat[0] })[1]
            if current_area.get_text(strip=True) == 'N/A':
              current_weapon[ cat[1] ] = 'N/A'
            else:
              material_string = current_area.get_text().replace('  ', ' ')
              for item in re.findall("[A-Za-z\s\-\+\']+\d{1,2}", material_string):
                current_weapon[ cat[1] ].append(item.strip())

          # "upgrade-to" loop
          current_area = soup.find_all(attrs={"data-source": "Upgrades Into"})[1].get_text(strip=True)
          if soup.find_all(attrs={"data-source": "Upgrades Into"})[1].get_text(strip=True) == 'N/A':
            current_weapon["upgrade-to"] = 'N/A'
          else:
            image_offset = 1
            for weapon in soup.find_all(attrs={"data-source": "Upgrades Into"})[1].find_all('a'):
              if image_offset%2 == 0:
                current_weapon["upgrade-to"].append( weapon.get_text(strip=True) )
              image_offset += 1
        except:
          logging.exception(f'Format 2 failed on: {url}')
          print("\nFormat 2 failed on", current_weapon["link"])
          failure = True

      # "None" and "-" fixer for consistency
      for key in current_weapon:
        if "???" in current_weapon[key] or "None" in current_weapon[key] or current_weapon[key] == "-":
          current_weapon[key] = "N/A"

      # sometimes items are listed as 'upgrade only' by site when they are instead 'create only', swap if true
      if current_weapon["upgrade-from"] == "N/A" and [current_weapon["upgrade-cost"], current_weapon["upgrade-mats"]] != ["N/A","N/A"]:
        current_weapon["create-cost"] = current_weapon["upgrade-cost"]
        current_weapon["create-mats"] = current_weapon["upgrade-mats"].copy()
        current_weapon["upgrade-cost"] = "N/A"
        current_weapon["upgrade-mats"] = "N/A"

      # if it's a dual blade double element, put spaces around the slash
      if "/" in current_weapon["element"] and current_weapon["element"] != "N/A": 
        current_weapon["element"] = " / ".join(current_weapon["element"].split("/"))

      if "Millenium Knife" in current_weapon["name"]:
        current_weapon["name"] = "Millennium Knife" # Typo correction

      # remove link from final data, not needed anymore
      del current_weapon["link"]

      return current_weapon

    def parse_sharpness(self, image_list):
      sharpness_string = ""
      for image in image_list:
          sharpness_string = sharpness_string + image['alt'][0:-4]
      if sharpness_string == "": sharpness_string = "Unknown" # site does not have data on sharpness, try to find manually
      return sharpness_string

    def init_switch(self, param):
      if param in ['sns', 'db']:
        return ['SnS', 'DS', 'https://monsterhunter.fandom.com/wiki/MHFU:_Sword_and_Shield_and_Dual_Blades_Weapon_Tree']
      elif param in ['gs', 'ls']:
        return ['GS', 'LS', 'https://monsterhunter.fandom.com/wiki/MHFU:_Great_Sword_and_Long_Sword_Tree']
      elif param in ['hm', 'hh']:
        return ['Hammer', 'HH', 'https://monsterhunter.fandom.com/wiki/MHF2_and_MHFU:_Hammer_and_Hunting_Horn_Tree']
      elif param in ['gl', 'la']:
        return ['GL', 'Lance', 'https://monsterhunter.fandom.com/wiki/MHF2_and_MHFU:_Lance_and_Gunlance_Tree']
      elif param == 'bow':
        return ['bow', 'none', 'https://monsterhunter.fandom.com/wiki/Bow_Weapon_Tree']

    def run(self, argv):
      weapon_one = ''
      weapon_two = ''

      # Handle options
      try:
        opts, args = getopt.getopt(argv,"hva:b:",["type1=","type2="])
      except getopt.GetoptError:
        print('scraper.py --type1 <type> --type2 <type>')
        sys.exit(2)
      for opt, arg in opts:
        if opt == '-h':
            print('scraper.py -a <type> -b <type>')
            print('scraper.py --type1 <type> --type2 <type>')
            print(
'''
Use -v for all messages

Use lower case only for types
Types are:
sns : Sword and Shield
db  : Dual Blades
gs  : Great Sword
ls  : Long Sword
hm  : Hammer
hh  : Hunting Horn
gl  : Gunlance
la  : Lance
'''
            )
            sys.exit()
        elif opt == '-v':
          self.verbose = True
        elif opt in ("-a", "--type1", "-b", "--type2"):
          if weapon_one == '':
            weapon_one = arg
          elif weapon_two == '':
            weapon_two == arg

      if weapon_one == '':
        print('Please enter weapon types: ')
        print('scraper.py --type1 <type> --type2 <type>')
        print('For more information, use -h')
        sys.exit(2)

      # assign correct names based on shorthand
      scraping_params = self.init_switch(weapon_one)
      weapon_one      = scraping_params[0]
      weapon_two      = scraping_params[1]
      url             = scraping_params[2]

      # Build initial list
      logging.info(f'Crawling: {url}')
      
      self.url_crawl(url, weapon_one, weapon_two)
      self.visited_urls.append(url)
      print(f'{len(self.urls_to_visit)} urls to visit') # Print number of pages
      total_urls = len(self.urls_to_visit)


      # Get upgrade/create info, and any weapon-type-unique info
      index = 0
      weapon_count = 1
      five_percent = math.floor(total_urls / 20)
      for weapon_list in [self.weapon_list_one, self.weapon_list_two]:
        weapon_type = ""
        if index == 0: weapon_type = weapon_one.lower()
        else: weapon_type = weapon_two.lower()
        for weapon in weapon_list:
          url = weapon["link"]
          #logging.info(f'Reading: {url}') # verbosity, print current page
          try:
              weapon = self.get_addl_info(url, weapon, weapon_type)
          except Exception:
              logging.exception(f'Failed to crawl: {url}')
          finally:
              if weapon_count % five_percent == 0:
                left = 20 * math.floor(5 * weapon_count / five_percent) // 100
                right = 20 - left
                print('\r[', '#' * left, ' ' * right, ']',
                      f' {math.floor(5 * weapon_count / five_percent)}%  #{weapon_count}',
                      sep='', end='', flush=True)
              weapon_count += 1
        index += 1

      total_weapons = [self.weapon_list_one, self.weapon_list_two]

      #dump to file
      #change ds back to db for consistency
      if weapon_one == "DS": weapon_one = "DB"
      elif weapon_two == "DS": weapon_two = "DB"
      elif weapon_one == "Hammer": weapon_one = "HM"
      elif weapon_two == "Hammer": weapon_two = "HM"
      elif weapon_one == "Lance": weapon_one = "LA"
      elif weapon_two == "Lance": weapon_two = "LA"
      fhandle = open(f'{weapon_one.lower()}-{weapon_two.lower()}-data.json', 'w')
      fhandle.write(json.dumps(total_weapons))
      fhandle.close()

if __name__ == '__main__':
    Crawler().run(sys.argv[1:])
