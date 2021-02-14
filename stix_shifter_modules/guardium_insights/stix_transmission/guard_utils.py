import requests
from requests.models import Response
import json
import sys, argparse, traceback
import hashlib
import datetime, re
from stix_shifter_utils.utils import logger

class GINSApiClient(object):

    def __init__ (self,url, secret):
        super().__init__()
        self.logger = logger.set_logger(__name__)
        self.url = url
        self.secret = secret
	    #self.user = user
        #self.password = password
        #self.client_id=client_id
        #self.token_target = '/oauth/token'
        self.report_target = '/api/v2/reports/run/'
        self.ping_target = '/api/v2/reports/categories'
        #self.qs_target = '/restAPI/quick_search'
        #self.fields_target = '/restAPI/fieldsTitles'
        self.fields = {}
        #self.get_token()
        #-H  "accept: application/json" -H  "authorization: Basic ZDBhZGQ0ODctYzZkYi00NWFlLWJkMzYtOGU0ZmM5Y2FlZjAxOjcwOTNhMjY2LTQ5ODAtNDE0My1hNzgyLWY2ODk1MDVlMmY0MQ==" -H  "Content-Type: application/json" 
        self.headers = {'Content-Type': 'application/json', 'accept':'application/json', 'Authorization': 'Basic {0}'.format(self.secret)}
        # -------------------------------------------------------------------------------
        # REPORT parameters
        # -------------------------------------------------------------------------------
        # TBD dates
        # self.set_call_dates()
        # self.QUERY_FROM_DATE = "Now -60 DAY"
        # self.QUERY_TO_DATE = "Now"
        # -------------------------------------------------------------------------------
        # QS parameters
        # -------------------------------------------------------------------------------
        # TBD dates
        # self.qs_startTime = "20200616 10:00:00"
        # self.qs_endTime = "20200616 21:00:00"
    
    def set_call_dates(self):
        # look for last_run file - if file exist read last run date from it
        # if file does not exist or date older then x days set from dates to now -1 Day
        # otherwise set from date = last run date
        self.now = datetime.datetime.now()
        self.qs_endTime = self.now.strftime("%Y-%m-%d %H:%M:%S")
        self.QUERY_TO_DATE = self.now.strftime("%Y-%m-%d %H:%M:%S")
        from_file = None
        try:
            file = open("./last_run", "r")
            try:
                text = file.read()
                from_file = json.loads(text)
            finally:
                file.close() 
        except:
            pass

        
        if from_file and self.url in from_file:
                period_start = datetime.datetime.strptime(from_file[self.url],"%Y/%m/%d %H:%M:%S")
                if self.now - period_start > datetime.timedelta(days=2):
                    period_start = self.now - datetime.timedelta(days=1)
        else:
            period_start = self.now - datetime.timedelta(days=1) 
        self.from_file = from_file    
        self.QUERY_FROM_DATE = period_start.strftime("%Y-%m-%d %H:%M:%S")
        self.qs_startTime = period_start.strftime("%Y-%m-%d %H:%M:%S")

    def save_last_run_date(self):
        try:
            if self.from_file:
                output = self.from_file
                output[self.url] = self.now.strftime("%Y/%m/%d %H:%M:%S")
            else:
                output = {self.url : self.now.strftime("%Y/%m/%d %H:%M:%S")}
            file = open("./last_run", "w")
            file.write(json.dumps(output))
        finally:
            file.close()     

    #def get_token(self):
        # -------------------------------------------------------------------------------
        # Authentication
        # -------------------------------------------------------------------------------
        # comment in and out all prints
        # print("client_id="+self.client_id)
        # print("secret="+self.secret)
        # print("user="+self.user)
        # print("password="+self.password)
        #response = self.request_token()

        #if self.validate_response(response, "token ", True):
            #self.access_token = response.json()['access_token']
            # print("token="+ self.access_token)
            #self.headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {0}'.format(self.access_token)}

    #def request_token(self):
    #    self.token_data = 'client_id={0}&grant_type=password&client_secret={1}&username={2}&password={3}'.format(
    #        self.client_id, self.secret, self.user, self.password)
            
    #    response = requests.post(self.url + self.token_target, params=self.token_data, verify=False)
    #    return response
    def ping(self):
        response = requests.get(self.url + self.ping_target, headers=self.headers, verify=False)
        return self.validate_response(response,"ping", True)

    def validate_response(self, p_response, prefix, abort=False):
        if p_response.status_code != 200:
            if abort:
                raise Exception(prefix+" request faild "+str(p_response.status_code)+"-"+p_response.reason)
            return False
        return True    

    def handle_report(self, report_id, params, offset, fetch_size):
        # -------------------------------------------------------------------------------
        # REPORT
        # -------------------------------------------------------------------------------
        #context().logger.debug('-------------------  ' + report_name + ' ----------------------')
        params_set = {"offset": "{0}".format(offset), "fetch_size": "{0}".format(fetch_size), 
        "runtime_parameter_list":params}
        rest_data = json.dumps(params_set)
        response = requests.post(self.url+self.report_target+report_id, data=rest_data, headers=self.headers, verify=False)
        if self.validate_response(response, "report", False):
            return self.translate_response(response)
        return response    


      
    
    
    def translate_response(self, response):
        # translate fields from numeric tags to field titles
        # set to lower case, replace white spaces with _
          
        sdata = str(response.content)
        sdata = sdata[2: len(sdata)-1]
        regex = r"hadar.*\(1\)"
        out_str = re.sub(regex, "ggg", sdata, 0)
        sdata = out_str 
        data = json.loads(sdata.split("\\n")[0])
        field_headers = self.flatten_field_map(data["result"]["report_layout"]["report_headers"])
        result1 = []
        if "data" in data["result"]:
            results = data["result"]["data"]    
            for result in results:
                record = result["results"]
                new_rec = dict()
                for key, value in record.items():
                    if value :
                      new_rec[field_headers[key]] = value
                    else:
                       new_rec[field_headers[key]] = ''
                result1.append(new_rec)
        response._content = json.dumps(result1) 
        return response
    
    def flatten_field_map(self, field_headers):
        ret = dict()
        print(str(field_headers))
        for field_header in field_headers:
            ret[str(field_header["sequence"])] = field_header["field_name"]["nls_value"]
        return ret

