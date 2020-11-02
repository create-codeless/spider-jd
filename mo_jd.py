# -*- coding: utf-8 -*-
# @Time    : 2020/11/2 19:20
# @Author  : lanyu
import json

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning,InsecurePlatformWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from selenium import webdriver
from loguru import logger
import time
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, WebDriverException
from lxml import etree
from retrying import retry
from selenium.webdriver import ActionChains
from loguru import logger

import pymongo
mongo_url = 'localhost'
mongo_db = 'jd'
mongo_table = 'jd_data'
client = pymongo.MongoClient(mongo_url)
db = client[mongo_db]




class Jd(object):
    def __init__(self):
        # self.browser = webdriver.Firefox()
        # options = webdriver.FirefoxProfile()
        # options.set_preference('permissions.default.image', 2)
        # self.browser = webdriver.Firefox(options)
        option = webdriver.FirefoxOptions()
        # 无头模式
        option.add_argument("-headless")
        # 禁止加载图片
        option.set_preference('permissions.default.image', 2)
        # 禁止加载css样式表
        option.set_preference('permissions.default.stylesheet', 2)
        self.browser = webdriver.Firefox(options=option)
        # 设置页面加载超时，超过这个时间就会抛出异常，执行之后的代码，不然会卡在>一直加载
        # self.firefox.set_page_load_timeout(5)
        # self.firefox.set_script_timeout(5)

        self.browser.implicitly_wait(5)
        self.domain = 'https://www.jd.com/'
        self.action_chains = ActionChains(self.browser)
        # 处理抓取为空的字段
        self.handleNone = lambda x: x if x else ' '
        self.headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36',
            'Host': 'club.jd.com'
        }
        self.session = requests.session()

    def get_product(self, product_name):
        self.browser.get(self.domain)
        self.browser.find_element_by_class_name('text').send_keys(product_name)
        self.browser.find_element_by_css_selector("button").click()  # 点击搜索
        # 等待加载
        time.sleep(1)
        self.get_product_detail()

    def drop_down(self):
        for x in range(1, 8):
            time.sleep(0.3)
            j = x / 10
            js = f"document.documentElement.scrollTop = document.documentElement.scrollHeight * {j}"
            self.browser.execute_script(js)
        # 兄地~太快容易出验证码
        time.sleep(2)

    def get_product_detail(self):
        self.drop_down()
        res = self.browser.page_source
        # selector = etree.HTML(html)
        html = etree.HTML(res)
        page = ''.join(html.xpath('//span[@class="p-num"]/a[@class="curr"]/text()')) # 提取当前页面
        # items = html.xpath('//div[contains(@id,"J_goodsList")]/ul/li[contains(@class,"gl-item")]')
        # for item in items[:1]:
        #     goods_ids = item.xpath('./@data-sku')[0]  # 获取商品id号     作为页面的id号
        #     title = self.handleNone(item.xpath(''.join('.//div[contains(@class,"p-name")]/a/i/text()')))
        #     # goods_names_tag.strip('\n ')
        #     # 提取商品标题
        #     price = self.handleNone(item.xpath(''.join('.//div[@class="p-price"]//i/text()'))) # 提取商品价格
        #     shop_name = self.handleNone(item.xpath(''.join('.//div[@class="p-shop"]//a/text()'))) # 提取店铺
        #     # goods_commits = item.xpath('.//div[@class="p-commit"]//a')  # 提取评价
        #     # logger.info(f"标题:{goods_names_tag}|价格:{goods_prices}|店名:{goods_stores_tag}|商铺ID:{goods_ids}")
        logger.info(f'抓取第{page}页完成')

        goods_ids = html.xpath(
            './/ul[@class="gl-warp clearfix"]/li[@class="gl-item"]/@data-sku')  # 获取商品id号     作为页面的id号
        goods_names_tag = html.xpath('.//div[@class="p-name p-name-type-2"]/a/em')  # 提取商品标题
        goods_prices = html.xpath('.//div[@class="p-price"]//i')  # 提取商品价格
        goods_stores_tag = html.xpath('.//div[@class="p-shop"]')  # 提取店铺
        goods_commits = html.xpath('.//div[@class="p-commit"]//a')  # 提取评价
        goods_names = []
        for goods_name in goods_names_tag:
            goods_names.append(goods_name.xpath('string(.)').strip())

        goods_stores = []
        for goods_store in goods_stores_tag:
            goods_stores.append(goods_store.xpath('string(.)').strip())

        goods_price = []
        for price in goods_prices:
            goods_price.append(price.xpath('string(.)').strip())

        goods_commit = []
        for commit in goods_commits:
            goods_commit.append(commit.xpath('string(.)').strip())

        goods_infos = list()  # 把所有的数据添加到 列表里面

        for i in range(0, len(goods_ids)):
            goods_info = {
            'ID' : goods_ids[i],
            '标题' : goods_names[i],
            '价格' : goods_price[i],
            '店铺' : goods_stores[i]
            }
            goods_infos.append(goods_info)
        return goods_infos

    # def get_next_page(self):
    #     try:
    #         next_btn = self.browser.find_element_by_xpath('.//a[@class="pn-next"]')      # 下一页地址
    #         if 'next-disabled' in next_btn.get_attribute('class'):
    #             logger.info('没有下一页，抓取完成')
    #         else:
    #             next_btn.click()
    @retry(stop_max_attempt_number=5, wait_fixed=2000)
    def request(self,url):
        # while True:
        try:
            res =self.session.get(url,headers=self.headers,verify=False)
        except ConnectionError:
            print('草率了')
        if res.status_code== 200:
            return res.text



    def parse_goods_comment(self,goods_id):
        """
        https://club.jd.com   抓包工具 接口数据
        :param goods_id:
        :return:   用户的评论数据
        """
        comm_url = r'https://club.jd.com/comment/productCommentSummaries.action?referenceIds={}'
        url = comm_url.format(goods_id)
        print(url)
        res = self.request(url) # 让他重试3次
        comment_json = json.loads(res)
        comments_list = comment_json['CommentsCount'][0]
        comment_count = comments_list['CommentCount']  # 总评论数
        good_count = comments_list['GoodCount']   # 好评数
        poor_count = comments_list['PoorCount']   # 差评
        good_rate = comments_list['GoodRate']    # 好评率
        comment_info = dict()
        comment_info['评论量'] = comment_count
        comment_info['好评'] = good_count
        comment_info['差评'] = poor_count
        comment_info['好评率'] = good_rate
        # https://item.jd.com/100011323932.html
        comment_info['商品地址'] = 'https://item.jd.com/'+ goods_id + '.html'
        return comment_info

    def save_mongo(self, data):
        try:
            if db[mongo_table].insert(data):
                print('保存成功')
        except Exception as e:
            print(e)

    def run(self):
        while True:
            s = self.get_product_detail()
            for i in s:
                comment_info = self.parse_goods_comment(i.get('ID'))
                info = dict(i, **comment_info)
                self.save_mongo(info)

            next = self.browser.find_element_by_xpath('.//a[@class="pn-next"]')  # 下一页地址
            if 'next-disabled' in next.get_attribute('class'):
                logger.info('没有下一页，抓取完成')
                break
            else:
                next.click()


if __name__ == '__main__':
    s = Jd()
    s.get_product('口红')
    s.run()

