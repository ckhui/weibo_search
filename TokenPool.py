import settings
from OutfileHelper import TokenLog
import time

class TokenPool():
    def __init__(self):
        super().__init__()
        self.ptr = 0
        self.saved_tokens = settings.TOKENS
        self.delay = settings.DOWNLOAD_DELAY

        self.token = list(self.saved_tokens.values())
        self.logger = TokenLog()

    def __len__(self):
        return len(self.token)

    def __iter__(self):
        self.ptr = 0
        return self

    def __next__(self):
        if self.ptr >= len(self.token):
            raise StopIteration
        e = self.token[self.ptr]
        self.ptr += 1
        return e
    
    def disableToken(self, token):
        self.token.remove(token)
        key = list(self.saved_tokens.keys())[list(self.saved_tokens.values()).index(token)]
        print(f'TOKEN IS DISABLE: {key}')
        self.logger.write(key)

        if len(self.token) == 0:
            raise Exception("TOKEN FINISH")

    def getToken(self):
        if self.ptr >= len(self.token):
            self.ptr = 0
            time.sleep(self.delay)
            return self.getToken()
        else:
            e = self.token[self.ptr]
            self.ptr += 1
            return e

