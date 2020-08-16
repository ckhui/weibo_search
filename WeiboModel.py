HEADER = [ 'id', 'bid', 'user_id', '用户昵称', '微博正文', '头条文章url',
    '发布位置', '艾特用户', '话题', '转发数', '评论数', '点赞数', '发布时间',
    '发布工具', '微博图片url', '微博视频url', 'retweet_id'
    ]

HEADER_ENG = ['id', 'bid', 'user_id', 'screen_name', 'text', 'article_url', 
    'location', 'at_users', 'topics', 'reposts_count', 'comments_count', 'attitudes_count', 'created_at', 
    'source', 'pics', 'video_url', 'retweet_id'
    ]

class WeiboItem(dict):
    # define the fields for your item here like:
    def __init__(self):
        super().__init__()
        # self.id = None
        # self.bid = None
        # self.user_id = None
        # self.screen_name = None
        # self.text = None
        # self.article_url = None
        # self.location = None
        # self.at_users = None
        # self.topics = None
        # self.reposts_count = None
        # self.comments_count = None
        # self.attitudes_count = None
        # self.created_at = None
        # self.source = None
        # self.pics = None
        # self.video_url = None
        # self.retweet_id = None
    
    def data(self):
        return [self.get(key, None) for key in HEADER_ENG]

    