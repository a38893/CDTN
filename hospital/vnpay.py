import hashlib
import hmac
import urllib.parse

class vnpay:
    def __init__(self):
        self.requestData = {}
        self.responseData = {}

    def get_payment_url(self, vnpay_payment_url, secret_key):
        inputData = sorted(self.requestData.items())
        queryString = urllib.parse.urlencode(inputData, quote_via=urllib.parse.quote_plus)
        hashData = "&".join(str(val) for key, val in inputData if val)  # Chỉ lấy giá trị không rỗng
        hashValue = self.__hmacsha512(secret_key, hashData)
        print(f'Create payment URL debug, HashData:{hashData}\nHashValue:{hashValue}')
        return f"{vnpay_payment_url}?{queryString}&vnp_SecureHash={hashValue}"

    def validate_response(self, secret_key):
        vnp_SecureHash = self.responseData.get('vnp_SecureHash')
        data = self.responseData.copy()
        data.pop('vnp_SecureHash', None)
        data.pop('vnp_SecureHashType', None)
        inputData = sorted((k, v) for k, v in data.items() if k.startswith('vnp_') and v)
        hasData = "&".join(str(val) for key, val in inputData)  # Chỉ lấy giá trị
        hashValue = self.__hmacsha512(secret_key, hasData)
        print(f'Validate debug, HashData:{hasData}\nHashValue:{hashValue}\nInputHash:{vnp_SecureHash}')
        return vnp_SecureHash == hashValue

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()