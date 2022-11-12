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

class DiningCodeCrawler:
    SEOUL_DISTRICT = ['강남구', '강동구', '강북구', '강서구', '관악구', '광진구','구로구', 
                '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구',
                '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구',
                '은평구', '종로구', '중구', '중랑구']
    SEARCH_URL = 'https://www.diningcode.com/list.dc?query='
    DETAIL_URL = 'https://www.diningcode.com/profile.php?rid='
    TIMEOUT_LIMIT = 2
    SAVE_POINT_DIR = './savepoint.text'
    SAVE_DIR = './diningcode_revision.h5'
    RE_NUM = re.compile(r'\d+')


    def __init__(self):
        options = ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--incognito')
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = ChromeService(ChromeDriverManager().install())
        self.driver = ChromeDriver(service=service, options=options)


    def __del__(self):
        self.driver.quit()


    # def wait(self):
    #     WebDriverWait(self.driver, self.TIMEOUT_LIMIT).until(EC.invisibility_of_element((By.CLASS_NAME, 'product_list_cover')))
        

    
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

    def load_save_point(self):
        save_file = open(self.SAVE_POINT_DIR, 'r')
        save_index = save_file.read()
        save_file.close()
        return int(save_index)

    def write_save_point(self, index):
        write_file = open(self.SAVE_POINT_DIR, 'w')
        write_file.write(str(index))
        write_file.close()

    def crawling(self):
        print('Crawl ID')
        self.crawling_id()
        print('Crawl reviews')
        self.crawling_review()

    def crawling_id(self):
        df = pd.DataFrame(columns=['id'])
        for district in self.SEOUL_DISTRICT:
            print(f'Processing {district}', end=' ')
            while True:
                try:
                    self.driver.get(self.SEARCH_URL + district)

                    for x in range(4): 
                        self.find_element_or_wait(self.driver, '//*[@class="SearchMore upper"]').click()
                        self.driver.implicitly_wait(10)

                    self.driver.find_elements(By.XPATH, '//*[@class="tmp loading asdfASDF--"]/*[2]')
                    #없는 elements 찾아서 강제로 전체 탐색
                    raw_id = self.driver.find_elements(By.XPATH, '//*[@class="PoiBlockContainer"]/*[2]')

                    restaurant_url_list = []
                    print(len(raw_id))
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
        df.reset_index().drop(columns=['index'])
        df.to_hdf(self.SAVE_DIR, 'ID')


    def crawling_review(self):
        id_list = list(pd.read_hdf('./diningcode.h5', 'ID')['id'])
        start = self.load_save_point()
        if start == 0:
            df = pd.DataFrame(columns=['ID', 'Name', 'Types', 'Like Count', 'Location',
                                    'Tags', 'Total Review', 'Total Score', 'Score', 'Detail Score',
                                    'Total Tag', 'Open Time', 'Menu', 'User', 'Daco',
                                    'Detail Score List', 'Date List', 'Total Score List', 'Review List', 'Review Rec List'])
            df.to_hdf(self.SAVE_DIR, 'Detail')
        else:
            df = pd.read_hdf(self.SAVE_DIR, 'Detail')

        while(True):
            for index in tqdm(range(start, len(id_list))):
                try:
                    self.driver.get(self.DETAIL_URL + id_list[index])
                    
                    tmp_len = len(self.driver.find_elements(By.XPATH, '//*[@class="more-btn button"]'))
                    tmp_clicks = self.driver.find_elements(By.XPATH, '//*[@class="more-btn button"]')
                    for x in range(tmp_len):
                        tmp_clicks[x].click()
                    menu_flag = 1
                    tmp_menu_click = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="menu-info short"]//*[@class="more-btn"]')
                    if len(tmp_menu_click) != 0:
                        tmp_menu_click[0].click()
                        menu_flag = 0

                    open_flag = 1
                    tmp_open_click = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="busi-hours short"]//*[@class="more-btn"]')
                    if len(tmp_open_click) != 0:
                        tmp_open_click[0].click()
                        open_flag = 0

                    if menu_flag == 0:
                        menu_left = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="menu-info"]//*[@class="l-txt Restaurant_MenuItem"]')
                        menu_right = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="menu-info"]//*[@class="r-txt Restaurant_MenuPrice"]')
                    else:
                        menu_left = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="menu-info short"]//*[@class="l-txt Restaurant_MenuItem"]')
                        menu_right = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="menu-info short"]//*[@class="r-txt Restaurant_MenuPrice"]')
                    
                    if open_flag == 0:
                        open_left = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="busi-hours"]//*[@class="l-txt"]')
                        open_right = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="busi-hours"]//*[@class="r-txt"]')
                    else:
                        open_left = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="busi-hours short"]//*[@class="l-txt"]')
                        open_right = self.driver.find_elements(By.XPATH, '//*[@class="s-list detail-info"]//*[@class="busi-hours short"]//*[@class="r-txt"]')
                    

                    restaurant_open_time = []
                    for x in range(len(open_left)):
                        restaurant_open_time.append(f"{open_left[x].text}---{open_right[x].text}")

                    restaurant_menu = []
                    for x in range(len(menu_left)):
                        restaurant_menu.append(f"{menu_left[x].text}---{menu_right[x].text}")

                    print(restaurant_open_time,restaurant_menu)
                    restaurant_name = self.find_element_or_none(self.driver, '//*[@class="s-list pic-grade"]//*[@class="tit-point"]//*[@class="tit"]').text
                    restaurant_type = self.find_element_or_none(self.driver, '//*[@class="s-list pic-grade"]//*[@class="btxt"]').text.split('|')[1].strip().split(',')
                    restaurant_like = self.find_element_or_none(self.driver, '//*[@class="favor-pic-appra"]//*[@class="favor"]/*//*[@class="num"]').text
                    restaurant_location = self.find_element_or_none(self.driver, '//*[@class="locat"]').text
                    restaurant_tag = self.find_element_or_none(self.driver, '//*[@class="tag"]').text.split(',') + self.find_element_or_none(self.driver, '//*[@class="char"]').text.split(',')
                    total_tag = self.driver.find_elements(By.XPATH, '//*[@class="app-arti"]//*[@class="icon"]')
                    restaurant_total_tag = []
                    for x in range(len(total_tag)):
                        restaurant_total_tag.append(total_tag[x].text)
                    

                    restaurant_total_review_count = int(self.RE_NUM.findall(self.find_element_or_none(self.driver, '//*[@class="s-list appraisal"]//*[@class="tit"]').text)[0])
                    restaurant_total_score = self.find_element_or_none(self.driver, '//*[@class="sns-grade"]//*[@class="grade"]/*[1]').text
                    restaurant_score = self.find_element_or_none(self.driver, '//*[@class="grade-info"]//*[@class="star-point"]//*[@class="point"]').text
                    restaurant_detail_score = self.find_element_or_none(self.driver, '//*[@class="grade-info"]//*[@class="point-detail"]').text.split(' ')

                    while(True):
                        self.driver.implicitly_wait(10)
                        view_more = self.find_element_or_none(self.driver, '//*[@id="div_more_review"]')
                        if view_more == None: break
                        view_more.click()
                    review_area = self.driver.find_elements(By.XPATH, '//*[@class="latter-graph"]')
                    review_user, review_user_daco, review_detail_score_list, review_date, review_total_score_list, review_list, review_rec = [], [], [], [], [], [], []

                    for x in range(len(review_area)):
                        review_user.append(self.find_element_or_none(review_area[x], '*[@class="person-grade"]//*[@class="btxt"]').text)
                        daco_flag = self.find_element_or_none(review_area[x], '*[@class="person-grade"]//*[@class="btxt"]//img')

                        if daco_flag == None:
                            review_user_daco.append(0)
                        else:
                            review_user_daco.append(1)

                        if len(review_area[x].find_elements(By.XPATH, '*[@class="point-detail"]')) != 0:
                            review_detail_score_list.append(self.find_element_or_none(review_area[x], '*[@class="point-detail"]').text)
                        else:
                            review_detail_score_list.append(np.NaN)

                        date = self.find_element_or_none(review_area[x], '*[@class="person-grade"]//*[@class="star-date"]/*[2]').text
                        if len(date.split(' ')) == 2:
                            date = '2022년 ' + date

                        review_date.append(date)
                        review_total_score_list.append(int(self.RE_NUM.findall(self.find_element_or_none(review_area[x], '*[@class="person-grade"]//*[@class="star-date"]/*[1]/*[1]').get_attribute('style'))[0])/20)
                        
                        if len(review_area[x].find_elements(By.XPATH, '*[@class="review_contents btxt"]')) != 0:
                            review_list.append(self.find_element_or_none(review_area[x], '*[@class="review_contents btxt"]').text.replace('\n', ''))
                        else:
                            review_list.append(np.NaN)
                        review_rec.append(self.find_element_or_none(review_area[x], '*[@class="symp-btn"]').text)

                    df.loc[index] = [id_list[index], restaurant_name, restaurant_type, restaurant_like, restaurant_location,
                                    restaurant_tag, restaurant_total_review_count, restaurant_total_score,restaurant_score, restaurant_detail_score,
                                    restaurant_total_tag, restaurant_open_time, restaurant_menu, review_user, review_user_daco,
                                    review_detail_score_list, review_date, review_total_score_list, review_list, review_rec]

                except NoSuchWindowException:
                    print('Window already closed')  
                    print(f'Current page is {index}')
                    exit(-1)
                except Exception as e:
                    print(e)
                    print(f'Restart from {index} page')
                else:
                    df.to_hdf(self.SAVE_DIR, 'Detail')
                    self.write_save_point(index+1)
        
        df.to_hdf(self.SAVE_DIR, 'Detail')

if __name__ == "__main__":
    DiningCodeCrawler().crawling()