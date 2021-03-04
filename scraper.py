import logging
import json
import re
import math
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from bs4 import SoupStrainer

weapon_one = 'SnS'
weapon_two = 'DB'
tree_link = 'https://monsterhunter.fandom.com/wiki/MHFU:_Sword_and_Shield_and_Dual_Blades_Weapon_Tree'
if weapon_one == "DB": weapon_one = "DS" # wiki site uses 'ds' as the abbr instead of 'db'
elif weapon_two == "DB": weapon_two = "DS"

logging.basicConfig(
    filename=f'scrape-log.txt',
    filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

class Crawler:

    def __init__(self, urls=[]):
        self.visited_urls    = []
        self.weapon_list_one = []
        self.weapon_list_two = []
        self.all_names       = []
        self.urls_to_visit   = urls

    def url_crawl(self, url):
        html = requests.get(url).text
        for url in self.init_weapon_info(url, html):
            self.urls_to_visit.append(url)

    def init_weapon_info(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        rows = []
        for table in soup.find_all(class_="treetable"):
          rows.extend(table.find_all('tr'))

        for row in rows:
          if len(row.find_all('td')) == 1: # skip title rows 
            continue
          elif row.find('a') == None: # skip heading rows
            continue
          elif row('a')[1].get_text(strip=True).startswith('Dummy'): # ignore 'Dummy' entries
            continue
          elif row.find_all('td')[0].find_all('a')[1].get_text(strip=True) in self.all_names: # skip duplicates
            print("duplicate detected", row.find_all('td')[0].find_all('a')[1].get_text(strip=True))
            continue
          
          cells = row.find_all('td')
          current_weapon = {
            "name": cells[0].find_all('a')[1].get_text(strip=True),
            "attack": cells[1].get_text(strip=True),
            "element": cells[2].get_text(strip=True),
            "sharpness": self.parse_sharpness(cells[3].find_all("img")),
            "affinity": cells[4].get_text(strip=True),
            "slots": cells[5].get_text(strip=True),
            "bonus": cells[6].get_text(strip=True),
            "rarity": cells[7].get_text(strip=True),
          }
          for prop in current_weapon: # Fill blanks
            if current_weapon[prop] == "": current_weapon[prop] = 'N/A'

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
          else: print("Weapon match failed!", current_weapon["name"])

          self.all_names.append(current_weapon["name"])
          
          if current_weapon["type"] == "ds": current_weapon["type"] = "db" # once again fix db / ds issue

          yield weapon_link

    def get_addl_info(self, url, current_weapon, weapon_type):
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')

        failure = False
        # Format 1
        try:
          a_list    = soup.find_all('a', string=re.compile('MHFU: '))    #couple extra hoops to jump through
          table_two = a_list[len(a_list)-1].parent.parent.parent.parent #to make sure we get the right table
          table_one = table_two.previous_sibling.previous_sibling
          tables    = [table_one, table_two]
          table_one_rows = table_one.find_all("tr")
          table_two_rows = table_two.find_all("tr")

          current_weapon["create-cost"]  = table_one_rows[2].find_all("td")[2].get_text(strip=True)
          current_weapon["upgrade-cost"] = table_one_rows[2].find_all("td")[3].get_text(strip=True)
          if len(tables[1].find_all("tr")[2].find_all("td")[0].find_all('a')) > 1:
            current_weapon["upgrade-from"] = [
              table_two_rows[2].find_all("td")[0].find_all('a')[0].get_text(strip=True),
              table_two_rows[2].find_all("td")[0].find_all('a')[1].get_text(strip=True),
            ]
            #print('double origin', current_weapon["upgrade-from"])
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
            print("Format 2 failed on", current_weapon["link"])
            failure = True

        # "None" fixer for consistency
        for key in current_weapon:
          if current_weapon[key] == "None":
            current_weapon[key] = "N/A"

        # sometimes items are listed as 'upgrade only' by site when they are instead 'create only', swap if true
        if current_weapon["upgrade-from"] == "N/A" and [current_weapon["upgrade-cost"], current_weapon["upgrade-mats"]] != ["N/A","N/A"]:
          current_weapon["create-cost"] = current_weapon["upgrade-cost"]
          current_weapon["create-mats"] = current_weapon["upgrade-mats"].copy()
          current_weapon["upgrade-cost"] = "N/A"
          current_weapon["upgrade-mats"] = "N/A"

        # if it's a dual blade double element, put spaces around the slash
        if "/" in current_weapon["element"]: 
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
        return sharpness_string

    def run(self):
        global weapon_one
        global weapon_two

        # Build initial list
        url = self.urls_to_visit.pop(0)
        logging.info(f'Crawling: {url}')
        
        self.url_crawl(url)
        self.visited_urls.append(url)
        print(f'{len(self.urls_to_visit)} urls to visit') # Print number of pages
        total_urls = len(self.urls_to_visit)


        # Get upgrade/create info, and any weapon-type-unique info
        index = 0
        weapon_count = 1
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
                print(weapon_count)
                weapon_count += 1
          index += 1

        total_weapons = [self.weapon_list_one, self.weapon_list_two]

        #dump to file
        #change ds back to db for consistency
        if weapon_one == "DS": weapon_one = "DB"
        elif weapon_two == "DS": weapon_two = "DB"
        fhandle = open(f'{weapon_one.lower()}-{weapon_two.lower()}-data.json', 'w')
        fhandle.write(json.dumps(total_weapons))
        fhandle.close()

if __name__ == '__main__':
    Crawler(urls=[tree_link]).run()
