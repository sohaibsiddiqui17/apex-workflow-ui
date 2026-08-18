/* ---------------------------------------------------------------------------
   apex-menu.js
   The X-Control left menu, extracted verbatim from the production capture
   (New DOM Structure/Import_Confirm.html, ul#side-menu).

   Labels, nesting depth and data-index values match production exactly, so
   a bot that clicks a.J_menuItem[data-index="16"] on the mock clicks the same
   thing on the real portal.
   --------------------------------------------------------------------------- */

(function (root) {
  'use strict';

  root.APEX_MENU = [
    {
      "label": "Update ATD&ATA",
      "icon": "fa-tachometer",
      "index": 2,
      "href": "https://xcimport.apexworkflow.com/updateAtdAta"
    },
    {
      "label": "US",
      "icon": "fa-paper-plane-o",
      "children": [
        {
          "label": "DN List",
          "index": 3,
          "href": "https://xcimport.apexworkflow.com/dnList"
        },
        {
          "label": "Delivery Address Confirmation",
          "index": 4,
          "href": "https://xcimport.apexworkflow.com/deliveryAddressConfirmation"
        },
        {
          "label": "Global IWT",
          "index": 5,
          "href": "https://wms-web-us.apexworkflow.com/asn/iwtManagement"
        },
        {
          "label": "OP-AMS Confirm",
          "index": 6,
          "href": "https://xcimport.apexworkflow.com/opAmsConfirm"
        },
        {
          "label": "Confirm Pre-DO",
          "index": 7,
          "href": "https://www.apexworkflow.com/hawb/dp/predp"
        },
        {
          "label": "Packing List",
          "index": 8,
          "href": "https://xcimport.apexworkflow.com/packingList"
        },
        {
          "label": "Dispatch-WT",
          "index": 9,
          "href": "https://www.apexworkflow.com/hawb/dp/wt"
        },
        {
          "label": "Dispatch-DO",
          "index": 10,
          "href": "https://www.apexworkflow.com/hawb/dp/dodp"
        },
        {
          "label": "CS-Document To Broker",
          "index": 11,
          "href": "https://xcimport.apexworkflow.com/docToBroker"
        },
        {
          "label": "Custom Admission/Release",
          "index": 12,
          "href": "https://xcimport.apexworkflow.com/customsRelease"
        },
        {
          "label": "Create Hold",
          "index": 13,
          "href": "https://xcimport.apexworkflow.com/create/hold"
        },
        {
          "label": "ABI Query",
          "index": 14,
          "href": "https://xcimport.apexworkflow.com/abiQuery"
        },
        {
          "label": "New Import Job",
          "index": 15,
          "href": "https://xcimport.apexworkflow.com/newImportJobApAc"
        },
        {
          "label": "Import Confirm",
          "index": 16,
          "href": "https://xcimport.apexworkflow.com/importConfirm"
        }
      ]
    },
    {
      "label": "xdoc management",
      "index": 17,
      "href": "https://xdoc.apexworkflow.com/xDocManagement?systemcode=xdoc&dbno=100"
    },
    {
      "label": "Shipment List",
      "icon": "fa-cloud",
      "index": 18,
      "href": "https://xcimport.apexworkflow.com/shipmentList"
    },
    {
      "label": "Invoice",
      "icon": "fa-folder-open-o",
      "children": [
        {
          "label": "Invoice Details",
          "index": 19,
          "href": "https://www.apexworkflow.com/invoice"
        },
        {
          "label": "Billing Setting",
          "children": [
            {
              "label": "ImportConversion",
              "index": 20,
              "href": "https://ep.apexglobe.info/Conversion/ImportConversion"
            },
            {
              "label": "Price Setting",
              "index": 21,
              "href": "https://www.apexworkflow.com/bChargeSetting/bCharge"
            },
            {
              "label": "Auto Setting",
              "index": 22,
              "href": "https://www.apexworkflow.com/bAutoExecuteSetting"
            },
            {
              "label": "WeekSetting",
              "index": 23,
              "href": "https://billing.apexworkflow.com/weekSetting"
            },
            {
              "label": "OriDestRate",
              "index": 24,
              "href": "https://billing.apexworkflow.com/handlingRateSetting"
            }
          ]
        },
        {
          "label": "LenovoRemark",
          "index": 25,
          "href": "https://www.apexworkflow.com/bInvoiceJob/tierRemarkJob"
        },
        {
          "label": "Report",
          "children": [
            {
              "label": "NCC_MSFT Report",
              "index": 26,
              "href": "https://xa-report.apexworkflow.com/home/list/NCC_MSFT_Billing_Report?systemCode=XC"
            },
            {
              "label": "MSFT Report",
              "index": 27,
              "href": "https://xa-report.apexworkflow.com/home/list/MSFT_Billing_Report?systemCode=XC"
            }
          ]
        },
        {
          "label": "ChargeList",
          "index": 28,
          "href": "https://billing.apexworkflow.com/chargeList"
        },
        {
          "label": "Internal Settlement Management",
          "index": 29,
          "href": "https://www.apexworkflow.com/bInvoice/bInvoiceClaim"
        },
        {
          "label": "Charge Code Mapping",
          "index": 30,
          "href": "https://billing.apexworkflow.com/chargeCodeMapping"
        },
        {
          "label": "Exception ShipmentLists",
          "index": 31,
          "href": "https://billing.apexworkflow.com/wrongCityList"
        },
        {
          "label": "Internal Settlement Management(US)",
          "index": 32,
          "href": "https://www.apexworkflow.com/bInvoice/bInvoiceClaimAbroad"
        },
        {
          "label": "Charge Code",
          "index": 33,
          "href": "https://www.apexworkflow.com/bChargeType"
        },
        {
          "label": "BShipmentList",
          "index": 34,
          "href": "https://www.apexworkflow.com/bInvoiceJob"
        },
        {
          "label": "Invoice List",
          "index": 35,
          "href": "https://www.apexworkflow.com/bInvoice"
        }
      ]
    },
    {
      "label": "214 Exception Management",
      "icon": "fa-book",
      "index": 36,
      "href": "https://www.apexworkflow.com/start/APEX214ExceptionManagement"
    },
    {
      "label": "Operation Log",
      "icon": "fa-building-o",
      "index": 37,
      "href": "https://www.apexworkflow.com/operlog/index1"
    },
    {
      "label": "Report",
      "icon": "fa-reply-all",
      "children": [
        {
          "label": "ASUS Tracking Report",
          "index": 38,
          "href": "https://xa-report.apexworkflow.com/home/list/ASUS_tracking_report?systemCode=XC"
        },
        {
          "label": "BillingCW Monitor",
          "index": 39,
          "href": "https://xa-report.apexworkflow.com/home/list/Apple_Billing_Wrong_CW_Report?systemCode=XC"
        },
        {
          "label": "EDI 214 Status Report-Air",
          "index": 40,
          "href": "https://xa-report.apexworkflow.com/home/list/EDI_214_Status_Report?systemCode=XC"
        },
        {
          "label": "EDI 214 Status Report-Truck",
          "index": 41,
          "href": "https://xa-report.apexworkflow.com/home/list/EDI_214_Status_Report_2?systemCode=XC"
        },
        {
          "label": "GAP General Report",
          "index": 42,
          "href": "https://xa-report.apexworkflow.com/home/list/XControlSystem_GAP_GENERAL_REPORT?systemCode=XC"
        },
        {
          "label": "NCC_Tesla Billing Status",
          "index": 43,
          "href": "https://xa-report.apexworkflow.com/home/list/NCC_Tesla_Billing_Status?systemCode=XC"
        },
        {
          "label": "Tesla Billing Status",
          "index": 44,
          "href": "https://xa-report.apexworkflow.com/home/list/Tesla_Billing_Status?systemCode=XC"
        },
        {
          "label": "TMS_adoption_report",
          "index": 45,
          "href": "https://xa-report.apexworkflow.com/home/list/TMS_adoption_report?systemCode=XC"
        }
      ]
    },
    {
      "label": "Air Event Management",
      "icon": "fa-align-justify",
      "children": [
        {
          "label": "Air Event Management",
          "index": 46,
          "href": "https://xcplugec.apexworkflow.com/apexfront/xc/airmilestone_new2"
        },
        {
          "label": "Air Event Label Default",
          "index": 47,
          "href": "https://xcplugec.apexworkflow.com/apexfront/xc/airmilestone_customer"
        },
        {
          "label": "Air Event Log",
          "index": 48,
          "href": "https://xcplugec.apexworkflow.com/apexfront/xc/airmilestone_log"
        },
        {
          "label": "Truck Milestone Management",
          "index": 49,
          "href": "https://xcplugec.apexworkflow.com/apexfront/truckmilestone/index"
        },
        {
          "label": "SHEIN AI Milestone",
          "index": 50,
          "href": "https://xcplugec.apexworkflow.com/apexfront/xc/airmilestone_sheinai"
        }
      ]
    },
    {
      "label": "System management",
      "icon": "fa-user",
      "children": [
        {
          "label": "Charge code management",
          "index": 51,
          "href": "https://chargecode.apexglobe.info/chargetype"
        },
        {
          "label": "bAccounts",
          "index": 52,
          "href": "https://system.apexworkflow.com/accounts/accounts.html"
        }
      ]
    },
    {
      "label": "E-Commerce",
      "children": [
        {
          "label": "Warehouse In",
          "index": 53,
          "href": "https://xcplugec.apexworkflow.com/xc_web/xc/warehousesInPending"
        },
        {
          "label": "Segregation",
          "index": 54,
          "href": "https://www.apexworkflow.com/ebay/cargoReady/cargoReady"
        },
        {
          "label": "Warehouse Out",
          "index": 55,
          "href": "https://www.apexworkflow.com/ebay/wtOut/pendingWhoutList"
        },
        {
          "label": "Consolidation",
          "index": 56,
          "href": "https://xcplugec.apexworkflow.com/xc_web/xc/consolidation"
        },
        {
          "label": "Customs Exam",
          "index": 57,
          "href": "https://xcplugec.apexworkflow.com/xc_web/xc/exampending"
        },
        {
          "label": "Exception Handling",
          "index": 58,
          "href": "https://xcplugec.apexworkflow.com/xc_web/xc/exception"
        }
      ]
    },
    {
      "label": "Milestone Management Center",
      "icon": "fa-address-card-o",
      "index": 59,
      "href": "https://xcplugec.apexworkflow.com/xc_web/xc/milestonemanagementcenter"
    },
    {
      "label": "AI Booking",
      "index": 60,
      "href": "https://www.apexworkflow.com/usBooking/goLeftList"
    }
  ];

  /* Menu indices the mock models in full; everything else opens the stub. */
  root.APEX_FRAME_SRC = {
    0:  'frames/home.html',
    2:  'frames/updateAtdAta.html',
    16: 'frames/importConfirm.html'
  };
})(typeof window !== 'undefined' ? window : this);
