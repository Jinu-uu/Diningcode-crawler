from lib2to3.pgen2 import driver
from typing import Union
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchWindowException
import pandas as pd
import numpy as np
import re
from tqdm import tqdm

class DanawaCrawler:
    SEOUL_DISTRICT = ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구','구로구', 
                '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구',
                '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구',
                '은평구', '종로구', '중구', '중랑구']
    SEARCH_URL = 'https://www.diningcode.com/list.dc?query='
    DETAIL_URL = 'https://www.diningcode.com/profile.php?rid='
    TIMEOUT_LIMIT = 20
    CATEGORY_URL = {
        # 'CPU'   :'http://prod.danawa.com/list/?cate=112747',
        # 'RAM'   :'http://prod.danawa.com/list/?cate=112752',
        # 'VGA'   :'http://prod.danawa.com/list/?cate=112753',
        # 'MBoard'   :'http://prod.danawa.com/list/?cate=112751',
        # 'SSD'   :'http://prod.danawa.com/list/?cate=112760',
        'HDD'   :'http://prod.danawa.com/list/?cate=112763',
        # 'Power'   :'http://prod.danawa.com/list/?cate=112777',
        # 'Cooler'   :'http://prod.danawa.com/list/?cate=11236855',
        # 'Case'   :'http://prod.danawa.com/list/?cate=112775',
        # 'Monitor'   :'http://prod.danawa.com/list/?cate=112757',
        # 'Speaker'   :'http://prod.danawa.com/list/?cate=112808',
        # 'Headphone'   :'http://prod.danawa.com/list/?cate=113837',
        # 'Earphone'   :'http://prod.danawa.com/list/?cate=113838',
        # 'Headset'   :'http://prod.danawa.com/list/?cate=11225097',
        # 'Keyboard'   :'http://prod.danawa.com/list/?cate=112782',
        # 'Mouse'   :'http://prod.danawa.com/list/?cate=112787',
        # 'Laptop'   :'http://prod.danawa.com/list/?cate=112758',
    }
    DETAIL_PAGE_URL = 'https://prod.danawa.com/info/?pcode='
    SAVE_DIR = './diningcode.h5'
    SAVE_KEY_INTERVAL = 5
    SAVE_DETAIL_INTERVAL = 5
    SAVE_REVIEW_INTERVAL = 2


    def __init__(self):
        options = ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--incognito')
        # options.add_argument('--headless')
        # options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = ChromeService(ChromeDriverManager().install())
        self.driver = ChromeDriver(service=service, options=options)


    def __del__(self):
        self.driver.quit()


    def wait(self):
        WebDriverWait(self.driver, self.TIMEOUT_LIMIT).until(EC.invisibility_of_element((By.CLASS_NAME, 'product_list_cover')))
        

    
    def find_element_or_wait(self, element : Union[WebDriver, WebElement], xpath):
        WebDriverWait(element, self.TIMEOUT_LIMIT).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        return element.find_element(By.XPATH, xpath)


    def find_element_or_none(self, element : Union[WebDriver, WebElement], xpath):
        ret = element.find_elements(By.XPATH, xpath)
        return ret[0] if ret else None

    
    def click_wait_update(self, element : Union[WebDriver, WebElement], update_xpath, button_xpath):
        update = self.find_element_or_wait(element, update_xpath)
        button = self.find_element_or_wait(element, button_xpath)
        WebDriverWait(element, self.TIMEOUT_LIMIT).until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
        button.click()
        WebDriverWait(self.driver, self.TIMEOUT_LIMIT).until(EC.staleness_of(update))



    def crawling(self):
        print('Crawl primary keys')
        self.crawling_id()
        # print('Crawl details')
        # self.crawling_detail()
        # print('Crawl reviews')
        # self.crawling_review()


    def crawling_id(self):
        df = pd.DataFrame(columns=['id'])
        df.to_hdf(self.SAVE_DIR, 'ID')
        for district in self.SEOUL_DISTRICT:
            print(f'Processing {district}')
            while True:
                try:
                    self.driver.get(self.SEARCH_URL + district)
                    self.wait()

                    for x in range(4): self.find_element_or_wait(self.driver, '//*[@class="SearchMore upper"]').click()

                    raw_id = self.driver.find_elements(By.XPATH, '//*[@class="PoiBlock"]')
                    restaurant_url_list = []

                    for x in raw_id:
                        restaurant_url_list.append(x.get_attribute('id').replace('block',''))
                    tmp_df = pd.DataFrame({'id' : restaurant_url_list})

                except NoSuchWindowException:
                    print('Window already closed')
                    exit(-1)
                except Exception as e:
                    print(e)
                    print('Restart')
                else:
                    df = pd.concat([df, tmp_df], axis = 0)
                    df.to_hdf(self.SAVE_DIR, 'ID')
                    break

        df = df.reset_index().drop(columns=['index'])
        df.to_hdf(self.SAVE_DIR, 'ID')


    def crawling_detail(self):
        for category_title in self.CATEGORY_URL.keys():
            indices = pd.read_hdf(self.SAVE_DIR, category_title)
            indices = indices.loc[indices['id_validator'] == True].index
            df = pd.DataFrame(columns=['name', 'image', 'price', 'shop_link', 'shop_name', 'shop_logo'])
            df['price'] = df['price'].astype(np.float64)
            df.to_hdf(self.SAVE_DIR, f'{category_title}_detail')

            progress = 0
            while True:
                df = pd.read_hdf(self.SAVE_DIR, f'{category_title}_detail')
                try:
                    for i in tqdm(range(progress, len(indices)), category_title, initial=progress, total=len(indices)):
                        idx = indices[i]
                        self.driver.get(self.DETAIL_PAGE_URL + idx)
                        self.wait()

                        name = self.find_element_or_wait(self.driver, '//*[@class="top_summary"]/h3').text
                        image = self.find_element_or_wait(self.driver, '//*[@id="baseImage"]').get_attribute('src')


                        review_count = self.find_element_or_none(self.driver, '//*[@class="smr_title"]//strong//em')
                        if review_count == None:
                            continue
                        if int(review_count.text.replace(',','')) < 12:
                            continue


                        price = np.NaN
                        shop_link, shop_name, shop_logo = '', '', ''
                        price_area = self.find_element_or_none(self.driver, '//*[@class="high_list"]/*[@class="lowest"]')
                        if price_area:
                            price = price_area.find_element(By.XPATH, '*[@class="price"]/*[1]/*[@class="txt_prc"]/*[1]').text
                            price = float(price.replace(',', ''))
                            shop_link = price_area.find_element(By.XPATH, '*[@class="mall"]/*[1]/*[1]').get_attribute('href')
                            shop_image = self.find_element_or_none(price_area, '*[@class="mall"]/*[1]/*[1]/*[1]')
                            if shop_image:
                                shop_name = shop_image.get_attribute('alt')
                                shop_logo = shop_image.get_attribute('src')
                            else:
                                shop_name = price_area.find_element(By.XPATH, '*[@class="mall"]/*[1]/*[1]').get_attribute('title')
                        
                        df.loc[idx] = [name, image, price, shop_link,   shop_name, shop_logo] + [''] * (len(df.columns) - 6)

                        # score crawling
                        mall_review_flag = self.find_element_or_none(self.driver, '//*[@class="tab_item"]//*[@class="num_c"]')
                        click_tab_flag = len(self.driver.find_elements(By.XPATH, '//li[@class="tab_item"]'))
                        self.find_element_or_wait(self.driver, f'//li[@class="tab_item"][{click_tab_flag}]/*').click()
                        WebDriverWait(self.driver, self.TIMEOUT_LIMIT).until(EC.invisibility_of_element((By.XPATH, '//img[@alt="로딩중"]')))
                        mall_review_flag2 = self.find_element_or_none(self.driver, '//*[@class="txt_no_v2"]')
                        if mall_review_flag and mall_review_flag2 == None:
                            score = self.find_element_or_wait(self.driver, '//*[@class="point_num"]/*[1]')
                            mall_review = self.find_element_or_wait(self.driver, '//*[@class="point_num"]/*[2]')
                            df.loc[idx, 'score'] = score.text
                            df.loc[idx, 'mall_review'] = mall_review.text
                        else:
                            df.loc[idx, 'score'] = np.nan
                            df.loc[idx, 'mall_review'] = np.nan

                        # spec crawling
                        spec_area = self.driver.find_elements(By.XPATH, '//*[@class="spec_tbl"]/tbody/*/*')
                        division = ''
                        key = None
                        value = None
                        for element in spec_area:
                            if element.get_attribute('class') == 'tit':
                                key = element.text
                            elif element.get_attribute('class') == 'dsc':
                                value = element.text
                            else:
                                division = element.text
                            if key != None and value != None:
                                if key != '':
                                    complete_key = division + key
                                    if complete_key not in df:
                                        df[complete_key] = ''
                                    df.loc[idx, complete_key] = value
                                key = None
                                value = None
                        
                        if (i + 1) % self.SAVE_DETAIL_INTERVAL == 0 or (i + 1) == len(indices):
                            df.to_hdf(self.SAVE_DIR, f'{category_title}_detail')
                            progress = i + 1
                            
                except NoSuchWindowException:
                    print('Window already closed')  
                    print(f'Current page is {progress}')
                    exit(-1)
                except Exception as e:
                    print(e)
                    print(f'Restart from {progress} page')
                else:
                    df.to_hdf(self.SAVE_DIR, f'{category_title}_detail')
                    break


    def crawling_review(self):
        for category_title in self.CATEGORY_URL.keys():
            indices = pd.read_hdf(self.SAVE_DIR, f'{category_title}')
            indices = indices.loc[indices['id_validator'] == True].index
            df = pd.DataFrame(columns=['id', 'comment', 'time', 'good', 'bad'])
            df.to_hdf(self.SAVE_DIR, f'{category_title}_review')

            progress = 0
            while True:
                df = pd.read_hdf(self.SAVE_DIR, f'{category_title}_review')
                try:
                    for i in tqdm(range(progress, len(indices)), category_title, initial=progress, total=len(indices)):
                        idx = indices[i]
                        self.driver.get(self.DETAIL_PAGE_URL + idx)
                        self.wait()

                        filter_button_xpaths = []
                        filter_button_xpaths.append('//*[@id="danawa-prodBlog-productOpinion-button-leftMenu-23"]')
                        filter_button_xpaths.append('//*[@id="danawa-prodBlog-productOpinion-button-leftMenu-83"]')
                        for filter_button_xpath in filter_button_xpaths:
                            self.click_wait_update(self.driver, '//*[@class="danawa_review"]', '//*[@class="danawa_review"]' + filter_button_xpath)
                            review_area = self.find_element_or_wait(self.driver, '//*[@class="danawa_review"]')
                            while True:
                                page_count = len(review_area.find_elements(By.XPATH, './/*[@class="page_nav_area"]/*[2]/*'))
                                if page_count == 0:
                                    break
                                for page_num in range(page_count):
                                    if page_num > 0:
                                        self.click_wait_update(self.driver, '//*[@class="danawa_review"]', f'.//*[@class="page_nav_area"]/*[2]/*[{page_num + 1}]')
                                        review_area = self.find_element_or_wait(self.driver, '//*[@class="danawa_review"]')

                                    reviews = self.find_element_or_wait(review_area, './/*[@class="cmt_list"]')
                                    reviews = reviews.find_elements(By.XPATH, '*[@class="cmt_item"]')
                                    for review in reviews:
                                        comment = review.find_element(By.XPATH, './/*[@class="danawa-prodBlog-productOpinion-clazz-content"]/input').get_attribute('value')
                                        time = review.find_element(By.XPATH, './/*[@class="date"]').text
                                        good = self.find_element_or_none(review, './/*[@class="btn_like"]/*[2]')
                                        good = float(good.text if good.text else 0) if good else np.NaN
                                        bad = self.find_element_or_none(review, './/*[@class="btn_dislike"]/*[2]')
                                        bad = float(bad.text if bad.text else 0) if bad else np.NaN
                                        df.loc[len(df.index)] = [idx, comment, time, good, bad]

                                next_button = review_area.find_element(By.XPATH, './/*[@class="page_nav_area"]/*[3]')
                                if next_button.get_attribute('class') == 'nav_edge nav_edge_next nav_edge_on':
                                    self.click_wait_update(self.driver, '//*[@class="danawa_review"]', '//*[@class="danawa_review"]//*[@class="page_nav_area"]/*[3]')
                                    review_area = self.find_element_or_wait(self.driver, '//*[@class="danawa_review"]')
                                else:
                                    break
                        
                        if (i + 1) % self.SAVE_REVIEW_INTERVAL == 0 or (i + 1) == len(indices):
                            df.to_hdf(self.SAVE_DIR, f'{category_title}_review')
                            progress = i + 1

                except NoSuchWindowException:
                    print('Window already closed')
                    print(f'Current page is {progress}')
                    exit(-1)
                except Exception as e:
                    print(e)
                    print(f'Restart from {progress} page')
                else:
                    df.to_hdf(self.SAVE_DIR, f'{category_title}_review')
                    break


DanawaCrawler().crawling()