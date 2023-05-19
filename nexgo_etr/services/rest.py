

import json
import frappe
import requests
import random
import qrcode
# from PIL import Image
import base64
#import string
from io import BytesIO
from frappe_qrcode.frappe_qr_code.doctype.frappe_qr_code_settings.frappe_qr_code_settings import generate_qr_code

# def generate_random_kra_pin():
#     mid_number=random.randint(0, 50000000)
#     letters = list(string.ascii_uppercase)
#     random_letter=random.randint(0,25)
#     second_arg_in_pin=[0,1,2,3,4,5,6,7,8,9]
#     pin=letters[random_letter]+str(second_arg_in_pin[0])+str(mid_number)+letters[random_letter-1]
#     print(f"\n\n\n{pin}\n\n\n")

def get_pin_of_buyer(invoice_number):
    customer_name=frappe.db.get_value("Sales Invoice", {"name":invoice_number}, "customer")
    return frappe.db.get_value("Customer",{"name":customer_name},"kra_pin")


def get_mode_of_payment(invoice_number):
    return frappe.db.get_value("Sales Invoice Payment",{"parent":invoice_number},"mode_of_payment")


def generate_qrCode(response_data_from_receipt_type):
    mdw_invoice_number=response_data_from_receipt_type['invoice']['middlewareInvoiceNumber']
    qrcode_data="https://itax.kra.go.ke/KRA-Portal/invoiceChk.htm?actionCode=loadPage&invoiceNo="+str(mdw_invoice_number)

    box_size = frappe.db.get_single_value('Frappe QR Code Settings', 'box_size')
    border = frappe.db.get_single_value('Frappe QR Code Settings', 'border')
    fill_color = frappe.db.get_single_value('Frappe QR Code Settings', 'fill_color')
    back_color = frappe.db.get_single_value('Frappe QR Code Settings', 'back_color')


    qr_code_image =  generate_qr_code(box_size=box_size, border=border, fill_color=fill_color, back_color=back_color, qrcode_data=qrcode_data)
    return qr_code_image

link="https://itax.kra.go.ke/KRA-Portal/invoiceChk.htm?actionCode=loadPage&invoiceNo="
url="http://192.168.100.16:8081/" 

@frappe.whitelist()
def post_data(item):

    random_number=random.randint(5,60000000)
    random_receipt_number=str(random_number)+item       

    # url="http://192.168.43.1:8081/" 

    invoice_info=frappe.db.get_all("Sales Invoice",{"name":item},["total","posting_date","posting_time"])
    total_cost=invoice_info[0]['total']
    posting_date=invoice_info[0]['posting_date']
    posting_time=invoice_info[0]['posting_time']

    print(f"\n\n\n{random_receipt_number}\n\n\n")

    item_codes_array=[]
    item_codes_array.append(item)

    for code in item_codes_array:
        print(f"\n\n\n{code}\n\n\n")
        data_from_invoice_item=frappe.db.get_all("Sales Invoice Item", {'parent':code},["item_name","qty","amount","uom"])

        inv_items=[]

        for invoice_item in data_from_invoice_item:
           print(f"\n\n\n{invoice_item.amount}\n\n\n")
           inv_items.append({
            "productName":invoice_item.item_name,
            "quantity":invoice_item.qty,
            "amount":invoice_item.amount,
            "taxRate": 16,
            "taxExempted": False,
            "hsCode": "000.111.23", 
            "unitOfMeasure": invoice_item.uom, 
            "discount": 10, 
            "discountIsPercentage": True 
            })
            # print(f"\n\n\n this areinv_items in {items}\n\n\n")
        # invoice_types=["FISCAL RECEIPT","DEBIT NOTE RECEIPT"]
        # for invoice_type in invoice_types:
        #     print(f"\n\n\n{invoice_type}\n\n\n")

        FISCAL={
            "type":"FISCAL RECEIPT",
            "paymentMethod":get_mode_of_payment(item),
            "amountPaid":total_cost,
            "buyerPin":get_pin_of_buyer(item),
            "reference":code, 
            "date":str(posting_date),
            "time":str(posting_time),
            "receiptNumber":item,
            "items":inv_items
        }      

    

        fiscal_response=requests.post(url,json=FISCAL)
        fiscal_data=json.loads(fiscal_response.text)

        sales_invoice_qrCodes=frappe.get_doc({
             "doctype" : "Sales Invoice QR Codes",
            "invoice_number" : code,
            "invoice_qr_code":generate_qrCode(fiscal_data),
            "invoice_serial_number":random_receipt_number
        })
        sales_invoice_qrCodes.submit()
    
        print(f"\n\n\n{fiscal_data}\n\n\n")
        return fiscal_data,fiscal_data['success']

    




