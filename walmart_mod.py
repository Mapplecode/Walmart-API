# -*- coding: utf-8 -*-
import requests
import uuid
import csv
import io
import zipfile

from datetime import datetime
from requests.auth import HTTPBasicAuth
from lxml import etree
from lxml.builder import E, ElementMaker
from walmart.exceptions import WalmartAuthenticationError


def epoch_milliseconds(dt):
    "Walmart accepts timestamps as epoch time in milliseconds"
    epoch = datetime.utcfromtimestamp(0)
    return (dt - epoch).total_seconds() * 1000.0


class Walmart(object):

    def __init__(self, client_id, client_secret):
        """To get client_id and client_secret for your Walmart Marketplace
        visit: https://developer.walmart.com/#/generateKey
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expires_in = None
        self.base_url = "https://marketplace.walmartapis.com/v3"

        session = requests.Session()
        session.headers.update({
            "WM_SVC.NAME": "Walmart Marketplace",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        })
        session.auth = HTTPBasicAuth(self.client_id, self.client_secret)
        self.session = session

        # Get the token required for API requests
        self.authenticate()

    def authenticate(self):
        data = self.send_request(
            "POST", "{}/token".format(self.base_url),
            body={
                "grant_type": "client_credentials",
            },
        )
        self.token = data["access_token"]
        self.token_expires_in = data["expires_in"]

        self.session.headers["WM_SEC.ACCESS_TOKEN"] = self.token

    @property
    def items(self):
        return Items(connection=self)


    @property
    def ordersReleased(self):
        return OrdersReleased(connection=self)
    @property
    def availableReconFiles(self):
        return AvailableReconFiles(connection=self)

    @property
    def ReconFiles_date(self):
        dated_data = AvailableReconFiles_dated(connection=self)
        return dated_data
    @property
    def itemPerformance(self):
        return ItemPerformance(connection=self)
    @property
    def itemTexonomy(self):
        return ItemTexonomy(connection=self)

    @property
    def inventory(self):
        return Inventory(connection=self)

    @property
    def inventories(self,limit=50,cursor=''):
        limit = str(limit)
        if cursor == '':
            return(AllInventories(connection=self))
        else:
            return cursor

    @property
    def prices(self):
        return Prices(connection=self)

    @property
    def orders(self):
        return Orders(connection=self)

    @property
    def report(self):
        return Report(connection=self)
    @property
    def qualitylisting(self):
        return Qualitylisting(connection=self)
    def send_request(
        self, method, url, params=None, body=None, request_headers=None
    ):
        # A unique ID which identifies each API call and used to track
        # and debug issues; use a random generated GUID for this ID
        headers = {
            "WM_QOS.CORRELATION_ID": uuid.uuid4().hex,
        }
        if request_headers:
            headers.update(request_headers)

        response = None
        if method == "GET":
            response = self.session.get(url, params=params, headers=headers)
        elif method == "PUT":
            response = self.session.put(
                url, params=params, headers=headers, data=body
            )
        elif method == "POST":
            response = self.session.post(url, data=body, headers=headers)

        if response is not None:
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                if response.status_code == 401:
                    raise WalmartAuthenticationError((
                        "Invalid client_id or client_secret. Please verify "
                        "your credentials from https://developer.walmart."
                        "com/#/generateKey"
                    ))
                elif response.status_code == 400:
                    data = response.json()
                    if data["error"][0]["code"] == \
                            "INVALID_TOKEN.GMP_GATEWAY_API":
                        # Refresh the token as the current token has expired
                        self.authenticate()
                        return self.send_request(
                            method, url, params, body, request_headers
                        )
                raise
        try:
            return response.json()
        except ValueError:
            # In case of reports, there is no JSON response, so return the
            # content instead which contains the actual report
            return response.content


class Resource(object):
    """
    A base class for all Resources to extend
    """

    def __init__(self, connection):
        self.connection = connection

    @property
    def url(self):
        return "{}/{}".format(self.connection.base_url, self.path)

    def all(self, **kwargs):
        return self.connection.send_request(
            method="GET", url=self.url, params=kwargs
        )
    def date(self,date='', **kwargs):
        url = self.connection.base_url+'/report/reconreport/reconFile?reportDate={}'.format(str(date))
        return self.connection.send_request(
            method="GET", url=url, params=kwargs
        )
    def get(self, id):
        url = "{}/{}".format(self.url, id)
        return self.connection.send_request(method="GET", url=url)

    def update(self, **kwargs):
        return self.connection.send_request(
            method="PUT", url=self.url, params=kwargs
        )

    def bulk_update(self, items):
        url = self.connection.base_url % 'feeds?feedType=%s' % self.feedType
        boundary = uuid.uuid4().hex
        headers = {
            'Content-Type': "multipart/form-data; boundary=%s" % boundary
        }
        data = self.get_payload(items)
        body = '--{boundary}\n\n{data}\n--{boundary}--'.format(
            boundary=boundary, data=data
        )
        return self.connection.send_request(
            method='POST',
            url=url,
            body=body,
            request_headers=headers
        )


class Items(Resource):
    """
    Get all items
    """

    path = 'items'

    def get_items(self):
        "Get all the items from the Item Report"
        response = self.connection.report.all(type="item")
        zf = zipfile.ZipFile(io.BytesIO(response), "r")
        product_report = zf.read(zf.infolist()[0]).decode("utf-8")

        return list(csv.DictReader(io.StringIO(product_report)))


class Inventory(Resource):
    """
    Retreives inventory of an item
    """

    path = 'inventory'
    feedType = 'inventory'

    def update_inventory(self, sku, quantity):
        headers = {
            'Content-Type': "application/xml"
        }
        return self.connection.send_request(
            method='PUT',
            url=self.url,
            params={'sku': sku},
            body=self.get_inventory_payload(sku, quantity),
            request_headers=headers
        )

    def get_inventory_payload(self, sku, quantity):
        element = ElementMaker(
            namespace='http://walmart.com/',
            nsmap={
                'wm': 'http://walmart.com/',
            }
        )
        return etree.tostring(
            element(
                'inventory',
                element('sku', sku),
                element(
                    'quantity',
                    element('unit', 'EACH'),
                    element('amount', str(quantity)),
                ),
                element('fulfillmentLagTime', '4'),
            ), xml_declaration=True, encoding='utf-8'
        )

    def get_payload(self, items):
        return etree.tostring(
            E.InventoryFeed(
                E.InventoryHeader(E('version', '1.4')),
                *[E(
                    'inventory',
                    E('sku', item['sku']),
                    E(
                        'quantity',
                        E('unit', 'EACH'),
                        E('amount', item['quantity']),
                    )
                ) for item in items],
                xmlns='http://walmart.com/'
            )
        )


class Prices(Resource):
    """
    Retreives price of an item
    """

    path = 'prices'
    feedType = 'price'

    def get_payload(self, items):
        root = ElementMaker(
            nsmap={'gmp': 'http://walmart.com/'}
        )
        return etree.tostring(
            root.PriceFeed(
                E.PriceHeader(E('version', '1.5')),
                *[E.Price(
                    E(
                        'itemIdentifier',
                        E('sku', item['sku'])
                    ),
                    E(
                        'pricingList',
                        E(
                            'pricing',
                            E(
                                'currentPrice',
                                E(
                                    'value',
                                    **{
                                        'currency': item['currenctCurrency'],
                                        'amount': item['currenctPrice']
                                    }
                                )
                            ),
                            E('currentPriceType', item['priceType']),
                            E(
                                'comparisonPrice',
                                E(
                                    'value',
                                    **{
                                        'currency': item['comparisonCurrency'],
                                        'amount': item['comparisonPrice']
                                    }
                                )
                            ),
                            E(
                                'priceDisplayCode',
                                **{
                                    'submapType': item['displayCode']
                                }
                            ),
                        )
                    )
                ) for item in items]
            ), xml_declaration=True, encoding='utf-8'
        )


class Orders(Resource):
    """
    Retrieves Order details
    """

    path = 'orders'

    def all(self, **kwargs):
        try:
            return super(Orders, self).all(**kwargs)
        except requests.exceptions.HTTPError as exc:
            if exc.response.status_code == 404:
                # If no orders are there on walmart matching the query
                # filters, it throws 404. In this case return an empty
                # list to make the API consistent
                return {
                    "list": {
                        "elements": {
                            "order": [],
                        }
                    }
                }
            raise

    def acknowledge(self, id):
        url = self.url + '/%s/acknowledge' % id
        return self.send_request(method='POST', url=url)

    def cancel(self, id, lines):
        url = self.url + '/%s/cancel' % id
        return self.send_request(
            method='POST', url=url, data=self.get_cancel_payload(lines))

    def get_cancel_payload(self, lines):
        element = ElementMaker(
            namespace='http://walmart.com/mp/orders',
            nsmap={
                'ns2': 'http://walmart.com/mp/orders',
                'ns3': 'http://walmart.com/'
            }
        )
        return etree.tostring(
            element(
                'orderCancellation',
                element(
                    'orderLines',
                    *[element(
                        'orderLine',
                        element('lineNumber', line),
                        element(
                            'orderLineStatuses',
                            element(
                                'orderLineStatus',
                                element('status', 'Cancelled'),
                                element(
                                    'cancellationReason', 'CANCEL_BY_SELLER'),
                                element(
                                    'statusQuantity',
                                    element('unitOfMeasurement', 'EACH'),
                                    element('amount', '1')
                                )
                            )
                        )
                    ) for line in lines]
                )
            ), xml_declaration=True, encoding='utf-8'
        )

    def create_shipment(self, order_id, lines):
        """Send shipping updates to Walmart

        :param order_id: Purchase order ID of an order
        :param lines: Order lines to be fulfilled in the format:
            [{
                "line_number": "123",
                "uom": "EACH",
                "quantity": 3,
                "ship_time": datetime(2019, 04, 04, 12, 00, 00),
                "other_carrier": None,
                "carrier": "USPS",
                "carrier_service": "Standard",
                "tracking_number": "34567890567890678",
                "tracking_url": "www.fedex.com",
            }]
        """
        url = self.url + "/{}/shipping".format(order_id)

        order_lines = []
        for line in lines:
            ship_time = line.get("ship_time", "")
            if ship_time:
                ship_time = epoch_milliseconds(ship_time)
            order_lines.append({
                "lineNumber": line["line_number"],
                "orderLineStatuses": {
                    "orderLineStatus": [{
                        "status": "Shipped",
                        "statusQuantity": {
                            "unitOfMeasurement": line.get("uom", "EACH"),
                            "amount": str(line["quantity"]),
                        },
                        "trackingInfo": {
                            "shipDateTime": ship_time,
                            "carrierName": {
                                "otherCarrier": line.get("other_carrier"),
                                "carrier": line["carrier"],
                            },
                            "methodCode": line.get("carrier_service", ""),
                            "trackingNumber": line["tracking_number"],
                            "trackingURL": line.get("tracking_url", "")
                        }
                    }],
                }
            })

        body = {
            "orderShipment": {
                "orderLines": {
                    "orderLine": order_lines,
                }
            }
        }
        return self.connection.send_request(
            method="POST",
            url=url,
            body=body,
        )


class Report(Resource):
    """
    Get report
    """

    path = 'getReport'

class Qualitylisting(Resource):
    path = 'insights/items/listingQuality/score'

class AvailableReconFiles(Resource):
    path = 'report/reconreport/availableReconFiles'

class AvailableReconFiles_dated(Resource):
    path = 'report/reconreport/reconFile'

class ItemPerformance(Resource):
    path = 'getReport?type=itemPerformance'

class OrdersReleased(Resource):
    path = 'orders/released'

class ItemTexonomy(Resource):
    path = 'items/taxonomy'

class AllInventories(Resource):
    path = 'inventories'
