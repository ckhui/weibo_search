import re
from datetime import datetime, timedelta
from urllib.parse import unquote
import utils.util as util
from WeiboModel import WeiboItem 
import settings
from lxml import html, etree
import requests
from TokenPool import TokenPool
from OutfileHelper import *

# split day to hour
# build request
# send request with token
# request2object / error

class TokenError(Exception):
    pass

DEFAULT_REQUEST_HEADERS = {
    'Accept':
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
    'cookie': "YOUR cookie"
}

def buildHeader(cookie):
    header = DEFAULT_REQUEST_HEADERS
    header['cookie'] = cookie
    return header

class WeiboSearch():
    def __init__(self):
        super().__init__()
        self.weibo_type = util.convert_weibo_type(settings.WEIBO_TYPE)
        self.contain_type = util.convert_contain_type(settings.CONTAIN_TYPE)
        self.regions = util.get_regions(settings.REGION)
        self.base_url = 'https://s.weibo.com/weibo'

        
        self.keyword_list = settings.KEYWORD_LIST
        self.start_date = settings.START_DATE
        self.end_date = settings.END_DATE

        self.tokenPool = TokenPool()
        self.logger = CompletionLog()
        

    def urlBuilder(self, keyword, date, hour, province=None, city=None):
        date_str = date.strftime('%Y-%m-%d') + '-0'
        start_date = datetime.strptime(date_str, '%Y-%m-%d-%H')
        start_date = start_date + timedelta(hours=hour)

        start_str = start_date.strftime('%Y-%m-%d-X%H').replace('X0', 'X').replace('X', '')
        end_time = start_date + timedelta(hours=1)
        end_str = end_time.strftime('%Y-%m-%d-X%H').replace('X0', 'X').replace('X', '')
        url = self.base_url + '?q=%s'%keyword

        if not province is None:
            if city is None:
                city = '1000'
            url += '&region=custom:{}:{}'.format(keyword, province['code'], city)
        url += self.weibo_type
        url += self.contain_type
        url += '&timescope=custom:{}:{}&page=1'.format(start_str, end_str)
        return url
        
    def crawl(self):
        for keyword in self.keyword_list:
            start_date = datetime.strptime(self.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(self.end_date, '%Y-%m-%d')
            while start_date <= end_date:
                self.csvWritter = WeiboWritter(f"{keyword} {start_date}")
                for i in range(0, 24):
                    self.logger.write(f'{start_date}-{i} Start')
                    count = 0
                    requestUrl = self.urlBuilder(keyword, start_date, i)
                    count += self.sendRequest(requestUrl)
                    if count == -1:
                        self.logger.write(f'{start_date}-{i} Split Region')
                        for region in self.regions.values():
                            print(region)
                            requestUrl = self.urlBuilder(keyword, start_date, i, region)
                            regionCount = self.sendRequest(requestUrl)
                            if regionCount == -1:
                                self.logger.write(f'{start_date}-{i} {region} Split City')
                                for city in region['city'].values():
                                    print(city)
                                    requestUrl = self.urlBuilder(keyword, start_date, i, region, city)
                                    count += self.sendRequest(requestUrl, firstPage=False)
                            else:
                                count += regionCount
                    
                    self.logger.write(f'{start_date}-{i} Complete')
                start_date = start_date + timedelta(days=1)
                
    def sendRequest(self, url, firstPage=True):
            ## send request, get response
            token = self.tokenPool.getToken()
            header = buildHeader(token)
            page = requests.get(url, headers=header)
            response = html.fromstring(page.content)
            is_empty = response.xpath('//div[@class="card card-no-result s-pt20b40"]')
            page_count = len(response.xpath('//ul[@class="s-scroll"]/li'))
            print(page_count)
            if is_empty:
                print('当前页面搜索结果为空')
                return 0
            if page_count < 50 or firstPage == False:
                count = 0 
                try:
                    for weibo in self.parse_weibo(response):
                        count += 1
                        self.csvWritter.write(weibo)
                except TokenError:
                    self.tokenPool.disableToken(token)
                    return self.sendRequest(url, firstPage)

                next_url = response.xpath('//a[@class="next"]/@href')[0]
                if next_url: 
                    next_url = self.base_url + next_url
                    next_count = self.sendRequest(next_url, firstPage=False)
                    return count + next_count 
                else:
                    return count
            else: ## Split
                
                return -1
                

    def parse_weibo(self, response):
        """解析网页中的微博信息"""
        # keyword = response.meta.get('keyword')
        all_weibo = []
        for sel in response.xpath("//div[@class='card-wrap']"):
            info = sel.xpath(
                "div[@class='card']/div[@class='card-feed']/div[@class='content']/div[@class='info']"
            )
            if info:
                weibo = WeiboItem()
                try:
                    weibo['id'] = sel.xpath('@mid')[0]
                except IndexError:
                    weibo['id'] = ''

                try:
                    weibo['bid'] = sel.xpath('(.//p[@class="from"])[last()]/a[1]/@href')[0].split('/')[-1].split('?')[0]
                except IndexError:
                    weibo['bid'] = ''

                try:
                    weibo['user_id'] = info[0].xpath('div[2]/a/@href')[0].split('?')[0].split('/')[-1]
                except IndexError:
                    weibo['user_id'] = ''

                try:
                    weibo['screen_name'] = info[0].xpath('div[2]/a/@nick-name')[0]
                except IndexError:
                    weibo['screen_name'] = ''
                
                txt_sel = sel.xpath('.//p[@class="txt"]')[0]
                retweet_sel = sel.xpath('.//div[@class="card-comment"]')
                retweet_txt_sel = ''
                if retweet_sel and retweet_sel[0].xpath('.//p[@class="txt"]'):
                    retweet_txt_sel = retweet_sel[0].xpath(
                        './/p[@class="txt"]')[0]
                content_full = sel.xpath(
                    './/p[@node-type="feed_list_content_full"]')
                is_long_weibo = False
                is_long_retweet = False
                if content_full:
                    if not retweet_sel:
                        txt_sel = content_full[0]
                        is_long_weibo = True
                    elif len(content_full) == 2:
                        txt_sel = content_full[0]
                        retweet_txt_sel = content_full[1]
                        is_long_weibo = True
                        is_long_retweet = True
                    elif retweet_sel[0].xpath(
                            './/p[@node-type="feed_list_content_full"]'):
                        retweet_txt_sel = retweet_sel[0].xpath(
                            './/p[@node-type="feed_list_content_full"]')[0]
                        is_long_retweet = True
                    else:
                        txt_sel = content_full[0]
                        is_long_weibo = True

                try:
                    weibo['text'] = txt_sel.xpath('string(.)').replace('\u200b', '').replace('\ue627', '')
                except IndexError:
                    weibo['text'] = ''

                weibo['article_url'] = self.get_article_url(txt_sel)
                weibo['location'] = self.get_location(txt_sel)
                if weibo['location']:
                    weibo['text'] = weibo['text'].replace(
                        '2' + weibo['location'], '')
                weibo['text'] = weibo['text'][2:].replace(' ', '')
                if is_long_weibo:
                    weibo['text'] = weibo['text'][:-6]

                weibo['at_users'] = self.get_at_users(txt_sel)
                weibo['topics'] = self.get_topics(txt_sel)
                try:
                    reposts_count = sel.xpath('.//a[@action-type="feed_list_forward"]/text()')[0]
                except IndexError:
                    reposts_count = ''

                try:
                    reposts_count = re.findall(r'\d+.*', reposts_count)
                except TypeError:
                    print('cookie无效或已过期，请按照'
                          'https://github.com/dataabc/weibo-search#如何获取cookie'
                          ' 获取cookie')
                    raise CloseSpider()
                weibo['reposts_count'] = reposts_count[
                    0] if reposts_count else '0'
                
                try:
                    comments_count = sel.xpath('.//a[@action-type="feed_list_comment"]/text()')[0]
                except IndexError:
                    comments_count = ''

                comments_count = re.findall(r'\d+.*', comments_count)
                weibo['comments_count'] = comments_count[
                    0] if comments_count else '0'

                try:
                    attitudes_count = sel.xpath('(.//a[@action-type="feed_list_like"])[last()]/em/text()')[0]
                except IndexError:
                    attitudes_count = ''

                weibo['attitudes_count'] = (attitudes_count
                                            if attitudes_count else '0')

                try:
                    created_at = sel.xpath('(.//p[@class="from"])[last()]/a[1]/text()')[0].replace(' ', '').replace('\n', '').split('前')[0]
                except IndexError:
                    created_at = ''

                weibo['created_at'] = util.standardize_date(created_at)

                try:
                    source = sel.xpath('(.//p[@class="from"])[last()]/a[2]/text()')[0]
                except IndexError:
                    source = ''

                weibo['source'] = source if source else ''
                pics = ''
                is_exist_pic = sel.xpath(
                    './/div[@class="media media-piclist"]')
                if is_exist_pic:
                    pics = is_exist_pic[0].xpath('ul[1]/li/img/@src')[:]
                    pics = [pic[2:] for pic in pics]
                    pics = [
                        re.sub(r'/.*?/', '/large/', pic, 1) for pic in pics
                    ]
                    pics = ['http://' + pic for pic in pics]
                video_url = ''
                is_exist_video = sel.xpath(
                    './/div[@class="thumbnail"]/a/@action-data')
                if is_exist_video:
                    
                    try:
                        video_url = is_exist_video[0]
                    except IndexError:
                        video_url = ''

                    video_url = unquote(
                        str(video_url)).split('video_src=//')[-1]
                    video_url = 'http://' + video_url
                if not retweet_sel:
                    weibo['pics'] = pics
                    weibo['video_url'] = video_url
                else:
                    weibo['pics'] = ''
                    weibo['video_url'] = ''
                weibo['retweet_id'] = ''
                if retweet_sel and retweet_sel[0].xpath(
                        './/div[@node-type="feed_list_forwardContent"]/a[1]'):
                    retweet = WeiboItem()

                    try:
                        retweet['id'] = retweet_sel[0].xpath('.//a[@action-type="feed_list_like"]/@action-data')[0][4:]
                    except IndexError:
                        retweet['id'] = ''

                    try:
                        retweet['bid'] = retweet_sel[0].xpath('.//p[@class="from"]/a/@href')[0].split('/')[-1].split('?')[0]    
                    except IndexError:
                        retweet['bid'] = ''


                    info = retweet_sel[0].xpath(
                        './/div[@node-type="feed_list_forwardContent"]/a[1]'
                    )[0]

                    try:
                        retweet['user_id'] = info.xpath('@href')[0].split('/')[-1]
                    except IndexError:
                        retweet['user_id'] = ''

                    try:
                        retweet['screen_name'] = info.xpath('@nick-name')[0]
                    except IndexError:
                        retweet['screen_name'] = ''

                    try:
                        retweet['text'] = retweet_txt_sel.xpath('string(.)').replace('\u200b','').replace('\ue627', '')
                    except IndexError:
                        retweet['text'] = ''

                    
                    
                    

                    retweet['article_url'] = self.get_article_url(
                        retweet_txt_sel)
                    retweet['location'] = self.get_location(retweet_txt_sel)
                    if retweet['location']:
                        retweet['text'] = retweet['text'].replace(
                            '2' + retweet['location'], '')
                    retweet['text'] = retweet['text'][2:].replace(' ', '')
                    if is_long_retweet:
                        retweet['text'] = retweet['text'][:-6]

                    import pdb; pdb.set_trace()
                    retweet['at_users'] = self.get_at_users(retweet_txt_sel)
                    retweet['topics'] = self.get_topics(retweet_txt_sel)

                    try:
                        reposts_count = retweet_sel[0].xpath('.//ul[@class="act s-fr"]/li/a[1]/text()')[0]
                    except IndexError:
                        reposts_count = ''
                    

                    reposts_count = re.findall(r'\d+.*', reposts_count)
                    retweet['reposts_count'] = reposts_count[
                        0] if reposts_count else '0'

                    try:
                        comments_count = retweet_sel[0].xpath('.//ul[@class="act s-fr"]/li[2]/a[1]/text()')[0]
                    except IndexError:
                        comments_count = ''

                    
                    comments_count = re.findall(r'\d+.*', comments_count)
                    retweet['comments_count'] = comments_count[
                        0] if comments_count else '0'

                    try:
                        attitudes_count = retweet_sel[0].xpath('.//a[@action-type="feed_list_like"]/em/text()')[0]
                    except IndexError:
                        attitudes_count = ''

                    retweet['attitudes_count'] = (attitudes_count
                                                  if attitudes_count else '0')
                    try:    
                        created_at = retweet_sel[0].xpath('.//p[@class="from"]/a[1]/text()')[0].replace(' ', '').replace('\n', '').split('前')[0]
                    except IndexError:
                        created_at = ''

                    retweet['created_at'] = util.standardize_date(created_at)

                    try:
                        source = retweet_sel[0].xpath('.//p[@class="from"]/a[2]/text()')[0]
                    except IndexError:
                        source = ''

                    retweet['source'] = source if source else ''
                    retweet['pics'] = pics
                    retweet['video_url'] = video_url
                    retweet['retweet_id'] = ''
                    # yield {'weibo': retweet, 'keyword': keyword}
                    weibo['retweet_id'] = retweet['id']
                all_weibo.append(weibo)
        return all_weibo

    
    def get_article_url(self, selector):
        """获取微博头条文章url"""
        article_url = ''
        text = selector.xpath('string(.)').replace(
            '\u200b', '').replace('\ue627', '').replace('\n',
                                                        '').replace(' ', '')
        if text.startswith('发布了头条文章'):
            urls = selector.xpath('.//a')
            for url in urls:
                if url.xpath(
                        'i[@class="wbicon"]/text()')[0] == 'O':
                    if url.xpath('@href')[0] and url.xpath(
                            '@href')[0].startswith('http://t.cn'):
                        article_url = url.xpath('@href')[0]
                    break
        return article_url

    def get_location(self, selector):
        """获取微博发布位置"""
        a_list = selector.xpath('.//a')
        location = ''
        for a in a_list:
            if a.xpath('./i[@class="wbicon"]') and a.xpath(
                    './i[@class="wbicon"]/text()')[0] == '2':
                location = a.xpath('string(.)')[1:]
                break
        return location

    def get_at_users(self, selector):
        """获取微博中@的用户昵称"""
        a_list = selector.xpath('.//a')
        at_users = ''
        at_list = []
        for a in a_list:
            if len(unquote(a.xpath('@href')[0])) > 14 and len(a.xpath('string(.)')) > 1:
                if unquote(a.xpath('@href')[0])[14:] == a.xpath('string(.)')[1:]:
                    at_user = a.xpath('string(.)')[1:]
                    if at_user not in at_list:
                        at_list.append(at_user)
        if at_list:
            at_users = ','.join(at_list)
        return at_users

    def get_topics(self, selector):
        """获取参与的微博话题"""
        a_list = selector.xpath('.//a')
        topics = ''
        topic_list = []
        for a in a_list:
            text = a.xpath('string(.)')
            if len(text) > 2 and text[0] == '#' and text[-1] == '#':
                if text[1:-1] not in topic_list:
                    topic_list.append(text[1:-1])
        if topic_list:
            topics = ','.join(topic_list)
        return topics