@frappe.whitelist()
def return_invoice(item):

    invoice_data=frappe.db.get_all("Sales Invoice",{"name":item},['return_against'])
    returned_against_invoice_number=invoice_data[0]['return_against']
    print(f"\n\n\n{item, returned_against_invoice_number}\n\n\n")
    
    invoice_period_SQL=f"""
    SELECT 
    posting_date,
    posting_time,
    total
    FROM `tabSales Invoice`
    WHERE name = '{returned_against_invoice_number}'
    """
    data=frappe.db.sql(invoice_period_SQL,as_dict=True)
    
    print(f"THIS IS THE DATA FROM THE SQL QUERY\n\n\n{data}\n\n\n")
    posting_date=data[0]['posting_date']
    posting_time=data[0]['posting_time']
    amount=data[0]['total']

    # invoice_serial_number=frappe.db.get_value("Sales Invoice QR Codes",{"name":returned_against_invoice_number},"invoice_serial_number") 
    get_invoice_items_info=frappe.db.get_all("Sales Invoice Item",{"parent":returned_against_invoice_number},["item_name","amount","qty"])

    invoice_items=[]
    for product in get_invoice_items_info:
        invoice_items.append({
            "productName":product.item_name,
            "amount":product.amount,
            "quantity":product.qty
        })
    

    CREDIT={
        "type": "CREDIT NOTE RECEIPT",
        "reference":returned_against_invoice_number,
        "amount":amount,
        "date":str(posting_date),
        "time":str(posting_time),
        "receiptNumber":item,
        "items":invoice_items,
        "isFullCreditNote":True
    }

    credit_response=requests.post(url,json=CREDIT)
    credit_data=json.loads(credit_response.text)
    print(f"\n\n\n{credit_data}\n\n\n")
    
    sales_return_qrCodes=frappe.get_doc({
        "doctype":"Sales Return QRcodes",
        "invoice_number":item,
        "returned_against_invoice":returned_against_invoice_number,
        "invoice_qr_code":generate_qrCode(credit_data)
    })

    sales_return_qrCodes.submit()

    is_success=credit_data['success']
    return credit_data,is_success




@frappe.whitelist()
def send_debit_note(item):
    debit_note_data=frappe.db.get_values("Sales Invoice",{"name":item},["return_against","posting_date","posting_time","total"],as_dict=True)

    returned_against_invoice=debit_note_data[0]['return_against']
    posting_date=debit_note_data[0]['posting_date']
    posting_time=debit_note_data[0]['posting_time']
    amount_to_debit=debit_note_data[0]['total']

    items=frappe.db.get_all("Sales Invoice Item",{"parent":item},["item_name","qty","amount"])

    is_debit_note_items=[]
    for product in items:
        is_debit_note_items.append({
            "productName":product.item_name,
            "quantity":product.qty,
            "amount":product.amount
        })


    DEBIT={
        "type":"DEBIT NOTE RECEIPT",
        "amount":amount_to_debit,
        "reference":returned_against_invoice, 
        "date":str(posting_date),
        "time":str(posting_time),
        "receiptNumber":item,
        "items":is_debit_note_items           
    }

    debit_note_request=requests.post(url,json=DEBIT)
    debit_note_response=json.loads(debit_note_request.text)
    print(f"\n\n\n\n{debit_note_response}\n\n\n\n")

    store_debit_note_qrCode=frappe.get_doc({
        "doctype":"Debit Note QRCodes",
        "invoice_number":item,
        "returned_against_invoice":returned_against_invoice,
        "invoice_qr_code":generate_qrCode(debit_note_response)
    })
    store_debit_note_qrCode.submit()
    success_msg=debit_note_response['success']

    return debit_note_response,success_msg



@frappe.whitelist()
def send_duplicate(item):
   
    invoice_info=frappe.db.get_values("Sales Invoice",{"name":item},["posting_date","posting_time"],as_dict=True)
    posting_date=invoice_info[0]['posting_date']
    posting_time=invoice_info[0]['posting_time']

    IS_DUPLICATE={
        "type":"DUPLICATE",
        "reference":item,
        "date":str(posting_date),
        "time":str(posting_time)

    }

    is_duplicate_request=requests.post(url,json=IS_DUPLICATE)
    is_duplicate_response=json.loads(is_duplicate_request.text)
    is_duplicate_doc=frappe.get_doc({
        "doctype":"Duplicate Receipt QR Codes",
        "invoice_number":item,
        "invoice_qr_code":generate_qrCode(is_duplicate_response)
    })
    is_duplicate_doc.submit()
   
    return is_duplicate_response,is_duplicate_response['success']

   



@frappe.whitelist()
def get_qrCode(doc):
    doctypes=["Sales Invoice QR Codes","Sales Return QRcodes","Debit Note QRCodes","Duplicate Receipt QR Codes"]
    for single_doctype in range(len(doctypes)):
        # print(f"\n\n\n\n{doctypes[single_doctype]}\n\n\n\n")
        docs=doctypes[single_doctype]
        invoice_qr_code=frappe.db.get_value(docs,{"invoice_number":doc.name},"invoice_qr_code")
        # print(f"\n\n\n\n{invoice_qr_code}\n\n\n\n")
        if invoice_qr_code !=None:
            # print(f"\n\n\n\n{invoice_qr_code, doc.name}\n\n\n\n")
            return invoice_qr_code


# @frappe.whitelist()
# def create_delivery_note(doc_name):
#     customer=frappe.db.get_value("Sales Invoice", {"name":doc_name}, "customer")
#     items=frappe.db.get_all("Sales Invoice Item",{"parent":doc_name},["item_code","item_name","qty","rate"])

#     print(f"\n\n\n\n {items}\n\n\n\n")
#     delivery=frappe.get_doc({
#         "doctype":"Delivery Note",
#         "customer":customer,
#         "items":items
#     })
#     delivery.submit()

## tomorrow  /home/orwa/point-of-sale/apps/point_of_sales_app/point_of_sales_app
## doc.qr_code = img.tobytes()
## https://itax.kra.go.ke/KRA-Portal/invoiceChk.htm?actionCode=loadPage&invoiceNo=276086946000000002


# orwa1053