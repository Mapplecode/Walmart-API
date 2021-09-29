import walmart_mod
import csv
import io
import zipfile
from datetime import datetime
def converter(data):
    zf = zipfile.ZipFile(io.BytesIO(data), "r")
    product_report = zf.read(zf.infolist()[0]).decode("utf-8")
    return list(csv.DictReader(io.StringIO(product_report)))

class Walmart():
    def __init__(self,wm='',date='',get=''):
        wm = walmart_mod.Walmart(wm[0], wm[1])
        self.wm = wm
        self.date = date
        self.get = get
    def getReports(self):
        wm = self.wm
        reports = wm.report.all()
        reports = converter(reports)
        return  reports
    def getQualitylisting(self):
        wm = self.wm
        items = wm.qualitylisting.all()
        print('SCORE is - ', items['payload']['score'])
        print('Post Purchase Quality is - ', items['payload']['postPurchaseQuality'])
        print('Listing Quality is - ', items['payload']['listingQuality'])
        return items
    def getQualityReport(self):
        wm = self.wm
        performance_report = wm.itemPerformance.all()
        performance_report = converter(performance_report)
        # print(type(performance_report))
        for pr in performance_report:
            print(pr)
        return  performance_report
    def get_AvailableReconFiles_date(self,date=''):
        wm = self.wm
        reconFiles = wm.ReconFiles_date.date(date)

        reconFiles = converter(reconFiles)
        return reconFiles
    def getavailableReconFiles(self,get=''):
        wm = self.wm
        reconFiles = wm.availableReconFiles.all()
        # print(reconFiles)
        date_list = list()
        if get == '':
            get = 'latest'
        if get == 'latest':
            # print(reconFiles)
            for rF in reconFiles['availableApReportDates']:
                # print(str(i))
                split_date = datetime.strptime(str(rF)[:2] + "-" + str(rF)[2:4] + "-" + str(rF)[4:], '%m-%d-%Y').date()
                # print(split_date)
                date_list.append((split_date))
            latest_date = (max(date_list))
            # print(latest_date)
            latest_date=(str(latest_date)[5:7]  +  str(latest_date)[-2:]  +  str(latest_date)[:4]   )
            reconFiles_d = wm.ReconFiles_date.date(str(latest_date))
            reconFiles_d = converter(reconFiles_d)
            return reconFiles_d
        if get == 'all':
            all_data = list()
            for rF in reconFiles['availableApReportDates']:
                try:
                    reconFiles_d = wm.ReconFiles_date.date(str(rF))
                    reconFiles_d = converter(reconFiles_d)
                    all_data.append(reconFiles_d)
                except:
                    pass
            return all_data

    def getInventory(self):

        wm = self.wm
        inventory = wm.inventory
        return inventory
    def getInventories(self):
        wm = self.wm
        b = True
        cursor = ''
        limit = 50
        cursor_list = list()
        count = 1
        total_count = 0
        total_count_deduction = 0
        product_list = list()
        while (b):
            invertory = wm.inventories.all(limit=limit,cursor=cursor)
            products = ((invertory['elements']['inventories']))
            cursor = invertory['meta']['nextCursor']
            total_count = int(invertory['meta']['totalCount'])
            if total_count_deduction == 0:
                total_count_deduction = total_count

            else:
                total_count_deduction = total_count_deduction - limit
            if total_count > 0:
                total_count = total_count - limit
            for pr in products:
                # print(pr)
                product_list.append(pr)
                print(pr)
            if int(invertory['meta']['totalCount']) <= (count * 50):
                b = False
                # print(total_count)
            else:
                cursor_list.append(cursor)
                count = count + 1
            if total_count_deduction < limit and total_count_deduction != 0:
                # print('LESS THEN LIMIT IS - ', total_count_deduction)
                invertory_last = wm.inventories.all(limit=total_count_deduction, cursor=str(cursor))
                for pr in invertory_last['elements']['inventories']:
                    product_list.append(pr)
                    b = False
        return product_list

    def getOrders(self):
        wm = self.wm
        orders = wm.orders.all()
        return orders
    def get_items(self):
        wm = self.wm
        items = wm.items.all()
        return items
    def getordersReleased(self):
        wm = self.wm
        ordersReleased = wm.ordersReleased.all()
        return ordersReleased
    def getitemTexonomy(self):
        wm = self.wm
        itemTexonomy = wm.itemTexonomy.all()
        return itemTexonomy


# Functions can be called like the example given Below
# Enter you're creads here

creds =('API-KEY','API-SECRET', 'Item-Name')

Wal = Walmart(wm=creds)

# This Is How You get result
# OVER Writted API CALLS

# - Financial Report
# https://developer.walmart.com/api/us/mp/orders
# RO = Wal.getordersReleased()
# print(RO)
# print("============================================")

# https://developer.walmart.com/us/whats-new/new-item-performance-report/
# QR = Wal.getQualityReport()
# print(QR)
# print("============================================")

# - Item Report
# https://developer.walmart.com/api/us/mp/items
# IT = Wal.get_items()
# print(IT)
# print("============================================")
# - Inventory Report
# https://developer.walmart.com/api/us/mp/inventory
# IN = Wal.getInventories()
# print(IN)
# print("============================================")

# - Buy Box Report
# https://developer.walmart.com/api/us/mp/reports
# YOU CAN PUT IN 'latest' OR 'all' to get the latest or all the data from the API
# RF = Wal.getavailableReconFiles(get='all')
# print(RF)

# print("============================================")
# RF = Wal.get_AvailableReconFiles_date(date='01212020')
# print(RF)
# print("============================================")
# - Listing Quality Report
# https://developer.walmart.com/api/us/mp/insights#operation/getListingQualityScore
# QL = Wal.getQualitylisting()
# print(QL)
# print("============================================")



# file= '01212020'