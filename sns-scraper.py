import logging
import json
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from bs4 import SoupStrainer

logging.basicConfig(
    filename='sns-log.txt',
    filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s',
    level=logging.INFO)

class Crawler:

    def __init__(self, urls=[]):
        self.visited_urls  = []
        self.weapon_list   = []
        self.urls_to_visit = urls

    def get_weapon_urls(self, url, html):
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all(class_="category-page__member-link"):
            path = link.get('href')
            if path and path.startswith('/'):
                path = urljoin(url, path)
            yield path

    def url_crawl(self, url):
        html = requests.get(url).text
        for url in self.get_weapon_urls(url, html):
            self.urls_to_visit.append(url)

    def compile_info(self, url):
        soup = BeautifulSoup(requests.get(url).text, 'html.parser')
        current_weapon = {
          "name": soup.find_all(attrs={"data-source": "English Name"})[1].get_text(strip=True),
          "attack": soup.find(attrs={"data-source": "Attack"}).find(class_="pi-data-value pi-font").get_text(strip=True),
          "attribute": soup.find(attrs={"data-source": "Special"}).find(class_="pi-data-value pi-font").get_text().strip(),
          "affinity": soup.find(attrs={"data-source": "Affinity"}).find(class_="pi-data-value pi-font").get_text(strip=True),
          "sharpness": self.parse_sharpness(soup.find(attrs={"data-source": "Sharpness"}).find_all("img")),
          "slots": soup.find(attrs={"data-source": "Slots"}).find(class_="pi-data-value pi-font").get_text(strip=True),
          "bonus": soup.find(attrs={"data-source": "Defense"}).find(class_="pi-data-value pi-font").get_text(strip=True),
          "rarity": soup.find(attrs={"data-source": "Rarity"}).find(class_="pi-data-value pi-font").get_text(strip=True),
          "create-cost": soup.find_all(attrs={"data-source": "Creation Cost"})[1].get_text(strip=True),
          "create-mats": [], # handled by loop
          "upgrade-cost": soup.find_all(attrs={"data-source": "Upgrade Cost"})[1].get_text(strip=True),
          "upgrade-mats": [], # handled by loop
          "upgrade-from": soup.find_all(attrs={"data-source": "Upgraded From"})[1].get_text(strip=True),
          "upgrade-to": [] # handled by loop
        }

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
        

        return current_weapon

    def parse_sharpness(self, image_list):
        sharpness_string = ""
        for image in image_list:
            sharpness_string = sharpness_string + image['alt'][0:-4]
        return sharpness_string

    def run(self):

        # Build initial list
        url = self.urls_to_visit.pop(0)
        logging.info(f'Crawling: {url}')
        
        self.url_crawl(url)
        self.visited_urls.append(url)
        print(f'{len(self.urls_to_visit)} urls to visit') # Print number of pages

        # Compile all the info
        while self.urls_to_visit:
            url = self.urls_to_visit.pop(0)
            #logging.info(f'Reading: {url}') # verbosity, print current page
            try:
                weapon = self.compile_info(url)
            except Exception:
                logging.exception(f'Failed to crawl: {url}')
            finally:
                self.weapon_list.append(weapon)
                #print(weapon) # verbosity, print the grabbed weapon details
        
        #dump to file
        fhandle = open('sns-data.txt', 'w')
        fhandle.write(json.dumps(self.weapon_list))
        fhandle.close()

if __name__ == '__main__':
    Crawler(urls=['https://monsterhunter.fandom.com/wiki/Category:MHFU_Swords_and_Shields']).run()